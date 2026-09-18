"""Deterministic claim analysis: every verdict traces to a policy clause, an IRDAI rule or a List I-IV item.

analyze(claim) -> Report. Claude (claimback.llm.review) only refines findings this engine marks as unresolved.
"""

import re
from datetime import date, datetime, timedelta, timezone

from ..fmt import inr, plural
from ..knowledge import knowledge
from ..models import (
    AlternateWording,
    CheckFinding,
    ClaimInput,
    Deduction,
    DeductionFinding,
    EscalationStep,
    OmbudsmanOffice,
    Report,
    ReportTotals,
    SimilarCase,
)
from .matcher import match_items

CLAUSE_REFERENCE = re.compile(r"clause|section|excl\s*\d|code\s|list\s+(i{1,3}|iv)\b|\b\d+\.\d+\b", re.I)
MEDICALLY_ESSENTIAL = re.compile(r"sutur|clip|implant|stent|screw|plate|mesh|staple|ligat|catheter|graft|lens|valve", re.I)
HISTOPATHOLOGY = re.compile(r"histopath|biopsy|specimen|frozen section", re.I)
SPORTS = re.compile(r"sport|football|cricket|hockey|badminton|trek|climb|marathon|gym", re.I)

# diagnosis keywords -> text of the matching specific-waiting-period condition in the policy wording
SPECIFIC_CONDITIONS = [
    (re.compile(r"calcul|stone|cholelith", re.I), "Calculi"),
    (re.compile(r"cataract", re.I), "Cataract"),
    (re.compile(r"hernia", re.I), "Hernia"),
    (re.compile(r"hysterectomy", re.I), "Hysterectomy"),
    (re.compile(r"piles|fissure|fistula|haemorrhoid|hemorrhoid", re.I), "Piles"),
    (re.compile(r"tonsil", re.I), "Tonsillectomy"),
    (re.compile(r"sinus", re.I), "Sinusitis"),
    (re.compile(r"prostat", re.I), "prostate"),
    (re.compile(r"varicose", re.I), "Varicose"),
    (re.compile(r"hydrocele", re.I), "Hydrocele"),
    (re.compile(r"joint replacement|arthroplasty", re.I), "joint replacement"),
    (re.compile(r"osteoarthritis|osteoporosis", re.I), "Osteoarthritis"),
]

CATEGORY_CASES = {
    "not_in_lists": ["non_payable_consumables"],
    "proportionate_deduction": ["proportionate_deduction", "room_rent_cap"],
    "reasonable_customary": ["reasonable_customary"],
    "non_disclosure": ["ped_non_disclosure"],
    "waiting_period": ["waiting_period"],
    "delay_documents": ["delayed_intimation", "documents"],
}


def months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    return months - 1 if end.day < start.day else months


def reason_category(reason: str) -> str:
    r = reason.lower()
    if re.search(r"proportionate|pro-?\s?rata|room rent .*exceed", r):
        return "proportionate_deduction"
    if "reasonable" in r and "customary" in r:
        return "reasonable_customary"
    if re.search(r"excl\s*0?\d+|not related|exclusion", r):
        return "exclusion"
    if re.search(r"restricted to|sub-?limit|policy limit|capped", r):
        return "policy_limit"
    if re.search(r"non-?\s?payable|not payable|consumable|non-?\s?medical|subsumed|list\s+(i{1,3}|iv)\b", r):
        return "non_payable"
    return "unknown"


class Analysis:
    def __init__(self, claim: ClaimInput):
        self.claim = claim
        self.kb = knowledge()
        self.policy = self.kb.policy(claim.policy.policy_wording_id)
        self.pid = claim.policy.policy_wording_id if self.policy else None
        self.lines = {line.code: line for line in claim.bill_lines}
        self.deduction_findings: list[DeductionFinding] = []
        self.check_findings: list[CheckFinding] = []
        self.alternate_wordings: list[AlternateWording] = []
        self.categories: set[str] = set()

    def clause(self, suffix: str) -> list[str]:
        cid = self.kb.policy_clause_id(self.pid, suffix)
        return [cid] if cid else []

    @property
    def copay_pct(self) -> float:
        if self.claim.policy.co_payment_pct is not None:
            return self.claim.policy.co_payment_pct
        return (self.policy or {}).get("limits", {}).get("co_payment_pct", 0) or 0

    @property
    def cashless_network(self) -> bool:
        return self.claim.admission.claim_type == "cashless" and bool(self.claim.admission.network_hospital)

    # ------------------------------------------------------------------------------------------------ deductions

    def analyze_deduction(self, n: int, d: Deduction) -> DeductionFinding:
        line = self.lines.get(d.line_code) if d.line_code else None
        category = reason_category(d.reason)
        base = dict(id=f"D{n:02d}", line_code=d.line_code, description=line.description if line else d.description,
                    billed=d.billed if d.billed is not None else (line.amount if line else None), deducted=d.deducted,
                    insurer_reason=d.reason)
        cites_clause = bool(CLAUSE_REFERENCE.search(d.reason))
        no_clause = [] if cites_clause else ["R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"]

        if category == "proportionate_deduction":
            return self.proportionate(base, d)

        if category == "policy_limit" and line is not None and line.head == "ambulance":
            cap = (self.policy or {}).get("limits", {}).get("road_ambulance_per_hospitalisation_inr")
            if cap is not None:
                expected = max(0.0, line.amount - cap)
                if abs(d.deducted - expected) <= 1:
                    return DeductionFinding(**base, category="policy_limit", verdict="fair",
                                            explanation=f"Road ambulance is covered up to {inr(cap)} per hospitalisation, so {inr(expected)} of the {inr(line.amount)} bill is correctly cut.",
                                            citations=self.clause("AMBULANCE"))
                over = d.deducted - expected
                return DeductionFinding(**base, category="policy_limit", verdict="challengeable", strength="strong", amount_challengeable=over,
                                        explanation=f"The ambulance limit is {inr(cap)}, so only {inr(expected)} should have been cut, not {inr(d.deducted)}.",
                                        citations=self.clause("AMBULANCE"))

        if category == "reasonable_customary":
            self.categories.add("reasonable_customary")
            return DeductionFinding(**base, category="reasonable_customary", verdict="needs_more_info", strength="moderate",
                                    explanation=(
                                        "The policy only pays what other hospitals or doctors in the same area would charge, but the letter gives no "
                                        "comparison or clause. Ask the insurer in writing for the local rates it used. For a network hospital, also ask "
                                        "whether the fee matches the tariff the insurer agreed with that hospital. If they can't show comparable rates, escalate."),
                                    citations=self.clause("MEDICAL-EXPENSES") + ["R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"])

        if category == "exclusion" and line is not None:
            if line.head == "investigations" and HISTOPATHOLOGY.search(line.description) and self.claim.admission.procedure:
                self.categories.add("not_in_lists")
                return DeductionFinding(**base, category="exclusion", verdict="challengeable", strength="strong", amount_challengeable=d.deducted,
                                        explanation=(
                                            f"This exclusion only covers tests that are not related or incidental to the treatment. Examining the tissue removed "
                                            f"during the {self.claim.admission.procedure.lower()} is part of that treatment."),
                                        citations=self.clause("7.1-EVAL") + ["R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"])
            return DeductionFinding(**base, category="exclusion", verdict="needs_more_info", strength="moderate",
                                    explanation="The insurer relies on an exclusion. Check that the exclusion is written in your policy and really applies to this item; ask the insurer to explain how.",
                                    citations=["R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS"] + no_clause)

        matches = match_items(line.description if line else d.description)
        if line is not None and line.head == "ambulance":
            matches = []  # ambulance is a covered benefit with its own limit, not a List I item
        if matches:
            m = matches[0]
            ids = [x.item_id for x in matches]
            listed = " and ".join(f"\"{x.item[:1].upper() + x.item[1:].lower()}\"" for x in matches)
            names = f"\"{line.description if line else d.description}\" is listed as {listed}, which"
            if m.list == "I":
                has_cover = any("consumable" in c.lower() for c in self.claim.policy.optional_covers)
                if has_cover:
                    self.categories.add("not_in_lists")
                    return DeductionFinding(**base, category="non_payable_item", verdict="challengeable", strength="strong",
                                            amount_challengeable=d.deducted, matched_item=m.item, citations=ids,
                                            explanation=f"{names} is a List I item, but your policy has a consumables add-on that covers it.")
                return DeductionFinding(**base, category="non_payable_item", verdict="fair", matched_item=m.item, citations=ids,
                                        explanation=f"{names} is in List I of your policy's Annexure-A (not covered). This deduction is correct.")
            where = {"II": "room charges", "III": "procedure charges", "IV": "cost of treatment"}[m.list]
            text = f"{names} is in List {m.list} of your policy's Annexure-A: it counts as part of the {where}, so it isn't paid as a separate line."
            if self.cashless_network:
                return DeductionFinding(**base, category="non_payable_item", verdict="fair_ask_hospital_to_absorb", matched_item=m.item, citations=ids,
                                        explanation=text + " Because this was cashless at a network hospital, you can ask the hospital to absorb it. That's a request, not a legal right.")
            return DeductionFinding(**base, category="non_payable_item", verdict="fair", matched_item=m.item, citations=ids,
                                    explanation=text + " The deduction is correct.")

        if category in ("non_payable", "unknown", "policy_limit"):
            if category == "non_payable":
                self.categories.add("not_in_lists")
                essential = line is not None and bool(MEDICALLY_ESSENTIAL.search(line.description))
                return DeductionFinding(**base, category="not_in_lists", verdict="challengeable", strength="strong" if essential else "moderate",
                                        amount_challengeable=d.deducted,
                                        explanation=(
                                            f"This item isn't in your policy's lists of non-payable items (Annexure-A, List I-IV)"
                                            f"{' and it is a medically necessary part of the surgery' if essential else ''}. "
                                            "An insurer can only deduct for exclusions actually written in the policy"
                                            f"{', and this letter cites no clause' if not cites_clause else ''}."),
                                        citations=self.clause("4.7-LISTS") + ["R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS"] + no_clause)
            return DeductionFinding(**base, category="unknown", verdict="needs_more_info", strength="weak",
                                    explanation="The reason given doesn't point to a policy clause or listed exclusion. Ask the insurer to name the exact clause.",
                                    citations=["R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE", "R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS"])

        return DeductionFinding(**base, category="unknown", verdict="needs_more_info", strength="weak",
                                explanation="ClaimBack couldn't match this deduction to a rule. Ask the insurer which clause it relies on.",
                                citations=["R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"])

    def proportionate_split(self, policy: dict, deducted_codes: set[str]) -> tuple[float, float, float] | None:
        """-> (eligible room rate, actual room rate, correct deduction) under a policy wording, or None if not computable."""
        limits = policy.get("limits", {})
        room_limit = limits.get("room_rent_per_day")
        rooms = [line for line in self.claim.bill_lines if line.head == "room"]
        if not room_limit or not rooms:
            return None
        eligible = min(self.claim.policy.sum_insured * room_limit["pct_of_sum_insured"] / 100, room_limit["max_inr"])
        actual = max(line.rate for line in rooms)
        if actual <= eligible:
            return eligible, actual, 0.0
        heads = set(policy["proportionate_deduction"].get("applies_to_bill_heads", []))
        base = sum(line.amount for line in self.claim.bill_lines if line.head in heads and line.code not in deducted_codes)
        return eligible, actual, round(base * (1 - eligible / actual))

    def proportionate(self, base: dict, d: Deduction) -> DeductionFinding:
        self.categories.add("proportionate_deduction")
        deducted_codes = {x.line_code for x in self.claim.decision.deductions if x.line_code}
        split = self.proportionate_split(self.policy, deducted_codes) if self.policy else None
        if split is None:
            return DeductionFinding(**base, category="proportionate_deduction", verdict="needs_more_info", strength="moderate",
                                    explanation="ClaimBack can't recompute this proportionate deduction without your policy wording and the room rent on the bill. Ask the insurer for the calculation and the clause.",
                                    citations=["R-POLICY-MUST-STATE-SUBLIMITS-PROPORTIONATE-DEDUCTIONS", "R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"])
        eligible, actual, correct = split
        prorata = self.clause("PRORATA")
        room = self.clause("4.1-ROOM")
        if correct == 0:
            return DeductionFinding(**base, category="proportionate_deduction", verdict="challengeable", strength="strong", amount_challengeable=d.deducted,
                                    explanation=f"Your room rent ({inr(actual)}/day) is within the policy limit ({inr(eligible)}/day), so no proportionate deduction applies.",
                                    citations=room + prorata)
        # the same bill under the other supported wordings - shows how much the exact wording matters
        for other_id, other in self.kb.policies.items():
            if other_id == self.pid:
                continue
            other_split = self.proportionate_split(other, deducted_codes)
            if other_split and other_split[2] > 0:
                self.alternate_wordings.append(AlternateWording(
                    policy_wording_id=other_id, insurer=other["insurer"], challengeable_amount=max(0.0, d.deducted - other_split[2]),
                    note=f"Under {other['insurer'].split(' Health')[0]}'s wording the correct deduction would be {inr(other_split[2])}."))
        heads = self.policy["proportionate_deduction"]["applies_to"]
        applies = set(self.policy["proportionate_deduction"].get("applies_to_bill_heads", []))
        head_names = {"pharmacy": "medicines", "investigations": "tests", "implant": "implants", "consumable": "consumables", "icu": "ICU charges",
                      "misc": "other charges", "ambulance": "ambulance", "room": "room rent", "nursing": "nursing", "doctor": "doctors' fees", "ot": "operation theatre"}
        exempt_on_bill = [head_names.get(line.head, line.head) for line in self.claim.bill_lines
                          if line.head not in applies and line.code not in deducted_codes]
        exempt = list(dict.fromkeys(exempt_on_bill)) or self.policy["proportionate_deduction"]["does_not_apply_to"]
        pct_paid = round(eligible / actual * 100, 1)
        if d.deducted <= correct + 1:
            return DeductionFinding(**base, category="proportionate_deduction", verdict="fair",
                                    explanation=f"Your room cost {inr(actual)}/day against a limit of {inr(eligible)}/day, so {pct_paid:g}% of {', '.join(heads)} is payable. The insurer's {inr(d.deducted)} is within the correct {inr(correct)}.",
                                    citations=room + prorata)
        over = d.deducted - correct
        return DeductionFinding(**base, category="proportionate_deduction", verdict="challengeable", strength="strong", amount_challengeable=over,
                                explanation=(
                                    f"Your room cost {inr(actual)}/day against a limit of {inr(eligible)}/day, so the policy lets the insurer pay {pct_paid:g}% of "
                                    f"{', '.join(heads[:-1])} and {heads[-1]}. That comes to a deduction of {inr(correct)}. The insurer cut {inr(d.deducted)}, which means it also "
                                    f"applied the cut to {' and '.join(exempt)}, which this clause doesn't allow. You can challenge {inr(over)}."),
                                citations=room + prorata + ["R-POLICY-MUST-STATE-SUBLIMITS-PROPORTIONATE-DEDUCTIONS", "R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS"])

    # ------------------------------------------------------------------------------------------------ claim-level checks

    def add_check(self, cid: str, issue: str, verdict: str, explanation: str, citations: list[str], strength: str | None = None, **computed):
        self.check_findings.append(CheckFinding(id=cid, issue=issue, verdict=verdict, strength=strength, explanation=explanation,
                                                citations=citations, computed=computed))

    def checks(self) -> None:
        c, dec = self.claim, self.claim.decision
        if dec.letter_type == "repudiation":
            self.repudiation_checks()

        if dec.letter_type == "settlement":
            unclear = [f for f in self.deduction_findings
                       if f.verdict in ("challengeable", "needs_more_info") and not CLAUSE_REFERENCE.search(f.insurer_reason)]
            if unclear:
                self.add_check("C-CLAUSE-REFERENCES", "Deduction letter does not cite policy clauses", "challengeable",
                               f"{plural(len(unclear), 'deduction')} only say{'s' if len(unclear) == 1 else ''} things like \"{unclear[0].insurer_reason}\". "
                               "When a claim is partly disallowed, the insurer must refer to the specific terms of the policy. Ask it to name the clause for each.",
                               ["R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"], "moderate", deductions=[f.id for f in unclear])

            if dec.co_payment is not None and self.copay_pct:
                admissible = dec.admissible_amount if dec.admissible_amount is not None else dec.amount_claimed - dec.total_deducted
                expected = round(admissible * self.copay_pct / 100)
                if abs(expected - dec.co_payment) <= 1:
                    self.add_check("C-COPAY", "Co-payment computation", "fair",
                                   f"The {self.copay_pct:g}% co-pay ({inr(dec.co_payment)}) was correctly applied to the admissible amount after deductions ({inr(admissible)}).",
                                   self.clause("9.5-COPAY"), admissible=admissible, co_payment=dec.co_payment)
                else:
                    self.add_check("C-COPAY", "Co-payment computation", "challengeable",
                                   f"A {self.copay_pct:g}% co-pay on the admissible {inr(admissible)} is {inr(expected)}, but the insurer took {inr(dec.co_payment)}.",
                                   self.clause("9.5-COPAY"), "strong", admissible=admissible, expected=expected, charged=dec.co_payment)

            self.room_rent_check()

        self.settlement_timeline_check()
        self.waiting_period_checks()

    def room_rent_check(self) -> None:
        if not self.policy or "proportionate_deduction" in self.categories:
            return
        split = self.proportionate_split(self.policy, set())
        if split and split[2] == 0:
            eligible, actual, _ = split
            self.add_check("C-ROOM-RENT", "Room rent", "fair",
                           f"{inr(actual)}/day doesn't exceed the eligible {inr(eligible)}/day, so no proportionate deduction applies.",
                           self.clause("4.1-ROOM"), actual_per_day=actual, eligible_per_day=eligible)

    def settlement_timeline_check(self) -> None:
        c, dec = self.claim, self.claim.decision
        if c.admission.claim_type != "reimbursement" or not dec.documents_received_date:
            return
        days = (dec.letter_date - dec.documents_received_date).days
        cites = self.clause("9.6-SETTLEMENT") + ["R-REIMBURSEMENT-SETTLEMENT-15-DAYS"]
        computed = dict(documents_received=dec.documents_received_date.isoformat(), decision_date=dec.letter_date.isoformat(), days_taken=days, allowed_days=15)
        if days <= 15:
            self.add_check("C-TIMELINE", "Settlement timeline", "fair",
                           f"Documents received {dec.documents_received_date:%d %b %Y}, decided {dec.letter_date:%d %b %Y}: {days} days, within the 15-day limit.", cites, **computed)
        else:
            self.add_check("C-TIMELINE", "Delayed decision - interest is due", "challengeable",
                           f"Documents were received on {dec.documents_received_date:%d %b %Y} and the decision came {days} days later, beyond the 15-day limit. "
                           "When the claim is paid, interest at the RBI bank rate + 2% is due from the date the claim was reported.",
                           cites + ["R-CLAIM-DELAY-INTEREST", "R-BANK-RATE-DEFINITION"], "strong", **computed)

    def waiting_period_checks(self) -> None:
        c = self.claim
        text = f"{c.admission.diagnosis} {c.admission.procedure or ''}"
        start = c.policy.continuous_cover_start or c.policy.first_inception
        if c.admission.is_accident:
            self.add_check("C-WAITING", "30-day and specific waiting periods", "not_applicable",
                           "Specific waiting periods don't apply to treatment needed because of an accident"
                           + (f", and the policy is {months_between(start, c.admission.admission_date)} months old, so the 30-day wait is over." if start else "."),
                           self.clause("6.3-SPECIFIC"))
            if SPORTS.search(text):
                self.add_check("C-SPORTS", "Hazardous or adventure sports exclusion", "not_applicable",
                               "This exclusion only applies to people taking part as professionals. A recreational sports injury isn't excluded, which is useful if the insurer raises it later.",
                               self.clause("7.6-SPORTS"))
            return
        if not self.policy or not start:
            return
        wp = self.policy.get("waiting_periods", {})
        months = months_between(start, c.admission.admission_date)
        for pattern, key in SPECIFIC_CONDITIONS:
            if not pattern.search(text):
                continue
            for required, conditions in ((24, wp.get("specific_24_months", [])), (36, wp.get("specific_36_months", []))):
                condition = next((x for x in conditions if key.lower() in x.lower()), None)
                if condition:
                    verdict = "not_applicable" if months >= required else "needs_more_info"
                    self.add_check("C-WAITING", f"Specific waiting period: {condition}", verdict,
                                   f"{condition} has a {required}-month waiting period. Continuous cover since {start:%d %b %Y} is {months} months at admission"
                                   + (", so the waiting period is complete." if months >= required else ", so the waiting period may still apply - check the insurer's reason."),
                                   self.clause("6.3-SPECIFIC") + ["R-SPECIFIC-WAITING-MAX-36M"], computed_months=months, required_months=required)
                    return

    def repudiation_checks(self) -> None:
        c, dec = self.claim, self.claim.decision
        reason = (dec.repudiation_reason or "").lower() + " " + " ".join(dec.clauses_cited).lower()
        start = c.policy.continuous_cover_start or c.policy.first_inception
        ported = bool(c.policy.continuous_cover_start and c.policy.first_inception and c.policy.continuous_cover_start < c.policy.first_inception)
        portability = ["R-PORTABILITY-CREDITS"] if ported else []

        if re.search(r"disclos|misrepresent|pre-?existing|excl\s*0?1\b", reason) and start:
            self.categories.add("non_disclosure")
            months = months_between(start, c.admission.admission_date)
            moratorium = (self.policy or {}).get("waiting_periods", {}).get("moratorium_months", 60)
            ped_months = (self.policy or {}).get("waiting_periods", {}).get("pre_existing_disease_months", 36)
            if months >= moratorium:
                self.add_check("C-MORATORIUM", "Non-disclosure after the moratorium", "challengeable",
                               f"Continuous cover from {start:%d %b %Y}{' (including the ported policy)' if ported else ''} to admission on {c.admission.admission_date:%d %b %Y} "
                               f"is {months} months, beyond the {moratorium}-month moratorium. After that, a claim can't be contested for non-disclosure or "
                               "misrepresentation except for established fraud, and the letter doesn't allege or prove fraud.",
                               self.clause("8-MORATORIUM") + ["R-MORATORIUM-60M"] + portability, "strong",
                               continuous_cover_start=start.isoformat(), admission_date=c.admission.admission_date.isoformat(), continuous_months=months, moratorium_months=moratorium)
            else:
                self.add_check("C-MORATORIUM", "Non-disclosure within the moratorium", "needs_more_info",
                               f"Continuous cover is {months} months, still inside the {moratorium}-month moratorium, so the insurer may contest non-disclosure. "
                               "It must show the proposal form explicitly asked about the condition.",
                               ["R-MORATORIUM-60M", "R-MATERIAL-INFORMATION-ONLY-WHAT-PROPOSAL-ASKED"], "moderate", continuous_months=months, moratorium_months=moratorium)
            if re.search(r"pre-?existing|excl\s*0?1\b", reason):
                verdict = "challengeable" if months >= ped_months else "needs_more_info"
                self.add_check("C-PED", "Pre-existing disease exclusion (Excl01)", verdict,
                               f"Even if the condition counts as pre-existing, the waiting period is {ped_months} months of continuous cover"
                               f"{', and portability credit counts' if ported else ''}. {months} months had passed"
                               + (". The insurer's real argument, that the condition wasn't declared, is the non-disclosure ground the moratorium bars." if months >= moratorium else "."),
                               self.clause("6.1-PED") + ["R-PED-WAITING-MAX-36M"] + portability + (self.clause("8-MORATORIUM") if months >= moratorium else []),
                               "strong" if months >= ped_months else "moderate")
            if months >= moratorium:
                self.add_check("C-PERMANENT-EXCLUSIONS", "Moratorium caveat - permanent exclusions", "not_applicable",
                               "The moratorium doesn't override permanent exclusions written in the policy. This rejection doesn't rely on one, so the caveat doesn't save it.",
                               ["R-MORATORIUM-PERMANENT-EXCLUSIONS-SURVIVE"])
            self.add_check("C-PROPOSAL-FORM", "What exactly the proposal form asked", "needs_more_info",
                           "Non-disclosure can only relate to information the proposal form explicitly asked for. Ask the insurer for a copy of the proposal form"
                           f"{' and the portability records' if ported else ''}.",
                           ["R-MATERIAL-INFORMATION-ONLY-WHAT-PROPOSAL-ASKED", "R-PROPOSAL-FORM-COPY-WITHIN-15-DAYS"], "moderate")
            fraud = self.clause("10.9-FRAUD")
            if fraud:
                self.add_check("C-GOOD-FAITH", "Good-faith misstatement", "challengeable",
                               "Fraud needs deliberate intent. Someone who didn't realise a controlled, long-standing condition had to be declared can rely on the good-faith protection in the policy.",
                               fraud, "moderate")

        if re.search(r"delay|late intimation|intimat|documents? (not|pending)|not submitted", reason):
            self.categories.add("delay_documents")
            self.add_check("C-DOCUMENTS-DELAY", "Rejection for delay or missing documents", "challengeable",
                           "A claim can't be rejected merely because documents are pending or the claim was reported late, and the policy allows delays for genuine reasons.",
                           ["R-NO-REJECTION-FOR-WANT-OF-DOCUMENTS-OR-DELAYED-INTIMATION"] + self.clause("9.4-CONDONE"), "strong")

        self.add_check("C-CRC-APPROVAL", "Repudiation approval", "needs_more_info",
                       "No claim may be rejected without approval from the insurer's Claims Review Committee. Ask the insurer to confirm that approval.",
                       ["R-REPUDIATION-NEEDS-CRC-APPROVAL"], "moderate")

    # ------------------------------------------------------------------------------------------------ report

    def not_payable_on_bill(self) -> float:
        total = 0.0
        for line in self.claim.bill_lines:
            if line.head != "ambulance" and match_items(line.description):
                total += line.amount
        return total

    def similar_cases(self) -> list[SimilarCase]:
        wanted = []
        for cat in sorted(self.categories):
            wanted += CATEGORY_CASES.get(cat, [])
        cases = [x for x in self.kb.cases if x["category"] in wanted]
        cases.sort(key=lambda x: str(x["decision_date"]), reverse=True)
        return [SimilarCase(case_id=x["id"], forum=x["forum"], decision_date=str(x["decision_date"]), decision=x["decision"], category=x["category"],
                            insurer_reason=x["insurer_reason"], reasoning=x["reasoning"], amount_awarded_inr=x.get("amount_awarded_inr"),
                            decided_before_2024_health_rules=x.get("decided_before_2024_health_rules", True), source_url=x["source_url"])
                for x in cases[:6]]

    def escalation(self, today: date, has_dispute: bool) -> tuple[list[EscalationStep], OmbudsmanOffice | None]:
        c = self.claim
        office = self.kb.ombudsman_office_for(c.policy.state, c.policy.city or c.admission.hospital_city)
        office_name = f"Insurance Ombudsman, {office['city'].title()}" if office else "the Insurance Ombudsman for your area"
        if not has_dispute:
            return [], (OmbudsmanOffice(city=office["city"], address=office.get("address"), email=office.get("email"), phone=office.get("phone")) if office else None)
        steps = [
            EscalationStep(step=1, title="Write to the insurer's grievance officer", due_date=today,
                           action="Send the complaint letter ClaimBack drafts, listing each disputed amount and the clause or rule behind it. Keep proof of sending.",
                           deadline_note=f"The insurer must acknowledge immediately and resolve it within 14 days, by {today + timedelta(days=14):%d %b %Y}.",
                           citations=["R-GRIEVANCE-ACK-IMMEDIATE-RESOLVE-14-DAYS", "R-OMBUDSMAN-PRECONDITION-APPROACH-INSURER-FIRST"]),
            EscalationStep(step=2, title="Register it on Bima Bharosa", due_date=today,
                           action="Also log the complaint on IRDAI's Bima Bharosa portal (bimabharosa.irdai.gov.in) so it's tracked.",
                           deadline_note="Optional, but it puts the complaint on IRDAI's record.", citations=["R-BIMA-BHAROSA-ONLINE-COMPLAINT"]),
            EscalationStep(step=3, title=f"Go to the {office_name}", due_date=today + timedelta(days=30),
                           action="If the insurer rejects your complaint, doesn't reply, or replies unsatisfactorily, file with the Ombudsman online at cioins.co.in. It's free.",
                           deadline_note="Possible after 30 days without a satisfactory reply. File within 1 year of the insurer's reply. Claims up to Rs 50 lakh.",
                           citations=["R-OMBUDSMAN-AFTER-30-DAYS-OR-UNSATISFACTORY-DECISION", "R-OMBUDSMAN-ONE-YEAR-LIMIT", "R-OMBUDSMAN-NO-FEE-FILING-MODES", "R-OMBUDSMAN-CLAIMS-UP-TO-50-LAKH"]),
            EscalationStep(step=4, title="Consumer commission (last resort)", due_date=None,
                           action="If the Ombudsman route doesn't work for you, a district consumer commission can hear the dispute. You can't pursue both for the same dispute.",
                           deadline_note="General information only; consider advice before filing.", citations=["R-OMBUDSMAN-BAR-IF-COURT-OR-FORUM-CASE"]),
        ]
        return steps, (OmbudsmanOffice(city=office["city"], address=office.get("address"), email=office.get("email"), phone=office.get("phone")) if office else None)

    def run(self, today: date | None = None) -> Report:
        c, dec = self.claim, self.claim.decision
        today = today or date.today()
        for n, d in enumerate(dec.deductions, 1):
            self.deduction_findings.append(self.analyze_deduction(n, d))
        self.checks()

        copay_factor = 1 - self.copay_pct / 100
        rejected = dec.letter_type == "repudiation"
        challengeable = sum(f.amount_challengeable for f in self.deduction_findings if f.verdict == "challengeable")
        needs_info = sum(f.deducted for f in self.deduction_findings if f.verdict == "needs_more_info")
        ask_hospital = sum(f.deducted for f in self.deduction_findings if f.verdict == "fair_ask_hospital_to_absorb")
        strong_rejection_challenge = rejected and any(ch.verdict == "challengeable" and ch.strength == "strong" for ch in self.check_findings)
        if rejected:
            admissible_if_accepted = dec.amount_claimed - self.not_payable_on_bill()
            challengeable = admissible_if_accepted if strong_rejection_challenge else 0.0
            needs_info = 0.0 if strong_rejection_challenge else dec.amount_claimed
        estimated = round(challengeable * copay_factor)

        totals = ReportTotals(claimed=dec.amount_claimed, paid=dec.amount_paid, total_deducted=dec.total_deducted if not rejected else dec.amount_claimed,
                              challengeable_amount=challengeable, needs_more_info_amount=needs_info, ask_hospital_amount=ask_hospital,
                              estimated_additional_payable=estimated, claim_rejected=rejected)
        has_dispute = challengeable > 0 or needs_info > 0 or any(ch.verdict == "challengeable" for ch in self.check_findings)
        steps, office = self.escalation(today, has_dispute)
        headline, summary = self.narrative(totals)

        cited = {cid for f in [*self.deduction_findings, *self.check_findings, *steps] for cid in f.citations}
        citations = {cid: cit for cid in sorted(cited) if (cit := self.kb.citation(cid))}
        return Report(
            generated_at=datetime.now(timezone.utc), policy_wording_id=self.pid,
            policy_wording_name=f"{self.policy['product']} (UIN {self.policy['uin']})" if self.policy else None,
            headline=headline, summary=summary, totals=totals, deduction_findings=self.deduction_findings, check_findings=self.check_findings,
            similar_cases=self.similar_cases(), escalation=steps, ombudsman_office=office, citations=citations,
            alternate_wordings=self.alternate_wordings,
        )

    def narrative(self, t: ReportTotals) -> tuple[str, str]:
        findings = self.deduction_findings
        n_total = len(findings)
        n_chal = sum(1 for f in findings if f.verdict == "challengeable")
        n_info = sum(1 for f in findings if f.verdict == "needs_more_info")
        n_hosp = sum(1 for f in findings if f.verdict == "fair_ask_hospital_to_absorb")
        copay = f" after the {self.copay_pct:g}% co-pay" if self.copay_pct else ""
        extra_checks = [ch for ch in self.check_findings if ch.verdict == "challengeable" and ch.id in ("C-TIMELINE", "C-COPAY")]

        if t.claim_rejected:
            if t.challengeable_amount > 0:
                grounds = {
                    "C-MORATORIUM": "it came after the 60-month moratorium, when non-disclosure can no longer be used",
                    "C-PED": "the pre-existing disease waiting period was long over",
                    "C-DOCUMENTS-DELAY": "a claim can't be rejected just for delays or pending documents",
                    "C-TIMELINE": "the decision was late, so interest is also due",
                }
                reasons = [grounds[ch.id] for ch in self.check_findings if ch.verdict == "challengeable" and ch.strength == "strong" and ch.id in grounds]
                listed = "; ".join(reasons[:-1]) + (f"; and {reasons[-1]}" if len(reasons) > 1 else reasons[-1])
                return (f"Your {inr(t.claimed)} claim was rejected, and the rejection doesn't hold up",
                        f"The rejection is weak because {listed}. If it's overturned, about {inr(t.estimated_additional_payable)} "
                        f"should be payable{copay}.")
            return (f"Your {inr(t.claimed)} claim was rejected: ask the insurer to justify it",
                    "ClaimBack found no clear-cut ground to overturn this rejection, but there are questions the insurer must answer.")

        parts = []
        if t.challengeable_amount > 0:
            headline = f"You can challenge {inr(t.challengeable_amount)} of the {inr(t.total_deducted)} deducted"
            parts.append(f"{n_chal} of {plural(n_total, 'deduction')} {'doesn' if n_chal == 1 else 'don'}'t hold up against your policy wording and IRDAI rules. "
                         f"If the insurer accepts, you could get about {inr(t.estimated_additional_payable)} more{copay}.")
        elif t.needs_more_info_amount > 0:
            headline = f"Ask your insurer to justify {inr(t.needs_more_info_amount)} of deductions"
        else:
            headline = "Your insurer's deductions look correct"
            parts.append(f"All {plural(n_total, 'deduction')} ({inr(t.total_deducted)}) match your policy wording, so there's nothing to challenge.")
        if n_info and t.needs_more_info_amount:
            parts.append(f"{inr(t.needs_more_info_amount)} across {plural(n_info, 'deduction')} needs the insurer to show its basis before you can judge it.")
        if n_hosp:
            parts.append(f"{inr(t.ask_hospital_amount)} ({plural(n_hosp, 'item')}) is part of room or procedure charges. The deduction is correct, but you can ask the hospital to waive it.")
        if extra_checks:
            parts.append(" ".join(ch.explanation for ch in extra_checks))
        return headline, " ".join(parts)


def analyze(claim: ClaimInput, today: date | None = None) -> Report:
    return Analysis(claim).run(today)

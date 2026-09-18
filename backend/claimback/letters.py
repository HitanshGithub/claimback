"""Complaint letters built directly from the report, so every point carries its clause or rule.

Claude (llm.letter) can polish the wording when Bedrock is enabled; this template is the reliable baseline.
"""

import re
from datetime import date

from .fmt import inr
from .knowledge import knowledge
from .models import ClaimInput, Letter, Report


def _cite(report: Report, ids: list[str]) -> str:
    """Group references by document: 'IRDAI Master Circular ..., 2024: Section 2, para 16.3; Section 1, Part B, V(3)(iii)(5)'."""
    groups: dict[str, list[str]] = {}
    for cid in ids:
        c = report.citations.get(cid)
        if not c:
            continue
        if c.kind == "policy_clause":
            doc, ref = "Policy wording", c.clause_ref
        elif c.kind == "rule":
            doc, ref = c.source, c.clause_ref
        else:
            doc, ref = "Policy wording", c.clause_ref
        refs = groups.setdefault(doc, [])
        if ref and ref not in refs:
            refs.append(ref)
    return "; ".join(f"{doc}: {', '.join(refs)}" for doc, refs in groups.items())


LETTER_VOICE = [
    ("your policy's", "the policy's"), ("Your policy's", "The policy's"), ("your policy", "the policy"), ("Your policy", "The policy"),
    ("this letter cites no clause", "your letter cites no clause"), ("the letter gives", "your letter gives"),
    ("the letter doesn't", "your letter doesn't"), ("Your room cost", "The room cost"), ("You can challenge", "I dispute"),
    ("The insurer's real argument", "Your real argument"),
]
DROP_SENTENCE = re.compile(r"^(Ask |If they can't|Check that|That's a request)")


def _letter_voice(text: str) -> str:
    """Turn an explanation written for the policyholder into an argument addressed to the insurer."""
    for old, new in LETTER_VOICE:
        text = text.replace(old, new)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(s for s in sentences if not DROP_SENTENCE.match(s))


def _points(claim: ClaimInput, report: Report) -> tuple[list[str], list[str]]:
    disputes, questions = [], []
    for f in report.deduction_findings:
        if f.verdict == "challengeable":
            disputes.append(f"{f.description}: {inr(f.amount_challengeable)} of the {inr(f.deducted)} deducted as \"{f.insurer_reason}\". "
                            f"{_letter_voice(f.explanation)} (Ref: {_cite(report, f.citations)})")
        elif f.verdict == "needs_more_info":
            questions.append(f"{f.description}: {inr(f.deducted)} deducted as \"{f.insurer_reason}\". {_letter_voice(f.explanation)} (Ref: {_cite(report, f.citations)})")
    for ch in report.check_findings:
        if ch.verdict == "challengeable":
            disputes.append(f"{ch.issue}: {_letter_voice(ch.explanation)} (Ref: {_cite(report, ch.citations)})")
        elif ch.verdict == "needs_more_info":
            asks = LETTER_ASKS.get(ch.id, _letter_voice(ch.explanation))
            questions.append(f"{ch.issue}: {asks} (Ref: {_cite(report, ch.citations)})")
    return disputes, questions


LETTER_ASKS = {
    "C-PROPOSAL-FORM": "please send a copy of the proposal form and portability records, and show which question the alleged non-disclosure relates to.",
    "C-CRC-APPROVAL": "please confirm that the Claims Review Committee approved this repudiation, with the date of approval.",
    "C-CLAUSE-REFERENCES": "please name the specific policy clause relied on for each deduction.",
}


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{i}. {text}" for i, text in enumerate(items, 1))


def grievance_letter(claim: ClaimInput, report: Report, today: date | None = None) -> Letter:
    today = today or date.today()
    p, a, d, t = claim.policy, claim.admission, claim.decision, report.totals
    disputes, questions = _points(claim, report)
    holder = p.holder_name or a.patient_name
    relief = (f"reconsider and settle the claim, paying about {inr(t.estimated_additional_payable)} after co-payment"
              if t.claim_rejected else
              f"pay the wrongly deducted {inr(t.challengeable_amount)} (about {inr(t.estimated_additional_payable)} after co-payment)")
    interest = any(ch.id == "C-TIMELINE" and ch.verdict == "challengeable" for ch in report.check_findings)
    decision_line = (f"repudiated the claim by letter dated {d.letter_date:%d %B %Y}" if t.claim_rejected
                     else f"settled the claim by letter dated {d.letter_date:%d %B %Y}, paying {inr(d.amount_paid)} against {inr(d.amount_claimed)} claimed")
    body = f"""Date: {today:%d %B %Y}

To
The Grievance Redressal Officer
{p.insurer_name}

Subject: Grievance against {'repudiation' if t.claim_rejected else 'deductions'} in claim no. {d.claim_number}, policy no. {p.policy_number}

Dear Sir/Madam,

I am writing about the above claim for the hospitalisation of {a.patient_name} at {a.hospital_name} from {a.admission_date:%d %B %Y} to {a.discharge_date:%d %B %Y} ({a.diagnosis}). Your office {decision_line}.

I have checked the decision against the policy wording{f' ({report.policy_wording_name})' if report.policy_wording_name else ''} and IRDAI's regulations, and I dispute the following:

{_numbered(disputes) if disputes else 'None.'}
"""
    if questions:
        body += f"""
In addition, please give me the basis for the following, with reference to the specific policy terms:

{_numbered(questions)}
"""
    body += f"""
I request you to {relief}{', together with interest at bank rate + 2% for the delayed decision' if interest else ''}, and to reply with reasons that refer to the specific terms of the policy. I understand IRDAI requires grievances to be acknowledged immediately and resolved within 14 days. If the grievance is not resolved, I will approach the Insurance Ombudsman under the Insurance Ombudsman Rules, 2017.

Enclosures: policy schedule, hospital bill, discharge summary, your {'repudiation' if t.claim_rejected else 'settlement'} letter dated {d.letter_date:%d %B %Y}.

Yours faithfully,
{holder}
Policy no. {p.policy_number}
"""
    return Letter(kind="grievance", to=f"Grievance Redressal Officer, {p.insurer_name}",
                  subject=f"Grievance: claim no. {d.claim_number}, policy no. {p.policy_number}", body=body, generated_by="template")


def ombudsman_letter(claim: ClaimInput, report: Report, today: date | None = None) -> Letter:
    today = today or date.today()
    p, a, d, t = claim.policy, claim.admission, claim.decision, report.totals
    office = report.ombudsman_office
    disputes, questions = _points(claim, report)
    amount = t.estimated_additional_payable
    rule = knowledge().rules.get("R-OMBUDSMAN-PRECONDITION-APPROACH-INSURER-FIRST", {})
    body = f"""Date: {today:%d %B %Y}

To
The Insurance Ombudsman
{office.city.title() if office else '[Ombudsman office for your area]'}{chr(10) + office.address if office and office.address else ''}{chr(10) + 'Email: ' + office.email if office and office.email else ''}

Subject: Complaint against {p.insurer_name} - claim no. {d.claim_number}, policy no. {p.policy_number}

Respected Sir/Madam,

1. Complainant: {p.holder_name or a.patient_name}, policyholder under policy no. {p.policy_number} ({p.product_name}) issued by {p.insurer_name.rstrip('.')}.

2. The claim: hospitalisation of {a.patient_name} at {a.hospital_name}, {a.hospital_city or ''}, from {a.admission_date:%d %B %Y} to {a.discharge_date:%d %B %Y} for {a.diagnosis}. Amount claimed: {inr(d.amount_claimed)}. Amount paid: {inr(d.amount_paid)}.

3. The insurer's decision: {'repudiation' if t.claim_rejected else 'partial settlement'} by letter dated {d.letter_date:%d %B %Y}.

4. I first represented to the insurer in writing on [date of your grievance] and [the insurer rejected it on (date) / did not reply within one month / replied on (date) and I am not satisfied]. ({rule.get('source_title', 'Insurance Ombudsman Rules, 2017')}, {rule.get('clause_ref', 'Rule 14(3)')})

5. Grounds of complaint:

{_numbered(disputes) if disputes else 'See enclosed grievance.'}
"""
    if questions:
        body += f"""
6. The insurer has not given the basis for:

{_numbered(questions)}
"""
    body += f"""
Relief sought: direct the insurer to pay {inr(amount)}{' (the claim after co-payment)' if t.claim_rejected else ' (the wrongly deducted amount after co-payment)'} with interest at bank rate + 2% from the date the claim was reported.

I confirm that the same dispute is not pending before, and has not been decided by, any court, consumer forum or arbitrator.

Enclosures: policy schedule and wording, hospital bill, discharge summary, insurer's letter dated {d.letter_date:%d %B %Y}, my grievance and the insurer's reply (if any).

Yours faithfully,
{p.holder_name or a.patient_name}
[Address, phone, email]
"""
    return Letter(kind="ombudsman", to=f"Insurance Ombudsman, {office.city.title()}" if office else "Insurance Ombudsman",
                  subject=f"Complaint against {p.insurer_name}: claim no. {d.claim_number}", body=body, generated_by="template")

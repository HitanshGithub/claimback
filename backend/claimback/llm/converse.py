"""Bedrock Converse provider - works with any Bedrock model (Ministral 3, Mistral Large, Nova, ...).

Differences from the Anthropic path that shape this code:
- these models take images, not PDFs, so PDF pages are rendered to PNGs first
- structured output comes from a forced tool call, not output_format
- small models do much better on several small schemas than one large one, so extraction is split into
  three calls (policy + admission, bill lines, insurer decision) against only the relevant documents
"""

import io
import json
import logging
import re
from typing import Any

import boto3
from pydantic import BaseModel, Field, ValidationError

from ..config import settings
from ..engine.matcher import match_items
from ..knowledge import knowledge
from ..models import Admission, BillLine, ClaimInput, InsurerDecision, Letter, PolicyInfo, Report

log = logging.getLogger(__name__)

MAX_PDF_PAGES = 8
RENDER_SCALE = 150 / 72  # 150 dpi keeps small print readable


def client():
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


# ---------------------------------------------------------------------------------------------- documents

def pdf_to_images(data: bytes) -> list[bytes]:
    import pypdfium2

    images = []
    pdf = pypdfium2.PdfDocument(data)
    for page in list(pdf)[:MAX_PDF_PAGES]:
        buffer = io.BytesIO()
        page.render(scale=RENDER_SCALE).to_pil().save(buffer, format="png")
        images.append(buffer.getvalue())
    return images


def document_blocks(documents: list[tuple[str, str, str, bytes]], kinds: set[str] | None = None) -> list[dict]:
    """documents: (kind, filename, content_type, bytes) -> Converse content blocks."""
    blocks: list[dict] = []
    for kind, filename, content_type, data in documents:
        if kinds and kind not in kinds:
            continue
        blocks.append({"text": f"--- {kind.replace('_', ' ')} ({filename}) ---"})
        if content_type == "application/pdf":
            for page_number, image in enumerate(pdf_to_images(data), 1):
                blocks.append({"text": f"page {page_number}"})
                blocks.append({"image": {"format": "png", "source": {"bytes": image}}})
        else:
            fmt = {"image/jpeg": "jpeg", "image/png": "png"}[content_type]
            blocks.append({"image": {"format": fmt, "source": {"bytes": data}}})
    return blocks


# ---------------------------------------------------------------------------------------------- structured output

def inline_refs(schema: dict) -> dict:
    """Resolve $ref/$defs - Bedrock tool schemas are plain JSON Schema without definitions."""
    defs = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].rsplit("/", 1)[-1]
                return resolve({k: v for k, v in defs[name].items()})
            return {k: resolve(v) for k, v in node.items() if k not in ("default",)}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


def structured(model: str, system: str, content: list[dict], output: type[BaseModel], tool_name: str,
               max_tokens: int = 4096, attempts: int = 2):
    """Force a tool call whose input matches `output`, and validate it."""
    schema = inline_refs(output.model_json_schema())
    tool_config = {
        "tools": [{"toolSpec": {"name": tool_name, "description": f"Record the extracted {tool_name.replace('_', ' ')}",
                                "inputSchema": {"json": schema}}}],
        "toolChoice": {"tool": {"name": tool_name}},
    }
    messages = [{"role": "user", "content": content}]
    last_error = None
    for attempt in range(attempts):
        response = client().converse(
            modelId=model, system=[{"text": system}], messages=messages, toolConfig=tool_config,
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
        )
        blocks = response["output"]["message"]["content"]
        tool_use = next((b["toolUse"] for b in blocks if "toolUse" in b), None)
        if tool_use is None:
            last_error = "the model did not call the tool"
        else:
            try:
                return output.model_validate(tool_use["input"])
            except ValidationError as exc:
                last_error = exc.errors(include_url=False)
                log.warning("%s: validation failed on attempt %s: %s", tool_name, attempt + 1, str(last_error)[:400])
        if attempt + 1 < attempts:  # show the model its own output and the errors
            messages = messages + [
                {"role": "assistant", "content": blocks},
                {"role": "user", "content": [{"toolResult": {
                    "toolUseId": tool_use["toolUseId"] if tool_use else "none",
                    "content": [{"text": f"That was rejected: {json.dumps(last_error, default=str)[:800]}. Call {tool_name} again, corrected."}],
                    "status": "error"}}]},
            ]
    raise RuntimeError(f"{tool_name} failed after {attempts} attempts: {str(last_error)[:300]}")


# ---------------------------------------------------------------------------------------------- extraction

class PolicyAndAdmission(BaseModel):
    # the as-printed strings come first so they are filled in before the numbers they correct
    sum_insured_as_printed: str = Field(default="", description="The sum insured copied character for character as printed, e.g. '5,00,000' or 'Rs. 3,00,000.00'")
    cumulative_bonus_as_printed: str = Field(default="", description="The cumulative bonus as printed, or empty if there is none")
    policy: PolicyInfo
    admission: Admission


class BillLines(BaseModel):
    bill_lines: list[BillLine]


def rupees(printed: str) -> float | None:
    """'Rs. 5,00,000.00' -> 500000.0 - once we parse the printed text ourselves, digit grouping can't be misread."""
    cleaned = re.sub(r"[^0-9.]", "", printed or "")
    if not cleaned or cleaned.count(".") > 1:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


EXTRACT_SYSTEM = """You read Indian health insurance claim documents shown as images. Copy values exactly as printed:
never calculate, guess or round. Use null for optional fields that are not shown. Dates are YYYY-MM-DD.

Amounts are rupees as plain numbers. Indian documents group digits as lakhs, not thousands, so count the digits:
  5,00,000    -> 500000     (five lakh, NOT five million)
  1,39,700.00 -> 139700
  2,59,100    -> 259100
  10,00,000   -> 1000000    (ten lakh)
Never add or drop a zero."""


def extract_claim(documents: list[tuple[str, str, str, bytes]], policy_wording_id: str | None) -> ClaimInput:
    model = settings.model_extract
    wordings = "\n".join(f"- {w['id']}: {w['product']}" for w in knowledge().wordings())

    policy_admission: PolicyAndAdmission = structured(
        model, EXTRACT_SYSTEM,
        document_blocks(documents, {"policy_schedule", "discharge_summary", "insurer_letter"}) + [{"text": (
            "Extract the policy and the hospital admission.\n"
            f"policy_wording_id must be one of these ids, or null if the product does not match:\n{wordings}\n"
            "Always fill sum_insured_as_printed (and cumulative_bonus_as_printed) by copying those amounts exactly as they "
            "appear on the schedule, commas and all, as well as filling in the numeric fields.\n"
            "continuous_cover_start is the start of continuous cover including any ported earlier policy; "
            "first_inception is the first policy with the current insurer. "
            "network_hospital is true only if the documents say so. is_accident is true only if the treatment followed an accident."
        )}],
        PolicyAndAdmission, "record_policy_and_admission", max_tokens=3000)

    bill: BillLines = structured(
        model, EXTRACT_SYSTEM,
        document_blocks(documents, {"hospital_bill"}) + [{"text": (
            "List every line of this hospital bill. Use the code printed on the bill, or L01, L02 ... in order if there is none. "
            "head must be one of: room, icu, nursing, doctor, ot, implant, pharmacy, investigations, consumable, misc, ambulance, other. "
            "Do not include sub-totals or the gross total."
        )}],
        BillLines, "record_bill_lines", max_tokens=6000)

    decision: InsurerDecision = structured(
        model, EXTRACT_SYSTEM,
        document_blocks(documents, {"insurer_letter"}) + [{"text": (
            "Extract the insurer's decision. One deduction entry per row of the deduction table; copy the reason word for word. "
            "line_code is the matching bill line code where you can tell, otherwise null (for example a proportionate / room-rent deduction "
            "that covers several heads). For a repudiation letter set letter_type to repudiation, put the full reason in repudiation_reason, "
            "amount_paid 0, and leave deductions empty.\n"
            "Bill line codes available: " + ", ".join(f"{l.code} ({l.description[:40]})" for l in bill.bill_lines)
        )}],
        InsurerDecision, "record_insurer_decision", max_tokens=4000)

    # trust the printed text over the number the model computed: small models misread lakh digit grouping
    for field, printed in (("sum_insured", policy_admission.sum_insured_as_printed),
                           ("cumulative_bonus", policy_admission.cumulative_bonus_as_printed)):
        parsed = rupees(printed)
        current = getattr(policy_admission.policy, field)
        if parsed is not None and parsed != current:
            log.info("%s: using %s parsed from %r instead of %s", field, parsed, printed, current)
            setattr(policy_admission.policy, field, parsed)
    if policy_admission.admission.network_hospital is None:
        policy_admission.admission.network_hospital = False
    if policy_wording_id:
        policy_admission.policy.policy_wording_id = policy_wording_id
    return ClaimInput(policy=policy_admission.policy, admission=policy_admission.admission,
                      bill_lines=bill.bill_lines, decision=decision)


# ---------------------------------------------------------------------------------------------- review

class ReviewDecision(BaseModel):
    verdict: str  # challengeable | needs_more_info | fair | fair_ask_hospital_to_absorb
    strength: str  # strong | moderate | weak
    amount_challengeable: float
    explanation: str
    citation_ids: list[str]


REVIEW_SYSTEM = """You review one deduction from an Indian health insurance claim that a rule engine could not settle.
Decide using ONLY the reference material given to you:
- challengeable: the material shows the deduction is wrong (set amount_challengeable)
- fair: the material shows it is right
- fair_ask_hospital_to_absorb: it is a List II-IV item on a cashless claim at a network hospital
- needs_more_info: the material does not settle it - say exactly what the insurer must show
Cite only ids listed under "Citations you may use". Never invent a rule, amount or id. Write two or three short
sentences for a worried family member, no jargon."""


def review(claim: ClaimInput, report: Report) -> tuple[Report, bool]:
    open_findings = [f for f in report.deduction_findings if f.verdict == "needs_more_info"][:5]
    if not open_findings:
        return report, False
    kb = knowledge()
    changed = False
    for finding in open_findings:
        passages = kb.search(f"{finding.description} {finding.insurer_reason}", k=4)
        allowed = {c for c in finding.citations}
        allowed |= {m.item_id for m in match_items(finding.description)}
        allowed |= {r["id"] for r in kb.rules.values() if r["topic"] in ("rejection_letter", "other", "proportionate_deduction", "room_rent")}
        policy = kb.policy(report.policy_wording_id)
        if policy:
            allowed |= {c["id"] for c in policy["clauses"]}
        citations = "\n".join(f"- {cid}: {c.title} | {(c.quote or '')[:220]}" for cid in sorted(allowed) if (c := kb.citation(cid)))
        prompt = [{"text": json.dumps({
            "claim_type": claim.admission.claim_type, "network_hospital": claim.admission.network_hospital,
            "diagnosis": claim.admission.diagnosis, "procedure": claim.admission.procedure,
            "deduction": {"item": finding.description, "billed": finding.billed, "deducted": finding.deducted,
                          "insurer_reason": finding.insurer_reason},
        }, default=str)},
            {"text": f"Reference material:\n{chr(10).join(p.text[:700] for p in passages)}"},
            {"text": f"Citations you may use:\n{citations}"}]
        try:
            decision = structured(settings.model_review, REVIEW_SYSTEM, prompt, ReviewDecision, "record_review", max_tokens=1200)
        except Exception:
            log.exception("review failed for %s", finding.id)
            continue
        valid = [c for c in decision.citation_ids if c in allowed and kb.citation(c)]
        if not valid or decision.verdict not in ("challengeable", "needs_more_info", "fair", "fair_ask_hospital_to_absorb"):
            continue
        finding.verdict = decision.verdict
        finding.strength = decision.strength if decision.strength in ("strong", "moderate", "weak") else "moderate"
        finding.amount_challengeable = min(max(decision.amount_challengeable, 0), finding.deducted) if decision.verdict == "challengeable" else 0
        finding.explanation = decision.explanation
        finding.citations = valid
        for cid in valid:
            report.citations.setdefault(cid, kb.citation(cid))
        changed = True
    return report, changed


# ---------------------------------------------------------------------------------------------- letter

POLISH_SYSTEM = """You edit a complaint letter from an Indian policyholder to their health insurer or the Insurance
Ombudsman. Keep every amount, date, claim and policy number, quoted reason and reference exactly as given, keep the
structure and keep [square bracket] placeholders. Do not add facts or legal claims.

Return the letter as plain text only: no markdown, no ** bold **, no headings, no commentary, and do not repeat the
subject line at the top. Start with the date line, exactly as the draft does."""


def polish(letter: Letter) -> Letter:
    response = client().converse(
        modelId=settings.model_letter,
        system=[{"text": POLISH_SYSTEM}],
        messages=[{"role": "user", "content": [{"text": f"Subject: {letter.subject}\n\n{letter.body}"}]}],
        inferenceConfig={"maxTokens": 4000, "temperature": 0.2},
    )
    body = "".join(b.get("text", "") for b in response["output"]["message"]["content"]).strip()
    body = re.sub(r"\*\*(.+?)\*\*", r"\1", body)  # models like to bold things; the UI shows plain text
    body = re.sub(r"(?m)^#{1,6}\s+", "", body)
    if body.lower().startswith("subject:"):  # a repeated subject line, the draft already has one
        body = body.split(chr(10), 1)[1].lstrip()
    if len(body) < len(letter.body) * 0.6:  # a short reply means it summarised instead of editing
        log.warning("letter polish returned %s chars vs %s - keeping the template", len(body), len(letter.body))
        return letter
    return letter.model_copy(update={"body": body, "generated_by": "ai"})

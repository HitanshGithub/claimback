"""Read the claimant's documents (PDF or photo) into a ClaimInput with Claude's structured output."""

import base64

from ..config import settings
from ..knowledge import knowledge
from ..models import ClaimInput
from . import check_refusal, client

SYSTEM = """You extract data from Indian health insurance claim documents: a policy schedule, a hospital's final bill, \
the insurer's settlement or repudiation letter, and optionally a discharge summary.

Rules:
- Copy amounts, dates, codes and the insurer's reasons exactly as printed. Never compute or guess a value that is not on \
the documents; use null where a field is optional and absent.
- bill_lines: one entry per billed line. Use the code printed on the bill; if there is none, number them L01, L02, ... \
in order. Choose the closest head for each line (room, icu, nursing, doctor, ot, implant, pharmacy, investigations, \
consumable, misc, ambulance, other).
- decision.deductions: one entry per row of the insurer's deduction table. line_code is the matching bill line code, or \
null when the deduction covers several heads (for example a proportionate / room-rent deduction). reason is the insurer's \
wording verbatim.
- policy.continuous_cover_start is the start of continuous cover including any ported or migrated earlier policy; \
policy.first_inception is the first policy with the current insurer.
- admission.network_hospital is true only if the documents say the hospital is in the insurer's network or the claim was \
cashless at a network hospital.
- admission.is_accident is true only if the documents say the treatment followed an accident or injury.
- Documents may be photos taken on a phone: read carefully, and prefer the printed totals when a digit is unclear."""


def _block(kind: str, filename: str, content_type: str, data: bytes) -> list[dict]:
    encoded = base64.standard_b64encode(data).decode("ascii")
    label = {"type": "text", "text": f"Document: {kind.replace('_', ' ')} ({filename})"}
    if content_type == "application/pdf":
        return [label, {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": encoded}}]
    return [label, {"type": "image", "source": {"type": "base64", "media_type": content_type, "data": encoded}}]


def extract_claim(documents: list[tuple[str, str, str, bytes]], policy_wording_id: str | None) -> ClaimInput:
    """documents: (kind, filename, content_type, bytes)"""
    wordings = "\n".join(f"- {w['id']}: {w['product']} (UIN {w['uin']})" for w in knowledge().wordings())
    content: list[dict] = []
    for kind, filename, content_type, data in documents:
        content += _block(kind, filename, content_type, data)
    content.append({"type": "text", "text": (
        "Extract the claim from these documents.\n"
        f"Supported policy wordings (set policy.policy_wording_id to one of these ids only if the schedule's insurer and product match, else null):\n{wordings}"
    )})
    message = client().messages.parse(
        model=settings.model_id,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": content}],
        output_format=ClaimInput,
    )
    check_refusal(message)
    claim = message.parsed_output
    if policy_wording_id:
        claim.policy.policy_wording_id = policy_wording_id
    return claim

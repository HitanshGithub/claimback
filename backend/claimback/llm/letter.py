"""Claude polishes the template letter without changing its facts, amounts or references."""

from pydantic import BaseModel

from ..config import settings
from ..models import Letter
from . import check_refusal, client

SYSTEM = """You edit complaint letters that Indian policyholders send to their health insurer or the Insurance Ombudsman. \
Make the draft clear, firm and polite. Keep every amount, date, claim/policy number, quoted reason and reference \
exactly as given, keep the structure (numbered grounds, relief sought, enclosures) and keep placeholders in [square \
brackets] for the policyholder to fill in. Do not add new legal claims, rules or facts."""


class LetterDraft(BaseModel):
    subject: str
    body: str


def polish(letter: Letter) -> Letter:
    # the API Lambda has ~29 s; on timeout the caller falls back to the template letter
    message = client().with_options(timeout=20.0, max_retries=0).messages.parse(
        model=settings.model_id,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Subject: {letter.subject}\n\n{letter.body}"}],
        output_format=LetterDraft,
    )
    check_refusal(message)
    draft = message.parsed_output
    return letter.model_copy(update={"subject": draft.subject, "body": draft.body, "generated_by": "claude"})

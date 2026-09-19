"""Claude or any Bedrock model, chosen by CLAIMBACK_LLM_PROVIDER.

"anthropic" uses the Anthropic SDK's Bedrock client (Claude models).
"converse" uses Bedrock's Converse API (Ministral 3, Mistral Large, Nova, ... - see converse.py).
"""

from functools import lru_cache

from ..config import settings
from ..models import ClaimInput, Letter, Report


@lru_cache(maxsize=1)
def client():
    """Anthropic SDK client for Claude on Bedrock.

    "mantle" is the Messages-API endpoint (not available in every region - it 404s in ap-south-1); "invoke" is the
    bedrock-runtime InvokeModel path, which needs an inference-profile model id such as global.anthropic.claude-opus-5.
    """
    from anthropic import AnthropicBedrock, AnthropicBedrockMantle

    if settings.bedrock_client == "mantle":
        return AnthropicBedrockMantle(aws_region=settings.aws_region)
    return AnthropicBedrock(aws_region=settings.aws_region)


class ModelRefused(RuntimeError):
    pass


def check_refusal(message) -> None:
    if message.stop_reason == "refusal":
        category = getattr(message.stop_details, "category", None) if message.stop_details else None
        raise ModelRefused(f"Claude declined this request (category: {category})")


def _provider():
    if settings.llm_provider == "anthropic":
        from . import extract as anthropic_extract, letter as anthropic_letter, review as anthropic_review

        return anthropic_extract.extract_claim, anthropic_review.review, anthropic_letter.polish
    from . import converse

    return converse.extract_claim, converse.review, converse.polish


def extract_claim(documents: list[tuple[str, str, str, bytes]], policy_wording_id: str | None) -> ClaimInput:
    return _provider()[0](documents, policy_wording_id)


def review(claim: ClaimInput, report: Report) -> tuple[Report, bool]:
    return _provider()[1](claim, report)


def polish(letter: Letter) -> Letter:
    return _provider()[2](letter)

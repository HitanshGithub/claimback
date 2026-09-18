"""Claude on Amazon Bedrock (enabled with CLAIMBACK_LLM=bedrock)."""

from functools import lru_cache

from anthropic import AnthropicBedrock, AnthropicBedrockMantle

from ..config import settings


@lru_cache(maxsize=1)
def client() -> AnthropicBedrock | AnthropicBedrockMantle:
    """Bedrock client for Claude.

    "mantle" is the Messages-API Bedrock endpoint (preferred, but not available in every region - it 404s in
    ap-south-1). "invoke" is the bedrock-runtime InvokeModel path, which works wherever the model does; it needs a
    model id with an inference-profile prefix such as global.anthropic.claude-opus-5.
    """
    if settings.bedrock_client == "mantle":
        return AnthropicBedrockMantle(aws_region=settings.aws_region)
    return AnthropicBedrock(aws_region=settings.aws_region)


class ModelRefused(RuntimeError):
    pass


def check_refusal(message) -> None:
    if message.stop_reason == "refusal":
        category = getattr(message.stop_details, "category", None) if message.stop_details else None
        raise ModelRefused(f"Claude declined this request (category: {category})")

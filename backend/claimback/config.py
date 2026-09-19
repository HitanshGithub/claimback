"""Runtime configuration from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    llm: str  # "offline" | "bedrock"
    storage: str  # "local" | "aws"
    data_dir: Path
    knowledge_dir: Path
    samples_dir: Path
    local_store_dir: Path
    aws_region: str
    llm_provider: str  # "anthropic" (Claude via the Anthropic SDK) | "converse" (any Bedrock model)
    bedrock_client: str  # "invoke" (bedrock-runtime, works in every region) | "mantle" (Messages API endpoint)
    model_id: str  # Claude model for the anthropic provider
    model_extract: str  # converse provider: reading documents (needs vision)
    model_review: str  # converse provider: reviewing unresolved deductions
    model_letter: str  # converse provider: polishing letters
    knowledge_base_id: str | None
    table_name: str | None
    bucket_name: str | None
    state_machine_arn: str | None
    step_delay_seconds: float


def load_settings() -> Settings:
    env = os.environ.get
    return Settings(
        llm=env("CLAIMBACK_LLM", "offline"),
        storage=env("CLAIMBACK_STORAGE", "local"),
        data_dir=Path(env("CLAIMBACK_DATA_DIR", str(REPO_ROOT / "data"))),
        knowledge_dir=Path(env("CLAIMBACK_KNOWLEDGE_DIR", str(REPO_ROOT / "knowledge-base"))),
        samples_dir=Path(env("CLAIMBACK_SAMPLES_DIR", str(REPO_ROOT / "samples"))),
        local_store_dir=Path(env("CLAIMBACK_LOCAL_STORE", str(REPO_ROOT / "backend" / ".claims"))),
        aws_region=env("CLAIMBACK_AWS_REGION", env("AWS_REGION", "ap-south-1")),
        llm_provider=env("CLAIMBACK_LLM_PROVIDER", "converse"),
        bedrock_client=env("CLAIMBACK_BEDROCK_CLIENT", "invoke"),
        model_id=env("CLAIMBACK_MODEL_ID", "global.anthropic.claude-opus-5"),
        model_extract=env("CLAIMBACK_MODEL_EXTRACT", "mistral.ministral-3-14b-instruct"),
        model_review=env("CLAIMBACK_MODEL_REVIEW", "mistral.ministral-3-14b-instruct"),
        model_letter=env("CLAIMBACK_MODEL_LETTER", "mistral.ministral-3-8b-instruct"),
        knowledge_base_id=env("CLAIMBACK_KB_ID"),
        table_name=env("CLAIMBACK_TABLE"),
        bucket_name=env("CLAIMBACK_BUCKET"),
        state_machine_arn=env("CLAIMBACK_STATE_MACHINE_ARN"),
        # small pause between local pipeline steps so the progress screen is readable in demos
        step_delay_seconds=float(env("CLAIMBACK_STEP_DELAY", "0.6")),
    )


settings = load_settings()

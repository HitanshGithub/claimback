"""AWS Lambda entry points."""

from mangum import Mangum

from .api import app
from .pipeline import run_step

api_handler = Mangum(app, lifespan="off")


def step_handler(event, context):
    """Step Functions task: {"claim_id": ..., "step": ...} -> same event, so states can chain."""
    run_step(event["claim_id"], event["step"])
    return {"claim_id": event["claim_id"]}


def fail_handler(event, context):
    """Step Functions catch-all: make sure a claim never stays 'processing' forever."""
    from .storage import storage

    claim = storage().get_claim(event["claim_id"])
    if claim and claim.status == "processing":
        claim.status = "failed"
        claim.error = claim.error or "Processing stopped unexpectedly. Please try again."
        storage().save_claim(claim)
    return {"claim_id": event["claim_id"], "status": "failed"}

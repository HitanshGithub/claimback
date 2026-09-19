"""The analysis pipeline, one step at a time.

Locally the steps run in a background thread (LocalRunner). Deployed, each step is a Step Functions task that calls
step_handler with {"claim_id", "step"} - the same run_step function.
"""

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import settings
from .engine.analyze import analyze
from .models import Claim, ClaimDocument, ClaimInput, ProgressStep, StepName
from .storage import Storage, load_json, storage

log = logging.getLogger(__name__)

STEPS: list[tuple[StepName, str]] = [
    ("read_documents", "Reading your documents"),
    ("check_items", "Checking every deduction against the policy's non-payable lists"),
    ("check_policy", "Checking your policy wording"),
    ("check_rules", "Checking IRDAI rules and deadlines"),
    ("similar_cases", "Finding similar Ombudsman and court decisions"),
    ("ai_review", "AI reviews anything the rules can't settle"),
    ("write_report", "Writing your report"),
]


def model_label() -> str:
    """Friendly name of the model doing the AI work, e.g. 'Ministral 3 14B' or 'Claude Opus 5'."""
    model = settings.model_id if settings.llm_provider == "anthropic" else settings.model_extract
    name = model.split(".", 1)[-1].replace("-instruct", "").replace("-", " ")
    return name.title().replace("Claude", "Claude").replace("Ministral 3 14B", "Ministral 3 14B")


def new_claim(source: str, title: str, sample_id: str | None = None) -> Claim:
    return Claim(
        id=uuid.uuid4().hex[:12], created_at=datetime.now(timezone.utc), status="processing", source=source, sample_id=sample_id,
        title=title, progress=[ProgressStep(name=name, label=label) for name, label in STEPS],
    )


def sample_folder(sample_id: str) -> Path:
    index = load_json(settings.samples_dir / "index.json")
    entry = next(s for s in index if s["scenario_id"] == sample_id)
    return settings.samples_dir.parent / entry["folder"]


def _set(claim: Claim, name: str, status: str, detail: str | None = None) -> None:
    for step in claim.progress:
        if step.name == name:
            step.status = status
            if detail is not None:
                step.detail = detail


def run_step(claim_id: str, name: StepName, store: Storage | None = None) -> Claim:
    store = store or storage()
    claim = store.get_claim(claim_id)
    _set(claim, name, "running")
    store.save_claim(claim)
    try:
        detail, status = _STEP_FUNCS[name](claim, store)
        _set(claim, name, status, detail)
    except Exception as exc:  # surface the failure on the claim so the UI can show it
        log.exception("step %s failed for claim %s", name, claim_id)
        _set(claim, name, "failed", str(exc)[:300])
        claim.status = "failed"
        claim.error = f"{dict(STEPS)[name]} failed: {exc}"
        store.save_claim(claim)
        raise
    store.save_claim(claim)
    return claim


def _read_documents(claim: Claim, store: Storage) -> tuple[str, str]:
    if claim.source == "sample":
        claim.claim_input = ClaimInput.model_validate(load_json(sample_folder(claim.sample_id) / "claim_input.json"))
        source = "Sample documents"
    else:
        if settings.llm != "bedrock":
            raise RuntimeError("Reading uploaded documents needs a model on Amazon Bedrock, which is not enabled.")
        from .llm import extract_claim

        docs = [(d.kind, d.filename, d.content_type, store.read_document(claim.id, d)) for d in claim.documents]
        claim.claim_input = extract_claim(docs, claim.policy_wording_id)
        a = claim.claim_input.admission
        claim.title = f"{a.hospital_name} - {a.diagnosis}"
        source = f"Read by {model_label()}"
    c = claim.claim_input
    return f"{source}: {len(c.bill_lines)} bill lines, {len(c.decision.deductions)} deductions", "done"


def _check_items(claim: Claim, store: Storage) -> tuple[str, str]:
    claim.report = analyze(claim.claim_input)
    findings = claim.report.deduction_findings
    matched = sum(1 for f in findings if f.matched_item)
    if not findings:
        return "No line-item deductions: the insurer rejected the whole claim", "done"
    return f"{len(findings)} deductions checked, {matched} found in the policy's lists", "done"


def _check_policy(claim: Claim, store: Storage) -> tuple[str, str]:
    r = claim.report
    if not r.policy_wording_id:
        return "Policy wording not supported yet: judged on IRDAI rules only", "done"
    return f"Checked against {r.policy_wording_name}", "done"


def _check_rules(claim: Claim, store: Storage) -> tuple[str, str]:
    r = claim.report
    rules = sum(1 for cid in r.citations.values() if cid.kind == "rule")
    return f"{len(r.check_findings)} claim-level checks, {rules} IRDAI rules cited", "done"


def _similar_cases(claim: Claim, store: Storage) -> tuple[str, str]:
    n = len(claim.report.similar_cases)
    return (f"{n} similar decision{'s' if n != 1 else ''} found" if n else "No close match needed: nothing to dispute"), "done"


def _ai_review(claim: Claim, store: Storage) -> tuple[str, str]:
    if settings.llm != "bedrock":
        return "Off in this local build (rule engine only)", "skipped"
    if not any(f.verdict == "needs_more_info" for f in claim.report.deduction_findings):
        return "Nothing left unresolved", "skipped"
    try:
        from .llm import review

        claim.report, changed = review(claim.claim_input, claim.report)
    except Exception as exc:  # the rule-engine report stands on its own; never fail a claim over the review
        log.exception("AI review failed for claim %s", claim.id)
        return f"AI review unavailable ({type(exc).__name__}) - showing the rule engine's findings", "skipped"
    claim.report.reviewed_by_ai = True
    return (f"{model_label()} updated unresolved deductions" if changed else f"{model_label()} agreed more information is needed"), "done"


def _write_report(claim: Claim, store: Storage) -> tuple[str, str]:
    claim.status = "complete"
    return claim.report.headline, "done"


_STEP_FUNCS = {
    "read_documents": _read_documents,
    "check_items": _check_items,
    "check_policy": _check_policy,
    "check_rules": _check_rules,
    "similar_cases": _similar_cases,
    "ai_review": _ai_review,
    "write_report": _write_report,
}


def start(claim: Claim) -> None:
    """Kick off processing: Step Functions when deployed, a background thread locally."""
    if settings.state_machine_arn:
        import json

        import boto3

        boto3.client("stepfunctions", region_name=settings.aws_region).start_execution(
            stateMachineArn=settings.state_machine_arn, name=claim.id, input=json.dumps({"claim_id": claim.id}))
        return

    def run() -> None:
        for name, _ in STEPS:
            time.sleep(settings.step_delay_seconds)
            try:
                run_step(claim.id, name)
            except Exception:
                return

    threading.Thread(target=run, daemon=True).start()


def attach_documents(claim: Claim, files: list[tuple[str, str, str, bytes]], store: Storage) -> None:
    for kind, filename, content_type, data in files:
        doc = ClaimDocument(kind=kind, filename=filename, content_type=content_type)
        store.save_document(claim.id, doc, data)
        claim.documents.append(doc)

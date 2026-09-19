"""HTTP API (FastAPI). Runs locally with uvicorn and on AWS Lambda through Mangum (see handlers.py)."""

import hashlib
import logging
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, Header, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import letters, pipeline
from .config import settings
from .knowledge import knowledge
from .models import Claim, ClaimDocument, Letter, ReportTotals
from .storage import load_json, storage

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("claimback")

app = FastAPI(title="ClaimBack API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CLAIMBACK_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
CONTENT_TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


OwnerHeader = Annotated[str | None, Header(alias="X-ClaimBack-Owner", description="Random per-browser id; claims are only visible to their owner")]


def _owner_hash(owner: str | None) -> str | None:
    return hashlib.sha256(owner.encode()).hexdigest() if owner else None


class ClaimSummary(BaseModel):
    id: str
    created_at: str
    status: str
    source: str
    sample_id: str | None
    title: str
    totals: ReportTotals | None


class SampleRequest(BaseModel):
    sample_id: str


class LetterRequest(BaseModel):
    kind: Literal["grievance", "ombudsman"]


@app.get("/api/health")
def health():
    return {"status": "ok", "llm": settings.llm, "storage": settings.storage, "version": app.version}


@app.get("/api/wordings")
def wordings():
    return knowledge().wordings()


@app.get("/api/samples")
def samples():
    out = []
    for entry in load_json(settings.samples_dir / "index.json"):
        folder = settings.samples_dir.parent / entry["folder"]
        expected = load_json(folder / "expected.json")
        claim_input = load_json(folder / "claim_input.json")
        out.append({
            "id": entry["scenario_id"], "title": entry["title"], "summary": expected["summary"],
            "claimed": entry["claim_totals"]["claimed"], "paid": entry["claim_totals"]["paid"],
            "letter_type": claim_input["decision"]["letter_type"],
        })
    return out


@app.post("/api/claims/sample", status_code=201, response_model=Claim)
def create_sample_claim(body: SampleRequest, owner: OwnerHeader = None):
    try:
        folder = pipeline.sample_folder(body.sample_id)
    except StopIteration:
        raise HTTPException(404, f"Unknown sample {body.sample_id}")
    title = next(s["title"] for s in load_json(settings.samples_dir / "index.json") if s["scenario_id"] == body.sample_id)
    claim = pipeline.new_claim("sample", title, sample_id=body.sample_id)
    claim.owner = _owner_hash(owner)
    files = [(kind, f"{kind}.pdf", "application/pdf", (folder / f"{kind}.pdf").read_bytes())
             for kind in ("policy_schedule", "hospital_bill", "insurer_letter", "discharge_summary") if (folder / f"{kind}.pdf").exists()]
    store = storage()
    pipeline.attach_documents(claim, files, store)
    store.save_claim(claim)
    pipeline.start(claim)
    return claim


async def _read_upload(kind: str, upload: UploadFile | None, required: bool) -> tuple[str, str, str, bytes] | None:
    if upload is None or not upload.filename:
        if required:
            raise HTTPException(422, f"{kind.replace('_', ' ')} is required")
        return None
    suffix = Path(upload.filename).suffix.lower()
    content_type = CONTENT_TYPES.get(suffix)
    if not content_type:
        raise HTTPException(415, f"{upload.filename}: upload a PDF, JPG or PNG")
    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"{upload.filename} is larger than 10 MB")
    return kind, Path(upload.filename).name, content_type, data


@app.post("/api/claims", status_code=201, response_model=Claim)
async def create_claim(
    hospital_bill: Annotated[UploadFile, File()],
    insurer_letter: Annotated[UploadFile, File()],
    policy_schedule: Annotated[UploadFile, File()],
    discharge_summary: Annotated[UploadFile | None, File()] = None,
    policy_wording_id: Annotated[str | None, Form()] = None,
    owner: OwnerHeader = None,
):
    if settings.llm != "bedrock":
        raise HTTPException(503, "Reading your own documents needs Claude on Amazon Bedrock, which isn't switched on in this build. Try a sample claim instead.")
    files = [f for f in [
        await _read_upload("hospital_bill", hospital_bill, True),
        await _read_upload("insurer_letter", insurer_letter, True),
        await _read_upload("policy_schedule", policy_schedule, True),
        await _read_upload("discharge_summary", discharge_summary, False),
    ] if f]
    wording = policy_wording_id if policy_wording_id and knowledge().policy(policy_wording_id) else None
    claim = pipeline.new_claim("upload", "Your claim")
    claim.owner = _owner_hash(owner)
    claim.policy_wording_id = wording
    store = storage()
    pipeline.attach_documents(claim, files, store)
    store.save_claim(claim)
    pipeline.start(claim)
    return claim


@app.get("/api/claims", response_model=list[ClaimSummary])
def list_claims(owner: OwnerHeader = None):
    mine = _owner_hash(owner)
    return [ClaimSummary(id=c.id, created_at=c.created_at.isoformat(), status=c.status, source=c.source, sample_id=c.sample_id,
                         title=c.title, totals=c.report.totals if c.report else None) for c in storage().list_claims() if c.owner == mine]


def _get(claim_id: str, owner: str | None) -> Claim:
    claim = storage().get_claim(claim_id)
    if not claim or (claim.owner and claim.owner != _owner_hash(owner)):
        raise HTTPException(404, "Claim not found")
    return claim


@app.get("/api/claims/{claim_id}", response_model=Claim)
def get_claim(claim_id: str, owner: OwnerHeader = None):
    return _get(claim_id, owner)


@app.delete("/api/claims/{claim_id}", status_code=204)
def delete_claim(claim_id: str, owner: OwnerHeader = None):
    _get(claim_id, owner)
    storage().delete_claim(claim_id)
    return Response(status_code=204)


@app.get("/api/claims/{claim_id}/documents/{kind}")
def get_document(claim_id: str, kind: str, owner: OwnerHeader = None, o: str | None = None):
    # documents open in a new tab, which can't send headers, so the owner id may also come as ?o=
    claim = _get(claim_id, owner or o)
    doc: ClaimDocument | None = next((d for d in claim.documents if d.kind == kind), None)
    if not doc:
        raise HTTPException(404, "Document not found")
    return Response(content=storage().read_document(claim_id, doc), media_type=doc.content_type,
                    headers={"Content-Disposition": f'inline; filename="{doc.filename}"'})


@app.post("/api/claims/{claim_id}/letters", response_model=Letter)
def create_letter(claim_id: str, body: LetterRequest, owner: OwnerHeader = None):
    claim = _get(claim_id, owner)
    if claim.status != "complete" or not claim.report or not claim.claim_input:
        raise HTTPException(409, "The report isn't ready yet")
    build = letters.grievance_letter if body.kind == "grievance" else letters.ombudsman_letter
    letter = build(claim.claim_input, claim.report)
    if settings.llm == "bedrock":
        try:
            from .llm import polish

            letter = polish(letter)
        except Exception:
            log.exception("letter polishing failed; returning the template letter")
    claim.letters[body.kind] = letter
    storage().save_claim(claim)
    return letter

"""API flow in offline mode: sample claim -> pipeline -> report -> letters -> documents."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from claimback.api import app

client = TestClient(app)
SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def wait_complete(claim_id: str) -> dict:
    for _ in range(200):
        claim = client.get(f"/api/claims/{claim_id}").json()
        if claim["status"] != "processing":
            return claim
        time.sleep(0.02)
    raise AssertionError("claim still processing")


def test_health_and_catalogue():
    assert client.get("/api/health").json()["llm"] == "offline"
    assert {w["id"] for w in client.get("/api/wordings").json()} == {"AS-NIVA-2026", "AS-STAR-2025"}
    assert [s["id"] for s in client.get("/api/samples").json()] == ["S1", "S2", "S3", "S4", "S5"]


def test_sample_claim_end_to_end():
    created = client.post("/api/claims/sample", json={"sample_id": "S3"})
    assert created.status_code == 201
    claim = wait_complete(created.json()["id"])
    assert claim["status"] == "complete", claim["error"]
    assert [p["status"] for p in claim["progress"]] == ["done", "done", "done", "done", "done", "skipped", "done"]
    report = claim["report"]
    assert report["totals"]["claim_rejected"] is True
    assert report["ombudsman_office"]["city"].lower() == "bengaluru"

    letter = client.post(f"/api/claims/{claim['id']}/letters", json={"kind": "ombudsman"})
    assert letter.status_code == 200
    assert "Insurance Ombudsman" in letter.json()["body"]
    assert "ombudsman" in client.get(f"/api/claims/{claim['id']}").json()["letters"]

    doc = client.get(f"/api/claims/{claim['id']}/documents/insurer_letter")
    assert doc.status_code == 200 and doc.headers["content-type"] == "application/pdf"

    assert any(c["id"] == claim["id"] for c in client.get("/api/claims").json())
    assert client.delete(f"/api/claims/{claim['id']}").status_code == 204
    assert client.get(f"/api/claims/{claim['id']}").status_code == 404


def test_upload_needs_bedrock_offline():
    folder = SAMPLES / "s1-consumables-mix-cashless"
    files = {kind: (f"{kind}.pdf", (folder / f"{kind}.pdf").read_bytes(), "application/pdf")
             for kind in ("hospital_bill", "insurer_letter", "policy_schedule")}
    assert client.post("/api/claims", files=files).status_code == 503


def test_unknown_sample_and_claim():
    assert client.post("/api/claims/sample", json={"sample_id": "S9"}).status_code == 404
    assert client.get("/api/claims/doesnotexist").status_code == 404


def test_claims_are_private_to_their_owner():
    alice, bob = {"X-ClaimBack-Owner": "alice-browser"}, {"X-ClaimBack-Owner": "bob-browser"}
    claim = client.post("/api/claims/sample", json={"sample_id": "S5"}, headers=alice).json()
    assert "owner" not in claim
    wait_complete_as = lambda h: client.get(f"/api/claims/{claim['id']}", headers=h)
    for _ in range(200):
        if wait_complete_as(alice).json()["status"] != "processing":
            break
        time.sleep(0.02)
    assert wait_complete_as(alice).status_code == 200
    assert wait_complete_as(bob).status_code == 404
    assert client.get(f"/api/claims/{claim['id']}/documents/hospital_bill?o=alice-browser").status_code == 200
    assert client.get(f"/api/claims/{claim['id']}/documents/hospital_bill?o=bob-browser").status_code == 404
    assert [c["id"] for c in client.get("/api/claims", headers=bob).json()] == []
    assert claim["id"] in [c["id"] for c in client.get("/api/claims", headers=alice).json()]

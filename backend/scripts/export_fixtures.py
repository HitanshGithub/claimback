"""Export real API responses for the 5 samples as frontend mock fixtures (backend/fixtures/)."""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[1]))
import json, os, sys, time
from pathlib import Path

os.environ["CLAIMBACK_STEP_DELAY"] = "0"
os.environ["CLAIMBACK_LOCAL_STORE"] = str(Path(__file__).parents[1] / ".fixture-claims")
from fastapi.testclient import TestClient
from claimback.api import app

out = Path(__file__).parents[1] / "fixtures"
out.mkdir(exist_ok=True)
client = TestClient(app)
(out / "health.json").write_text(json.dumps(client.get("/api/health").json(), indent=2), encoding="utf-8")
(out / "wordings.json").write_text(json.dumps(client.get("/api/wordings").json(), indent=2), encoding="utf-8")
samples = client.get("/api/samples").json()
(out / "samples.json").write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
for s in samples:
    claim = client.post("/api/claims/sample", json={"sample_id": s["id"]}).json()
    for _ in range(100):
        claim = client.get(f"/api/claims/{claim['id']}").json()
        if claim["status"] != "processing":
            break
        time.sleep(0.05)
    assert claim["status"] == "complete", claim.get("error")
    for kind in ("grievance", "ombudsman"):
        client.post(f"/api/claims/{claim['id']}/letters", json={"kind": kind})
    claim = client.get(f"/api/claims/{claim['id']}").json()
    claim["id"] = f"sample-{s['id'].lower()}"
    (out / f"claim-{s['id']}.json").write_text(json.dumps(claim, indent=2, ensure_ascii=False), encoding="utf-8")
    print(s["id"], claim["report"]["headline"])

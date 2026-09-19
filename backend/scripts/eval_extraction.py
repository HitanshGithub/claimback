"""Score Claude's document extraction against samples/*/claim_input.json. CALLS BEDROCK (costs money).

For each sample it sends the PDFs (and, with --photo, S1's phone photo instead of the bill PDF), then compares:
  - scalar fields (dates, amounts, claim type, network flag ...)
  - bill lines matched by amount + description
  - deductions matched by amount
  - whether the rule engine reaches the same totals from the extracted data (the number that matters)

Usage:
  set CLAIMBACK_LLM=bedrock & set CLAIMBACK_AWS_REGION=ap-south-1
  uv run python scripts/eval_extraction.py [--only S1] [--photo]
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claimback.engine.analyze import analyze  # noqa: E402
from claimback.llm import extract_claim  # noqa: E402
from claimback.models import ClaimInput  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
KINDS = ("policy_schedule", "hospital_bill", "insurer_letter", "discharge_summary")
SCALARS = [
    "policy.policy_number", "policy.sum_insured", "policy.first_inception", "policy.continuous_cover_start",
    "admission.claim_type", "admission.network_hospital", "admission.admission_date", "admission.discharge_date", "admission.is_accident",
    "decision.letter_type", "decision.letter_date", "decision.documents_received_date", "decision.amount_claimed",
    "decision.total_deducted", "decision.co_payment", "decision.amount_paid",
]


def get(obj, path: str):
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


def score(truth: ClaimInput, got: ClaimInput) -> dict:
    scalar_hits = {path: get(truth, path) == get(got, path) for path in SCALARS}
    truth_lines = {(line.amount, line.description.lower()[:12]) for line in truth.bill_lines}
    got_lines = {(line.amount, line.description.lower()[:12]) for line in got.bill_lines}
    truth_deductions = sorted(d.deducted for d in truth.decision.deductions)
    got_deductions = sorted(d.deducted for d in got.decision.deductions)
    today = date(2026, 9, 17)
    t_report, g_report = analyze(truth, today), analyze(got, today)
    return {
        "scalars": f"{sum(scalar_hits.values())}/{len(scalar_hits)}",
        "scalar_misses": [p for p, ok in scalar_hits.items() if not ok],
        "bill_lines": f"{len(truth_lines & got_lines)}/{len(truth_lines)} (extra {len(got_lines - truth_lines)})",
        "deductions_exact": truth_deductions == got_deductions,
        "same_challengeable_amount": t_report.totals.challengeable_amount == g_report.totals.challengeable_amount,
        "challengeable": [t_report.totals.challengeable_amount, g_report.totals.challengeable_amount],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--photo", action="store_true", help="use S1's phone photo instead of its bill PDF")
    args = parser.parse_args()
    results = {}
    for folder in sorted(SAMPLES.glob("s*-*")):
        truth = ClaimInput.model_validate_json((folder / "claim_input.json").read_text(encoding="utf-8"))
        sid = folder.name.split("-")[0].upper()
        if args.only and sid != args.only.upper():
            continue
        docs = []
        for kind in KINDS:
            if kind == "hospital_bill" and args.photo and (folder / "hospital_bill_photo.jpg").exists():
                docs.append((kind, "hospital_bill_photo.jpg", "image/jpeg", (folder / "hospital_bill_photo.jpg").read_bytes()))
            else:
                docs.append((kind, f"{kind}.pdf", "application/pdf", (folder / f"{kind}.pdf").read_bytes()))
        got = extract_claim(docs, truth.policy.policy_wording_id)
        results[sid] = score(truth, got)
        print(sid, json.dumps(results[sid], default=str))
    passed = sum(1 for r in results.values() if r["same_challengeable_amount"])
    print(f"\nengine reached the same challengeable amount on {passed}/{len(results)} samples")


if __name__ == "__main__":
    main()

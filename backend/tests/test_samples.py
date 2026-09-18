"""Engine vs the hand-checked ground truth in samples/*/expected.json."""

import json
from datetime import date
from pathlib import Path

import pytest

from claimback.engine.analyze import analyze
from claimback.models import ClaimInput

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
SEVERITY = ["not_applicable", "fair", "fair_ask_hospital_to_absorb", "needs_more_info", "challengeable"]
CHECK_IDS = {  # expected issue text (substring) -> engine check id
    "does not cite policy clauses": "C-CLAUSE-REFERENCES",
    "specific waiting period": "C-WAITING",
    "waiting periods": "C-WAITING",
    "after moratorium": "C-MORATORIUM",
    "pre-existing disease exclusion": "C-PED",
    "permanent exclusions": "C-PERMANENT-EXCLUSIONS",
    "proposal form": "C-PROPOSAL-FORM",
    "repudiation approval": "C-CRC-APPROVAL",
    "good-faith": "C-GOOD-FAITH",
    "delayed decision": "C-TIMELINE",
    "settlement timeline": "C-TIMELINE",
    "sports exclusion": "C-SPORTS",
    "co-payment computation": "C-COPAY",
    "room rent": "C-ROOM-RENT",
}


def load(folder: Path):
    claim = ClaimInput.model_validate_json((folder / "claim_input.json").read_text(encoding="utf-8"))
    expected = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
    return analyze(claim, today=date(2026, 9, 17)), expected


FOLDERS = sorted(p for p in SAMPLES.iterdir() if (p / "claim_input.json").exists())


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: p.name)
def test_deduction_verdicts(folder):
    report, expected = load(folder)
    by_line = {}
    for e in expected["deductions"]:
        by_line.setdefault(e["line_code"], []).append(e)
    assert len(report.deduction_findings) == len(by_line)
    for finding in report.deduction_findings:
        exp = by_line[finding.line_code]
        worst = max((e["expected_verdict"] for e in exp), key=SEVERITY.index)
        assert finding.verdict == worst, f"{finding.line_code} {finding.description}: {finding.verdict} != {worst}"
        exp_challengeable = sum(e["deducted"] for e in exp if e["expected_verdict"] == "challengeable")
        assert finding.amount_challengeable == pytest.approx(exp_challengeable), finding.line_code
        exp_cites = {c for e in exp for c in e["citations"]}
        assert exp_cites <= set(finding.citations), f"{finding.line_code}: missing citations {exp_cites - set(finding.citations)}"


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: p.name)
def test_totals(folder):
    report, expected = load(folder)
    t, r = report.totals, expected["result"]
    if r.get("claim_rejected"):
        accepted = expected["if_claim_accepted"]
        assert t.claim_rejected
        assert t.challengeable_amount == pytest.approx(accepted["admissible"])
        assert t.estimated_additional_payable == pytest.approx(accepted["estimated_payable"])
        return
    assert t.challengeable_amount == pytest.approx(r["challengeable_amount"])
    assert t.estimated_additional_payable == pytest.approx(r["estimated_additional_payable_after_copay"])
    assert t.needs_more_info_amount == pytest.approx(r["needs_more_info_amount"])
    assert t.ask_hospital_amount == pytest.approx(r["ask_hospital_to_absorb_amount"])


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: p.name)
def test_claim_level_checks(folder):
    report, expected = load(folder)
    checks = {c.id: c for c in report.check_findings}
    for e in expected.get("other_checks", []) + expected.get("rejection_checks", []):
        cid = next(v for k, v in CHECK_IDS.items() if k in e["issue"].lower())
        assert cid in checks, f"missing check {cid} for '{e['issue']}'"
        assert checks[cid].verdict == e["verdict"], f"{cid}: {checks[cid].verdict} != {e['verdict']}"
        missing = set(e.get("citations", [])) - set(checks[cid].citations)
        assert not missing, f"{cid}: missing citations {missing}"


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: p.name)
def test_similar_cases_and_citations(folder):
    report, expected = load(folder)
    assert {c.case_id for c in report.similar_cases} == {c["case_id"] for c in expected["similar_real_cases"]}
    cited = {cid for f in [*report.deduction_findings, *report.check_findings, *report.escalation] for cid in f.citations}
    assert cited <= set(report.citations), f"unresolved citation ids: {cited - set(report.citations)}"


def test_alternate_wording_s2():
    report, expected = load(SAMPLES / "s2-proportionate-deduction")
    alt = expected["alternate_wordings"][0]
    assert [a.policy_wording_id for a in report.alternate_wordings] == [alt["wording_id"]]
    assert report.alternate_wordings[0].challengeable_amount == pytest.approx(alt["challengeable_amount"])

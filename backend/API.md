# ClaimBack API

Base path `/api`. JSON bodies use the models in `claimback/models.py`. Dates are ISO `YYYY-MM-DD`; timestamps are ISO 8601; money is a plain number of rupees.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | - | `{"status": "ok", "llm": "offline" \| "bedrock", "storage": "local" \| "aws", "version": "0.1.0"}` |
| GET | `/api/wordings` | - | `[{"id": "AS-NIVA-2026", "insurer": "...", "product": "...", "uin": "..."}]` - policy wordings the engine supports |
| GET | `/api/samples` | - | `[{"id": "S1", "title", "summary", "claimed", "paid", "letter_type": "settlement" \| "repudiation"}]` |
| POST | `/api/claims/sample` | `{"sample_id": "S1"}` | `201` `Claim` with `status: "processing"` |
| POST | `/api/claims` | multipart: `hospital_bill`, `insurer_letter`, `policy_schedule` (files, required), `discharge_summary` (file, optional), `policy_wording_id` (text, optional) | `201` `Claim`. `503 {"detail": "..."}` when `llm` is `offline` (reading uploaded documents needs Claude on Bedrock) |
| GET | `/api/claims` | - | `[ClaimSummary]` newest first: `{"id", "created_at", "status", "source", "sample_id", "title", "totals": ReportTotals \| null}` |
| GET | `/api/claims/{id}` | - | `Claim` (404 if unknown) |
| DELETE | `/api/claims/{id}` | - | `204` |
| GET | `/api/claims/{id}/documents/{kind}` | - | the original file (`kind` = `policy_schedule` \| `hospital_bill` \| `insurer_letter` \| `discharge_summary`) |
| POST | `/api/claims/{id}/letters` | `{"kind": "grievance" \| "ombudsman"}` | `Letter`, also saved in `Claim.letters[kind]`. `409` if the claim is not complete |

## Processing

A new claim comes back with `status: "processing"` and `progress` steps in order:

| name | label |
|---|---|
| `read_documents` | Reading your documents |
| `check_items` | Checking every deduction against the policy's non-payable lists |
| `check_policy` | Checking your policy wording |
| `check_rules` | Checking IRDAI rules and deadlines |
| `similar_cases` | Finding similar Ombudsman and court decisions |
| `ai_review` | Claude reviews anything the rules can't settle (`skipped` in offline mode) |
| `write_report` | Writing your report |

Each step's `status` moves `pending -> running -> done | skipped | failed`, with an optional `detail` string (e.g. "22 bill lines, 14 deductions"). Poll `GET /api/claims/{id}` about once a second until `status` is `complete` (then `report` is set) or `failed` (then `error` is set).

## Report essentials for the UI

- `report.totals` - `claimed`, `paid`, `total_deducted`, `challengeable_amount`, `needs_more_info_amount`, `ask_hospital_amount`, `estimated_additional_payable`, `claim_rejected`.
- `report.deduction_findings[]` - one per insurer deduction: `verdict`, `strength`, `amount_challengeable`, `explanation`, `citations` (ids).
- `report.check_findings[]` - claim-level checks (moratorium, delay interest, co-pay maths, letter missing clause references...).
- `report.citations` - map id -> `{kind, title, quote, source, clause_ref, page, url}`. Every id in any `citations` array resolves here.
- `report.similar_cases[]`, `report.escalation[]` (with `due_date`), `report.ombudsman_office`, `report.alternate_wordings[]`.

Verdict meanings: `challengeable` (dispute it), `needs_more_info` (ask the insurer to justify), `fair` (deduction is correct), `fair_ask_hospital_to_absorb` (correct, but you can ask a network hospital to waive it - a request, not a right), `not_applicable` (check didn't apply).

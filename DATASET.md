# ClaimBack dataset and knowledge base

Everything the ClaimBack agent needs to judge a health insurance claim deduction or rejection in India, with a citation for every answer. Data collected on 2026-09-17.

```
knowledge-base/      -> sync to S3, then attach as an Amazon Bedrock Knowledge Base (RAG)
  regulations/       12 IRDAI / Ministry of Finance documents (PDF + .metadata.json): 2024 regulations and master circulars, Ombudsman Rules 2017 + amendments
  policy-wordings/   Arogya Sanjeevani wordings: Niva Bupa 2026-27, Star Health 2025-26
  curated/           21 short Markdown pages generated from data/ (clean chunks, always cited)
  cases/             40 real decided cases (Ombudsman, consumer commissions, Supreme Court), one Markdown file each
data/                -> structured JSON for deterministic agent tools (Lambda), not for RAG
samples/             -> 5 fictional claim packs with expected verdicts, for demo and evaluation
reference/           -> NOT in the knowledge base
  superseded/        superseded circulars, kept for history
  case-originals/    full award / judgment texts behind each case (contain real party names as published)
scripts/             -> rebuild and verify everything
```

## How the pieces fit

The agent should **compute** with `data/` and **explain and cite** with the knowledge base:

| Question the agent answers | Use |
|---|---|
| Is "Gloves Rs 1,240" a genuinely non-payable item? | `data/non_payable_items.json` (match by name and alias) |
| Was the room-rent proportionate deduction applied to the right bill heads? | `data/policy_terms_arogya_sanjeevani.json` -> `proportionate_deduction` |
| Can the insurer reject for non-disclosure after 7 years? | `data/rules_regulatory.json` (`R-MORATORIUM-60M`) and the policy clause `NIVA-AS-8-MORATORIUM` |
| Where do I complain next, and by when? | `data/escalation_path.json`, `data/ombudsman_offices.json` |
| Has an Ombudsman decided a similar case? | `data/real_cases.json` / `knowledge-base/cases/` |

Every rule and clause has a stable `id`. The agent should cite ids, and the UI can resolve an id to its verbatim quote, clause reference, page and source PDF.

## data/

| File | What it is |
|---|---|
| `rules_regulatory.json` | 60 rules from current regulations, each with `verbatim_quote`, `clause_ref`, `page`, `source_file`, `use_when`, `challenge_strength` (34 strong, 18 moderate, 8 context-dependent) |
| `policy_terms_arogya_sanjeevani.json` | Limits, waiting periods, proportionate-deduction scope, claim timelines and 25 quoted clauses for 2 insurer wordings |
| `non_payable_items.json` / `.csv` | The 146 List I-IV items with meaning, guidance, bill-wording aliases, and the page where each appears in both current wordings |
| `escalation_path.json` | Insurer grievance -> Bima Bharosa -> Insurance Ombudsman -> consumer commission, with timelines and rule ids |
| `ombudsman_offices.json` | The 18 Insurance Ombudsman offices: address, phone, email, states / UTs / districts covered (from cioins.co.in, 2026-09-17) |
| `real_cases.json` | 40 real decided cases: facts, insurer's reason, decision, reasoning, amounts, key quote, source URL, `decided_before_2024_health_rules` |
| `superseded_circulars.json` | The 55 circulars that the 2024 health master circular superseded (its Annexure-6) |

### Facts that are easy to get wrong (all verified in the source PDFs)

- **Non-payable List I-IV is no longer an IRDAI rule.** The 2020 standardization circular that created it was superseded on 29 May 2024 and nothing re-issues the list. It still binds as **Annexure-A of the policy wording**, so cite the wording, not IRDAI.
- **The "standard" product is not worded identically.** Niva Bupa's Arogya Sanjeevani applies proportionate deduction only to room rent, nursing, doctors' fees and OT charges. Star Health's applies it to everything except medicines. Always judge against the claimant's own wording.
- **Reimbursement claims must be settled within 15 days** of submission (not the commonly quoted 30), with interest at bank rate + 2% from intimation if late.
- **Ombudsman award limit is Rs 50 lakh** since 9 Nov 2023 (not Rs 30 lakh). Filing is free, within 1 year, after approaching the insurer first.
- **Insurer grievances must be resolved in 14 days**. The Ombudsman can be approached after 30 days or an unsatisfactory reply.
- **After the 60-month moratorium** a claim cannot be contested for non-disclosure except established fraud, but permanent exclusions written in the policy still apply.
- **Any deduction must trace to an exclusion written in the policy** (`R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS`), and **a partial disallowance must cite the specific policy terms** (`R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE`).
- There is **no current regulatory definition of "reasonable and customary charges"**. Use the policy's own definition of Medical Expenses (Niva Bupa 3.29).

## Real cases

40 cases: 26 Insurance Ombudsman awards (25 full awards from April 2021, Mumbai / Pune / Chandigarh, plus 1 from a 2017-18 summary book), 12 consumer commission orders (NCDRC 1, State Commissions 10, District Commission 1) and 2 Supreme Court judgments (`forum_type: court`). Outcomes: 20 allowed, 9 partly allowed, 11 dismissed. The dismissed cases matter, because they keep the agent honest. Every quote and amount was checked against the downloaded source text. Personal details are removed from the summaries; court case titles are kept as published citations.

| Category | Cases | | Category | Cases |
|---|---|---|---|---|
| proportionate_deduction | 5 | | modern_treatment | 3 |
| ped_non_disclosure | 5 | | sub_limit, co_payment, day_care, hospitalization_24h, delayed_intimation, documents | 2 each |
| waiting_period | 5 | | other | 2 |
| reasonable_customary | 4 | | room_rent_cap | 1 |
| non_payable_consumables | 3 | | | |

**Rules-era caveat:** 38 of 40 were decided before the 29 May 2024 health rules. Those files start with a note and carry `decided_before_2024_health_rules: true` (also a KB metadata filter). Use them as "how forums reason", and cite the current rule for the law.

Patterns in the cases:
- Proportionate deduction is upheld when the policy clause clearly allows it. It was struck down when the hospital had no room-category pricing, the calculation was wrong, it was applied to surgeon fees without clause support, or terms changed at renewal without notice.
- Capping a non-network hospital's bill at network package rates or the GI Council Covid rate card almost always lost. A cap written into the policy wins.
- Terms never communicated to the policyholder (caps added at renewal, exclusions never supplied) were struck down, as in Jacob Punnen (SC, 2021).
- Non-disclosure: the insurer wins when the proposal form had a clear "no" and treatment before inception is documented. The policyholder wins when the insurer skipped underwriting, accepted premium despite blank answers, or could not prove the condition predated the policy.
- Modern and day-care treatments (intravitreal injections, oral chemotherapy) usually win. Pure home treatment with no admission lost.

CIO no longer publishes awards publicly (downloads need an OTP sent to the parties), so the 2021 awards come from a Wayback Machine copy of one monthly compilation.

## samples/

Five fictional claims (fictional insurer "Nirmaan Health", fictional hospitals, every page footed "FICTIONAL SAMPLE DOCUMENT"). Each folder has `policy_schedule.pdf`, `hospital_bill.pdf`, `discharge_summary.pdf`, `insurer_letter.pdf`, `line_items.json` (ground truth for bill extraction) and `expected.json` (ground truth verdicts with citations). Judge each against the wording named in `evaluate_with_policy_wording`.

| # | Scenario | Claimed | Paid | Expected result |
|---|---|---|---|---|
| S1 | Gallbladder surgery, cashless, 14 "non-payable" deductions | 1,39,700 | 1,13,867 | Rs 11,600 challengeable (sutures, clips, drain, histopathology); +Rs 11,020 after co-pay. Includes `hospital_bill_photo.jpg` for OCR testing |
| S2 | Pneumonia, Rs 8,000 room vs Rs 5,000 limit, pro-rata applied to the whole bill | 1,16,100 | 66,975 | Rs 22,800 challengeable under Niva Bupa wording (+21,660 after co-pay); only Rs 14,400 under Star Health wording |
| S3 | Heart attack, fully rejected for non-disclosure after 84 months of continuous cover (ported) | 2,59,100 | 0 | Strong challenge: moratorium, portability credit, late decision (30 days vs 15) so interest is due |
| S4 | ACL surgery, surgeon fee halved as "reasonable and customary" | 2,57,300 | 1,72,710 | Rs 60,000 needs more info (insurer must show locality benchmark and cite a clause); other deductions fair |
| S5 | Dengue, deductions are genuine List I/II/IV items | 39,760 | 33,687 | Nothing to challenge: the app must say so |

Verdict values: `challengeable`, `needs_more_info`, `fair`, `fair_ask_hospital_to_absorb` (the deduction is correct, but the patient can ask a network hospital to waive the charge, which is a request, not a right), `not_applicable`.

Each `expected.json` also lists `similar_real_cases` from `data/real_cases.json` in the same category, with both wins and losses, for the "a similar case was decided like this" part of the demo.

## Upload to Amazon Bedrock Knowledge Bases

Bedrock reads each `<file>.metadata.json` sidecar from the same S3 prefix, so upload files and sidecars together. `knowledge-base/` contains only what should be searchable. Superseded documents and case originals with party names live in `reference/`:

```bash
aws s3 sync knowledge-base/ s3://<your-kb-bucket>/
```

Then create a knowledge base with an S3 data source on that bucket. Metadata attributes such as `doc_type`, `topic`, `policy_id`, `category`, `decision`, `status` and `decided_before_2024_health_rules` can be used as retrieval filters. For example, filter `policy_id = AS-NIVA-2026` when judging a Niva Bupa claim. Each file must be under 50 MB. The largest here is about 2 MB.

## Rebuild and verify

Requires Python 3.12+ with `pypdf`, `pillow`, and `pdftotext` (poppler) and Google Chrome for PDF rendering.

```bash
python scripts/build_non_payable_items.py   # List I-IV from the circular, cross-checked against current wordings
python scripts/build_samples.py             # 5 claim packs; fails if any citation id does not exist
python scripts/build_kb_markdown.py         # knowledge-base/curated/*.md from data/
python scripts/verify_quotes.py             # every verbatim_quote must appear in its source PDF
```

## Sources

- IRDAI (Insurance Products) Regulations, 2024; Master Circular on Health Insurance Business, 29.05.2024 (IRDAI/HLT/CIR/PRO/84/5/2024) and annexures - https://irdai.gov.in/health-dept
- IRDAI (Protection of Policyholders' Interests, Operations and Allied Matters of Insurers) Regulations, 2024 and Master Circular, 05.09.2024 (IRDAI/PP&GR/CIR/MISC/117/9/2024)
- Insurance Ombudsman Rules, 2017 with amendments of 2018, 2021 (two) and 2023; IRDAI circular IRDAI/PP&GR/CIR/MISC/95/07/2026 - https://www.cioins.co.in/
- Arogya Sanjeevani wordings: Niva Bupa (UIN NBHHLIP27056V042627), Star Health (UIN SHAHLIP26045V042526)
- Superseded, history only: Master Circular on Standardization of Health Insurance Products, 22.07.2020 (IRDAI/HLT/REG/CIR/193/07/2020); Guidelines on Standardization of Exclusions, 2019
- Cases: Council for Insurance Ombudsmen April 2021 health awards (Wayback Machine copy), ecoi.co.in 2017-18 award summaries, Indian Kanoon, LiveLaw. Per-case URLs are in `data/real_cases.json`
- Ombudsman offices: https://www.cioins.co.in/Ombudsman

This dataset supports an informational tool. It is not legal advice, and rules should be re-checked against IRDAI's site before relying on them.

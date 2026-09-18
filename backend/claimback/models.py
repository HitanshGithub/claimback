"""Data contract shared by extraction, the rule engine, the API and the frontend.

ClaimInput  - what we read from the claimant's documents (the extraction target).
Report      - what the engine (+ optional Claude review) concludes, with citation ids resolvable in Report.citations.
Claim       - the stored record the API returns.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Verdict = Literal["challengeable", "needs_more_info", "fair", "fair_ask_hospital_to_absorb", "not_applicable"]
Strength = Literal["strong", "moderate", "weak"]
BillHead = Literal[
    "room", "icu", "nursing", "doctor", "ot", "implant", "pharmacy", "investigations", "consumable", "misc", "ambulance", "other"
]


# ----------------------------------------------------------------------------------------------------------------
# Extraction target
# ----------------------------------------------------------------------------------------------------------------

class BillLine(BaseModel):
    code: str = Field(description="Line code printed on the bill, or a generated one like L01 if none")
    head: BillHead = Field(description="Bill section the line belongs to")
    description: str
    qty: float
    rate: float
    amount: float


class Deduction(BaseModel):
    line_code: str | None = Field(description="Code of the bill line this deduction applies to; null for whole-bill deductions such as proportionate deduction")
    description: str = Field(description="Item as named in the insurer's letter")
    billed: float | None
    deducted: float
    reason: str = Field(description="Reason exactly as written by the insurer")


class PolicyInfo(BaseModel):
    policy_number: str
    insurer_name: str
    product_name: str
    policy_wording_id: str | None = Field(description="Id of a supported policy wording, e.g. AS-NIVA-2026, or null if not supported")
    sum_insured: float
    cumulative_bonus: float = 0
    policy_period_start: date | None = None
    policy_period_end: date | None = None
    first_inception: date | None = Field(default=None, description="Inception of the first policy with the current insurer")
    continuous_cover_start: date | None = Field(default=None, description="Start of continuous cover including ported / migrated policies")
    peds_declared: list[str] = Field(default_factory=list)
    optional_covers: list[str] = Field(default_factory=list)
    co_payment_pct: float | None = None
    holder_name: str | None = None
    city: str | None = None
    state: str | None = None


class Admission(BaseModel):
    patient_name: str
    age: int | None = None
    gender: str | None = None
    hospital_name: str
    hospital_city: str | None = None
    network_hospital: bool | None = None
    claim_type: Literal["cashless", "reimbursement"]
    admission_date: date
    discharge_date: date
    diagnosis: str
    procedure: str | None = None
    is_accident: bool = False
    comorbidities: list[str] = Field(default_factory=list)


class InsurerDecision(BaseModel):
    letter_type: Literal["settlement", "repudiation"]
    letter_date: date
    claim_number: str
    documents_received_date: date | None = None
    amount_claimed: float
    total_deducted: float
    admissible_amount: float | None = None
    co_payment: float | None = None
    amount_paid: float
    deductions: list[Deduction] = Field(default_factory=list)
    repudiation_reason: str | None = None
    clauses_cited: list[str] = Field(default_factory=list)


class ClaimInput(BaseModel):
    policy: PolicyInfo
    admission: Admission
    bill_lines: list[BillLine]
    decision: InsurerDecision


# ----------------------------------------------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------------------------------------------

class Citation(BaseModel):
    id: str
    kind: Literal["rule", "policy_clause", "non_payable_item"]
    title: str
    quote: str | None = None
    source: str = Field(description="Short human-readable document name")
    source_detail: str | None = Field(default=None, description="Full document title and reference number")
    clause_ref: str | None = None
    page: int | str | None = None
    url: str | None = None


class DeductionFinding(BaseModel):
    id: str
    line_code: str | None
    description: str
    billed: float | None
    deducted: float
    insurer_reason: str
    category: str = Field(description="non_payable_item | not_in_lists | proportionate_deduction | reasonable_customary | exclusion | policy_limit | unknown")
    verdict: Verdict
    strength: Strength | None = None
    amount_challengeable: float = 0
    explanation: str
    citations: list[str] = Field(default_factory=list)
    matched_item: str | None = None


class CheckFinding(BaseModel):
    id: str
    issue: str
    verdict: Verdict
    strength: Strength | None = None
    explanation: str
    citations: list[str] = Field(default_factory=list)
    computed: dict = Field(default_factory=dict)


class SimilarCase(BaseModel):
    case_id: str
    forum: str
    decision_date: str
    decision: str
    category: str
    insurer_reason: str
    reasoning: str
    amount_awarded_inr: float | None = None
    decided_before_2024_health_rules: bool
    source_url: str


class EscalationStep(BaseModel):
    step: int
    title: str
    action: str
    due_date: date | None = None
    deadline_note: str
    citations: list[str] = Field(default_factory=list)


class OmbudsmanOffice(BaseModel):
    city: str
    address: str | None = None
    email: str | None = None
    phone: str | None = None


class ReportTotals(BaseModel):
    claimed: float
    paid: float
    total_deducted: float
    challengeable_amount: float
    needs_more_info_amount: float
    ask_hospital_amount: float
    estimated_additional_payable: float = Field(description="Challengeable amount after the policy's co-payment")
    claim_rejected: bool = False


class AlternateWording(BaseModel):
    policy_wording_id: str
    insurer: str
    challengeable_amount: float
    note: str


class Report(BaseModel):
    generated_at: datetime
    policy_wording_id: str | None
    policy_wording_name: str | None
    headline: str
    summary: str
    totals: ReportTotals
    deduction_findings: list[DeductionFinding]
    check_findings: list[CheckFinding]
    similar_cases: list[SimilarCase]
    escalation: list[EscalationStep]
    ombudsman_office: OmbudsmanOffice | None = None
    citations: dict[str, Citation]
    alternate_wordings: list[AlternateWording] = Field(default_factory=list)
    reviewed_by_ai: bool = False
    disclaimer: str = (
        "ClaimBack gives information, not legal advice. Check the cited clauses and rules before relying on them."
    )


class Letter(BaseModel):
    kind: Literal["grievance", "ombudsman"]
    to: str
    subject: str
    body: str
    generated_by: Literal["template", "claude"]


# ----------------------------------------------------------------------------------------------------------------
# Stored claim
# ----------------------------------------------------------------------------------------------------------------

StepName = Literal["read_documents", "check_items", "check_policy", "check_rules", "similar_cases", "ai_review", "write_report"]
ClaimStatus = Literal["processing", "complete", "failed"]


class ProgressStep(BaseModel):
    name: StepName
    label: str
    status: Literal["pending", "running", "done", "skipped", "failed"] = "pending"
    detail: str | None = None


class ClaimDocument(BaseModel):
    kind: Literal["policy_schedule", "hospital_bill", "insurer_letter", "discharge_summary", "other"]
    filename: str
    content_type: str


class Claim(BaseModel):
    id: str
    created_at: datetime
    status: ClaimStatus
    source: Literal["sample", "upload"]
    sample_id: str | None = None
    policy_wording_id: str | None = Field(default=None, description="Wording the user selected at upload, if any")
    owner: str | None = Field(default=None, exclude=True, description="SHA-256 of the browser's owner id; never returned by the API")
    title: str
    documents: list[ClaimDocument] = Field(default_factory=list)
    progress: list[ProgressStep] = Field(default_factory=list)
    claim_input: ClaimInput | None = None
    report: Report | None = None
    letters: dict[str, Letter] = Field(default_factory=dict)
    error: str | None = None

/**
 * TypeScript mirror of backend/claimback/models.py (pydantic) plus the small
 * response shapes documented in backend/API.md.
 *
 * Conventions from the API: dates are ISO `YYYY-MM-DD` strings, timestamps are
 * ISO 8601 strings, money is a plain number of rupees.
 */

/** ISO date, `YYYY-MM-DD`. */
export type ISODate = string
/** ISO 8601 timestamp. */
export type ISODateTime = string

export type Verdict =
  | 'challengeable'
  | 'needs_more_info'
  | 'fair'
  | 'fair_ask_hospital_to_absorb'
  | 'not_applicable'

export type Strength = 'strong' | 'moderate' | 'weak'

export type BillHead =
  | 'room'
  | 'icu'
  | 'nursing'
  | 'doctor'
  | 'ot'
  | 'implant'
  | 'pharmacy'
  | 'investigations'
  | 'consumable'
  | 'misc'
  | 'ambulance'
  | 'other'

// ---------------------------------------------------------------------------
// Extraction target
// ---------------------------------------------------------------------------

export interface BillLine {
  code: string
  head: BillHead
  description: string
  qty: number
  rate: number
  amount: number
}

export interface Deduction {
  line_code: string | null
  description: string
  billed: number | null
  deducted: number
  reason: string
}

export interface PolicyInfo {
  policy_number: string
  insurer_name: string
  product_name: string
  policy_wording_id: string | null
  sum_insured: number
  cumulative_bonus: number
  policy_period_start: ISODate | null
  policy_period_end: ISODate | null
  first_inception: ISODate | null
  continuous_cover_start: ISODate | null
  peds_declared: string[]
  optional_covers: string[]
  co_payment_pct: number | null
  holder_name: string | null
  city: string | null
  state: string | null
}

export interface Admission {
  patient_name: string
  age: number | null
  gender: string | null
  hospital_name: string
  hospital_city: string | null
  network_hospital: boolean | null
  claim_type: 'cashless' | 'reimbursement'
  admission_date: ISODate
  discharge_date: ISODate
  diagnosis: string
  procedure: string | null
  is_accident: boolean
  comorbidities: string[]
}

export interface InsurerDecision {
  letter_type: 'settlement' | 'repudiation'
  letter_date: ISODate
  claim_number: string
  documents_received_date: ISODate | null
  amount_claimed: number
  total_deducted: number
  admissible_amount: number | null
  co_payment: number | null
  amount_paid: number
  deductions: Deduction[]
  repudiation_reason: string | null
  clauses_cited: string[]
}

export interface ClaimInput {
  policy: PolicyInfo
  admission: Admission
  bill_lines: BillLine[]
  decision: InsurerDecision
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------

export type CitationKind = 'rule' | 'policy_clause' | 'non_payable_item'

export interface Citation {
  id: string
  kind: CitationKind
  title: string
  quote: string | null
  /** Short human-readable document name */
  source: string
  /** Full document title (show as a tooltip) */
  source_detail?: string | null
  clause_ref: string | null
  page: number | string | null
  url: string | null
}

/**
 * `category` is one of: non_payable_item | not_in_lists | proportionate_deduction |
 * reasonable_customary | exclusion | policy_limit | unknown
 */
export interface DeductionFinding {
  id: string
  line_code: string | null
  description: string
  billed: number | null
  deducted: number
  insurer_reason: string
  category: string
  verdict: Verdict
  strength: Strength | null
  amount_challengeable: number
  explanation: string
  citations: string[]
  matched_item: string | null
}

export type ComputedValue = string | number | boolean | null | ComputedValue[] | { [key: string]: ComputedValue }

export interface CheckFinding {
  id: string
  issue: string
  verdict: Verdict
  strength: Strength | null
  explanation: string
  citations: string[]
  computed: Record<string, ComputedValue>
}

export interface SimilarCase {
  case_id: string
  forum: string
  decision_date: string
  /** "allowed" | "partly_allowed" | "dismissed" in the dataset */
  decision: string
  category: string
  insurer_reason: string
  reasoning: string
  amount_awarded_inr: number | null
  decided_before_2024_health_rules: boolean
  source_url: string
}

export interface EscalationStep {
  step: number
  title: string
  action: string
  due_date: ISODate | null
  deadline_note: string
  citations: string[]
}

export interface OmbudsmanOffice {
  city: string
  address: string | null
  email: string | null
  phone: string | null
}

export interface ReportTotals {
  claimed: number
  paid: number
  total_deducted: number
  challengeable_amount: number
  needs_more_info_amount: number
  ask_hospital_amount: number
  /** Challengeable amount after the policy's co-payment */
  estimated_additional_payable: number
  claim_rejected: boolean
}

export interface AlternateWording {
  policy_wording_id: string
  insurer: string
  challengeable_amount: number
  note: string
}

export interface Report {
  generated_at: ISODateTime
  policy_wording_id: string | null
  policy_wording_name: string | null
  headline: string
  summary: string
  totals: ReportTotals
  deduction_findings: DeductionFinding[]
  check_findings: CheckFinding[]
  similar_cases: SimilarCase[]
  escalation: EscalationStep[]
  ombudsman_office: OmbudsmanOffice | null
  citations: Record<string, Citation>
  alternate_wordings: AlternateWording[]
  reviewed_by_ai: boolean
  disclaimer: string
}

export type LetterKind = 'grievance' | 'ombudsman'

export interface Letter {
  kind: LetterKind
  to: string
  subject: string
  body: string
  generated_by: 'template' | 'ai'
}

// ---------------------------------------------------------------------------
// Stored claim
// ---------------------------------------------------------------------------

export type StepName =
  | 'read_documents'
  | 'check_items'
  | 'check_policy'
  | 'check_rules'
  | 'similar_cases'
  | 'ai_review'
  | 'write_report'

export type StepStatus = 'pending' | 'running' | 'done' | 'skipped' | 'failed'

export type ClaimStatus = 'processing' | 'complete' | 'failed'

export interface ProgressStep {
  name: StepName
  label: string
  status: StepStatus
  detail: string | null
}

export type DocumentKind = 'policy_schedule' | 'hospital_bill' | 'insurer_letter' | 'discharge_summary' | 'other'

export interface ClaimDocument {
  kind: DocumentKind
  filename: string
  content_type: string
}

export interface Claim {
  id: string
  created_at: ISODateTime
  status: ClaimStatus
  source: 'sample' | 'upload'
  sample_id: string | null
  policy_wording_id?: string | null
  title: string
  documents: ClaimDocument[]
  progress: ProgressStep[]
  claim_input: ClaimInput | null
  report: Report | null
  /** keyed by LetterKind */
  letters: Partial<Record<LetterKind, Letter>>
  error: string | null
}

// ---------------------------------------------------------------------------
// Other endpoint shapes (API.md)
// ---------------------------------------------------------------------------

export interface Health {
  status: 'ok' | string
  llm: 'offline' | 'bedrock'
  storage: 'local' | 'aws'
  version: string
}

export interface PolicyWording {
  id: string
  insurer: string
  product: string
  uin: string
}

export interface SampleSummary {
  id: string
  title: string
  summary: string
  claimed: number
  paid: number
  letter_type: 'settlement' | 'repudiation'
}

export interface ClaimSummary {
  id: string
  created_at: ISODateTime
  status: ClaimStatus
  source: 'sample' | 'upload'
  sample_id: string | null
  title: string
  totals: ReportTotals | null
}

/** Files for POST /api/claims (multipart). */
export interface NewClaimUpload {
  hospital_bill: File
  insurer_letter: File
  policy_schedule: File
  discharge_summary?: File | null
  policy_wording_id?: string | null
}

/**
 * Mock-mode letter drafts. The real backend returns a `Letter` built by its own
 * template (or by Claude); this mirrors that shape so the UI can be exercised
 * without a server.
 */
import type { Citation, Claim, Letter, LetterKind, Report } from '../api/types'
import { formatDate } from '../lib/format'

const num = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })
const rs = (n: number) => `Rs ${num.format(Math.round(n))}`

function citeLine(ids: string[], citations: Report['citations']): string | null {
  const parts = ids
    .map((id) => citations[id])
    .filter((c): c is Citation => Boolean(c))
    .map((c) => {
      if (c.kind === 'rule') return `${c.source}, ${c.clause_ref ?? ''}`.replace(/,\s*$/, '')
      return `Policy wording, ${c.clause_ref ?? c.title}`
    })
  const unique = [...new Set(parts)]
  return unique.length ? unique.join('; ') : null
}

function indent(text: string): string {
  return text
    .split('\n')
    .map((l) => (l ? `   ${l}` : l))
    .join('\n')
}

export function buildMockLetter(claim: Claim, kind: LetterKind, today = new Date()): Letter {
  const report = claim.report
  const input = claim.claim_input
  if (!report) throw new Error('Report not ready')

  const insurer = input?.policy.insurer_name ?? 'the insurer'
  const holder = input?.policy.holder_name ?? input?.admission.patient_name ?? '[Your name]'
  const city = input?.policy.city ?? '[Your city]'
  const policyNo = input?.policy.policy_number ?? '[Policy number]'
  const claimNo = input?.decision.claim_number ?? '[Claim number]'
  const letterDate = input ? formatDate(input.decision.letter_date) : '[date of the insurer’s letter]'
  const totals = report.totals
  const todayText = formatDate(today.toISOString().slice(0, 10))
  const copay = input?.policy.co_payment_pct

  const disputed = totals.claim_rejected
    ? report.check_findings.filter((c) => c.verdict === 'challengeable')
    : report.deduction_findings.filter((d) => d.verdict === 'challengeable')
  const justify = totals.claim_rejected
    ? report.check_findings.filter((c) => c.verdict === 'needs_more_info')
    : report.deduction_findings.filter((d) => d.verdict === 'needs_more_info')

  const facts: string[] = []
  if (input) {
    const a = input.admission
    facts.push(`Policy number: ${policyNo}`)
    facts.push(`Claim number: ${claimNo}`)
    facts.push(`Patient: ${a.patient_name}`)
    facts.push(`Hospital: ${a.hospital_name}${a.hospital_city ? `, ${a.hospital_city}` : ''}`)
    facts.push(
      `Admission: ${formatDate(a.admission_date)} to ${formatDate(a.discharge_date)}${a.procedure ? ` (${a.procedure})` : ''}`,
    )
  }

  const opening = totals.claim_rejected
    ? `I am writing to dispute your letter dated ${letterDate}, which rejected the above claim of ${rs(totals.claimed)}${
        input?.decision.clauses_cited.length ? ` under ${input.decision.clauses_cited.join(' and ')}` : ''
      }.`
    : `I am writing to dispute the settlement of the above claim. The hospital bill was ${rs(totals.claimed)}. Your letter dated ${letterDate} deducted ${rs(totals.total_deducted)} and paid ${rs(totals.paid)}.`

  const points: string[] = []
  disputed.forEach((item, i) => {
    const isDeduction = 'deducted' in item
    const title = isDeduction
      ? `${item.description}${item.line_code ? ` (bill line ${item.line_code})` : ''}: ${rs(item.deducted)}`
      : item.issue
    const lines = [`${i + 1}. ${title}`]
    if (isDeduction) lines.push(indent(`Reason given: "${item.insurer_reason}"`))
    lines.push(indent(`${isDeduction ? 'Why this should be paid: ' : ''}${item.explanation}`))
    const cite = citeLine(item.citations, report.citations)
    if (cite) lines.push(indent(`Relevant terms: ${cite}`))
    points.push(lines.join('\n'))
  })

  const justifyPoints = justify.map((item, i) => {
    const isDeduction = 'deducted' in item
    const title = isDeduction ? `${item.description}: ${rs(item.deducted)}` : item.issue
    return `${i + 1}. ${title}\n${indent(item.explanation)}`
  })

  const relief = totals.claim_rejected
    ? [
        '(a) withdraw the rejection and settle the admissible claim;',
        '(b) pay interest at 2% above the bank rate from the date of claim intimation, as the decision was made after the 15 days allowed; and',
        '(c) send me a copy of my proposal form and confirm that the Claims Review Committee approved the rejection.',
      ]
    : [
        `(a) pay the disputed amount of ${rs(totals.challengeable_amount)}${copay ? `, less the ${copay}% co-payment` : ''}; and`,
        '(b) name the specific policy clause for any deduction you maintain.',
      ]

  if (kind === 'grievance') {
    const body = [
      'Dear Sir or Madam,',
      '',
      ...facts,
      '',
      opening,
      '',
      disputed.length ? (totals.claim_rejected ? 'My grounds are:' : 'I dispute the following deductions:') : '',
      '',
      points.join('\n\n'),
      '',
      !totals.claim_rejected && disputed.length ? `Total disputed: ${rs(totals.challengeable_amount)}.` : '',
      justifyPoints.length
        ? `\nPlease also explain the following, with reference to the specific policy clause and the data you relied on:\n\n${justifyPoints.join('\n\n')}\n`
        : '',
      'Under the IRDAI Master Circular on Protection of Policyholders’ Interests, 2024, a rejection or partial disallowance must be explained with reference to the specific terms and conditions of the policy.',
      '',
      'I request you to:',
      ...relief,
      '',
      `Please acknowledge this grievance and resolve it within 14 days. If it is not resolved, I will approach the Insurance Ombudsman${report.ombudsman_office ? `, ${report.ombudsman_office.city}` : ''}.`,
      '',
      'Enclosures: policy schedule, hospital bill, discharge summary and your decision letter.',
      '',
      'Yours faithfully,',
      '',
      holder,
      city,
      todayText,
    ]
      .join('\n')
      .replace(/\n{3,}/g, '\n\n')

    return {
      kind,
      to: `Grievance Redressal Officer, ${insurer}`,
      subject: `Grievance about claim ${claimNo} under policy ${policyNo}`,
      body,
      generated_by: 'template',
    }
  }

  const office = report.ombudsman_office
  const body = [
    'Respected Ombudsman,',
    '',
    '1. Complainant',
    indent(`Name: ${holder}\nAddress: [your full address], ${city}${input?.policy.state ? `, ${input.policy.state}` : ''}\nPhone / email: [your phone] / [your email]`),
    '',
    '2. Insurer',
    indent(`${insurer}\nPolicy number: ${policyNo}\nClaim number: ${claimNo}`),
    '',
    '3. Nature of complaint',
    indent(totals.claim_rejected ? 'Total rejection of a health insurance claim.' : 'Partial rejection (deductions) of a health insurance claim.'),
    '',
    '4. Facts',
    indent(
      `${opening}\nI sent a written grievance to the insurer on [date of your grievance]. [It was rejected on ___ / I did not receive a reply within 30 days / The reply did not resolve my complaint.]`,
    ),
    '',
    '5. Grounds',
    indent(points.join('\n\n') || 'Details are set out in the enclosed grievance.'),
    '',
    '6. Relief sought',
    indent(
      totals.claim_rejected
        ? `Settlement of the admissible claim (about ${rs(totals.estimated_additional_payable)} after non-payable items and co-payment), with interest for the delayed decision.`
        : `Payment of ${rs(totals.challengeable_amount)}${copay ? ` less the ${copay}% co-payment (about ${rs(totals.estimated_additional_payable)})` : ''}, with interest as applicable.`,
    ),
    '',
    '7. Declarations',
    indent(
      '- This complaint is made within one year of the insurer’s final reply.\n- The same matter is not pending before, and has not been decided by, any court, consumer forum or arbitrator.',
    ),
    '',
    'Enclosures: policy schedule, hospital bill, discharge summary, the insurer’s decision letter, my grievance and the insurer’s reply (if any).',
    '',
    'Yours faithfully,',
    '',
    holder,
    todayText,
  ].join('\n')

  return {
    kind,
    to: office
      ? `The Insurance Ombudsman, ${office.city}${office.address ? ` - ${office.address}` : ''}`
      : 'The Insurance Ombudsman',
    subject: `Complaint under Rule 14 of the Insurance Ombudsman Rules, 2017 against ${insurer} - claim ${claimNo}`,
    body,
    generated_by: 'template',
  }
}

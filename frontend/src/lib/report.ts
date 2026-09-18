import type { CheckFinding, Claim, DeductionFinding, Report, Verdict } from '../api/types'
import { VERDICT_ORDER } from './verdicts'

/** "Arogya Sanjeevani Policy, Niva Bupa Health Insurance Co. Ltd. (UIN …)" -> "Niva Bupa" */
export function shortInsurerName(name: string | null | undefined): string | null {
  if (!name) return null
  let s = name.replace(/\s*\(UIN[^)]*\)\s*$/i, '').trim()
  const comma = s.lastIndexOf(', ')
  if (comma !== -1 && /policy/i.test(s.slice(0, comma))) s = s.slice(comma + 2)
  s = s
    .replace(/\s+(?:Health\s+Insurance|and\s+Allied\s+Insurance|Insurance)\s+(?:Company|Co\.?)\s*(?:Limited|Ltd\.?)?\.?$/i, '')
    .replace(/\s+(Limited|Ltd\.?)$/i, '')
    .trim()
  return s || name
}

/** "Arogya Sanjeevani Policy, Niva Bupa Health Insurance Co. Ltd. (UIN …)" -> "Arogya Sanjeevani Policy" */
export function productName(name: string | null | undefined): string | null {
  if (!name) return null
  const s = name.replace(/\s*\(UIN[^)]*\)\s*$/i, '').trim()
  const comma = s.indexOf(', ')
  return comma === -1 ? s : s.slice(0, comma)
}

export function sortByVerdict<T extends { verdict: Verdict }>(items: T[]): T[] {
  return [...items].sort((a, b) => VERDICT_ORDER.indexOf(a.verdict) - VERDICT_ORDER.indexOf(b.verdict))
}

export function needsAction(verdict: Verdict): boolean {
  return verdict === 'challengeable' || verdict === 'needs_more_info'
}

export interface ReportShape {
  rejected: boolean
  nothingToChallenge: boolean
  challengeableFindings: DeductionFinding[]
  needsInfoFindings: DeductionFinding[]
  actionableChecks: CheckFinding[]
}

export function reportShape(report: Report): ReportShape {
  const t = report.totals
  const challengeableFindings = report.deduction_findings.filter((f) => f.verdict === 'challengeable')
  const needsInfoFindings = report.deduction_findings.filter((f) => f.verdict === 'needs_more_info')
  const actionableChecks = report.check_findings.filter((c) => needsAction(c.verdict))
  const nothingToChallenge =
    !t.claim_rejected &&
    t.challengeable_amount <= 0 &&
    t.needs_more_info_amount <= 0 &&
    challengeableFindings.length === 0 &&
    needsInfoFindings.length === 0 &&
    actionableChecks.length === 0
  return {
    rejected: t.claim_rejected,
    nothingToChallenge,
    challengeableFindings,
    needsInfoFindings,
    actionableChecks,
  }
}

/** Amount a finding contributes to its verdict bucket. */
export function findingAmount(f: DeductionFinding): number {
  if (f.verdict === 'challengeable') return f.amount_challengeable > 0 ? f.amount_challengeable : f.deducted
  return f.deducted
}

export function coPayPct(claim: Claim): number | null {
  return claim.claim_input?.policy.co_payment_pct ?? null
}

/** The date part of an ISO timestamp, e.g. "2026-09-17". */
export function isoDay(timestamp: string): string {
  return timestamp.slice(0, 10)
}

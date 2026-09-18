import { ArrowDown, ChevronLeft, ChevronRight, ListChecks, MessageSquareQuote } from 'lucide-react'
import type { ReactNode } from 'react'
import type { CheckFinding, DeductionFinding, Report } from '../../api/types'
import { cn } from '../../lib/cn'
import { categoryLabel, prettyRupees } from '../../lib/format'
import { VERDICTS } from '../../lib/verdicts'
import { CitationList } from '../CitationCard'
import { Money } from '../Money'
import { StrengthMeter, VerdictChip } from '../Verdict'
import { ComputedFacts } from './ComputedFacts'

export type Selection = { kind: 'deduction'; id: string } | { kind: 'check'; id: string }

const NEXT_STEP: Record<string, ReactNode> = {
  challengeable: 'Include this in your complaint to the insurer. The letter we draft already lists it, with the clause.',
  needs_more_info: 'Ask the insurer, in writing, to show the basis for this cut and the clause it relies on.',
  fair_ask_hospital_to_absorb: 'Ask the hospital’s billing desk to waive it. It’s a polite request, not something they must agree to.',
  fair: 'Nothing to do. Your policy allows this deduction.',
  not_applicable: 'Nothing to do. This check didn’t apply to your claim.',
}

function Label({ children }: { children: ReactNode }) {
  return <h3 className="text-xs font-semibold tracking-[0.08em] text-stone-500 uppercase">{children}</h3>
}

export function FindingHeader({
  finding,
  titleId,
}: {
  finding: DeductionFinding | CheckFinding
  titleId: string
}) {
  const isDeduction = 'deducted' in finding
  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <VerdictChip verdict={finding.verdict} context={isDeduction ? 'deduction' : 'check'} />
        {finding.strength && <StrengthMeter strength={finding.strength} />}
      </div>
      <h2 id={titleId} className="mt-3 font-display text-[1.55rem] leading-tight tracking-tight text-stone-900">
        {isDeduction ? finding.description : finding.issue}
      </h2>
      {isDeduction && (
        <p className="mt-1 text-[13px] text-stone-500">
          {finding.line_code ? `Bill line ${finding.line_code}` : 'Applies across the bill'} · {categoryLabel(finding.category)}
        </p>
      )}
    </div>
  )
}

export function FindingBody({
  finding,
  report,
  onOpenDeduction,
  onGoToLetter,
}: {
  finding: DeductionFinding | CheckFinding
  report: Report
  onOpenDeduction: (id: string) => void
  onGoToLetter?: () => void
}) {
  const isDeduction = 'deducted' in finding
  const meta = VERDICTS[finding.verdict]
  const citationCount = new Set(finding.citations).size

  return (
    <div className="space-y-7">
      {isDeduction && (
        <dl className="grid grid-cols-3 overflow-hidden rounded-xl border border-line">
          <div className="p-3.5">
            <dt className="text-xs text-stone-500">Billed</dt>
            <dd className="mt-0.5 text-[15px] font-semibold text-stone-800">
              {finding.billed ? <Money amount={finding.billed} /> : <span className="text-stone-400">—</span>}
            </dd>
          </div>
          <div className="border-l border-line p-3.5">
            <dt className="text-xs text-stone-500">Deducted</dt>
            <dd className="mt-0.5 text-[15px] font-semibold text-stone-900">
              <Money amount={finding.deducted} />
            </dd>
          </div>
          <div className={cn('border-l border-line p-3.5', finding.amount_challengeable > 0 && 'bg-challenge-50')}>
            <dt className={cn('text-xs', finding.amount_challengeable > 0 ? 'text-challenge-700' : 'text-stone-500')}>
              You can challenge
            </dt>
            <dd
              className={cn(
                'mt-0.5 text-[15px] font-semibold',
                finding.amount_challengeable > 0 ? 'text-challenge-700' : 'text-stone-400',
              )}
            >
              <Money amount={finding.amount_challengeable} />
            </dd>
          </div>
        </dl>
      )}

      {isDeduction && (
        <section>
          <Label>What the insurer said</Label>
          <p className="mt-2 flex gap-2.5 rounded-lg bg-paper-2 px-3.5 py-3 text-[15px] leading-relaxed text-stone-700">
            <MessageSquareQuote className="mt-0.5 size-4 shrink-0 text-stone-400" aria-hidden="true" />
            <span>“{prettyRupees(finding.insurer_reason)}”</span>
          </p>
        </section>
      )}

      <section>
        <Label>What we found</Label>
        <p className="mt-2 text-[15px] leading-relaxed text-stone-800">{prettyRupees(finding.explanation)}</p>
        {isDeduction && finding.matched_item && (
          <p className="mt-3 flex items-start gap-2 text-sm text-stone-600">
            <ListChecks className="mt-0.5 size-4 shrink-0 text-brand-700" aria-hidden="true" />
            <span>
              Matched to your policy’s list as <span className="font-medium text-stone-800">{finding.matched_item}</span>
            </span>
          </p>
        )}
        {!isDeduction && Object.keys(finding.computed).length > 0 && (
          <div className="mt-4">
            <ComputedFacts
              computed={finding.computed}
              findings={report.deduction_findings}
              onOpenFinding={onOpenDeduction}
              compact
            />
          </div>
        )}
      </section>

      <section className={cn('rounded-xl border p-4', meta.classes.border, meta.classes.softBg)}>
        <h3 className={cn('text-sm font-semibold', meta.classes.text)}>What you can do</h3>
        <p className="mt-1 text-sm leading-relaxed text-stone-700">{NEXT_STEP[finding.verdict]}</p>
        {onGoToLetter && (finding.verdict === 'challengeable' || finding.verdict === 'needs_more_info') && (
          <button type="button" onClick={onGoToLetter} className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700 hover:text-brand-900">
            Draft my complaint letter
            <ArrowDown className="size-3.5" aria-hidden="true" />
          </button>
        )}
      </section>

      {citationCount > 0 && (
        <section>
          <Label>
            The {citationCount === 1 ? 'rule' : `${citationCount} rules`} behind this
          </Label>
          <CitationList ids={finding.citations} citations={report.citations} className="mt-3" />
        </section>
      )}
    </div>
  )
}

export function FindingPager({
  index,
  total,
  onPrev,
  onNext,
}: {
  index: number
  total: number
  onPrev: () => void
  onNext: () => void
}) {
  if (total <= 1) return null
  return (
    <div className="flex items-center justify-between gap-3">
      <button type="button" className="btn-ghost btn-sm" onClick={onPrev} disabled={index <= 0}>
        <ChevronLeft className="size-4" aria-hidden="true" />
        Previous
      </button>
      <span className="money text-xs text-stone-500" aria-live="polite">
        {index + 1} of {total}
      </span>
      <button type="button" className="btn-ghost btn-sm" onClick={onNext} disabled={index >= total - 1}>
        Next
        <ChevronRight className="size-4" aria-hidden="true" />
      </button>
    </div>
  )
}

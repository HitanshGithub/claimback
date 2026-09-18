import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import type { Claim, Letter, Report } from '../../api/types'
import { cn } from '../../lib/cn'
import { formatDate, formatINR, prettyRupees } from '../../lib/format'
import { findingAmount, needsAction, reportShape, sortByVerdict } from '../../lib/report'
import { Money } from '../Money'
import { VerdictChip } from '../Verdict'
import { SectionHeading } from '../SectionHeading'
import { Sheet } from '../Sheet'
import { ComputedFacts, hasComparison } from './ComputedFacts'
import { FindingBody, FindingHeader, FindingPager } from './FindingDetail'
import { FindingsPaper, type PaperRow } from './FindingsPaper'
import { LetterSection } from './LetterSection'
import {
  AlternateWordingsCallout,
  CheckFindingsSection,
  Disclaimer,
  DocumentsSection,
  NextStepsSection,
  SimilarCasesSection,
} from './Sections'
import { SummaryHeader } from './SummaryHeader'

function ReportNav({ items }: { items: { id: string; label: string }[] }) {
  const [active, setActive] = useState(items[0]?.id)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-140px 0px -55% 0px' },
    )
    items.forEach((item) => {
      const el = document.getElementById(item.id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [items])

  return (
    <nav aria-label="Report sections" className="sticky top-16 z-30 mt-10 border-y border-line bg-paper/95 supports-[backdrop-filter]:bg-paper/85 supports-[backdrop-filter]:backdrop-blur-sm print:hidden">
      <div className="container-page">
        <ul className="-mx-2 flex gap-1 overflow-x-auto py-2 scrollbar-none">
          {items.map((item) => (
            <li key={item.id} className="shrink-0">
              <a
                href={`#${item.id}`}
                aria-current={active === item.id ? 'true' : undefined}
                onClick={(e) => {
                  e.preventDefault()
                  document.getElementById(item.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  history.replaceState(null, '', `${location.pathname}${location.search}#${item.id}`)
                  setActive(item.id)
                }}
                className={cn(
                  'block rounded-lg px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors',
                  active === item.id ? 'bg-white text-stone-900 shadow-card ring-1 ring-line' : 'text-stone-600 hover:text-stone-900',
                )}
              >
                {item.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  )
}

function PaperHeader({ claim, report, rejected }: { claim: Claim; report: Report; rejected: boolean }) {
  const input = claim.claim_input
  const decision = input?.decision
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 px-5 pt-5 pb-4 sm:px-6 sm:pt-6">
      <div className="min-w-0">
        <p className="text-[11px] font-semibold tracking-[0.1em] text-stone-500 uppercase">
          {rejected ? 'Insurer’s rejection letter' : 'Insurer’s settlement letter'}
        </p>
        <p className="mt-1 font-display text-xl leading-tight tracking-tight text-stone-900">
          {input?.admission.hospital_name ?? claim.title}
        </p>
        {decision && (
          <p className="mt-1 text-[13px] text-stone-500">
            Claim {decision.claim_number} · Letter dated {formatDate(decision.letter_date)}
            {input?.admission.claim_type ? ` · ${input.admission.claim_type === 'cashless' ? 'Cashless' : 'Reimbursement'}` : ''}
          </p>
        )}
      </div>
      <div className="sm:text-right">
        <p className="text-xs text-stone-500">{rejected ? 'Claimed, not paid' : 'Total deducted'}</p>
        <p className="money text-2xl font-semibold tracking-tight text-stone-900">
          {formatINR(rejected ? report.totals.claimed : report.totals.total_deducted)}
        </p>
      </div>
    </div>
  )
}

export function ReportView({
  claim,
  report,
  onLetterSaved,
}: {
  claim: Claim
  report: Report
  onLetterSaved: (letter: Letter) => void
}) {
  const shape = reportShape(report)
  const [searchParams, setSearchParams] = useSearchParams()
  const findingParam = searchParams.get('finding')
  const [pagerIds, setPagerIds] = useState<string[] | null>(null)

  const deductionIds = report.deduction_findings.map((f) => f.id)
  const checksSorted = useMemo(() => sortByVerdict(report.check_findings), [report.check_findings])
  const checkIds = checksSorted.map((c) => c.id)

  const selectedDeduction = report.deduction_findings.find((f) => f.id === findingParam)
  const selectedCheck = selectedDeduction ? undefined : report.check_findings.find((c) => c.id === findingParam)
  const selected = selectedDeduction ?? selectedCheck ?? null

  const setFinding = useCallback(
    (id: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (id) next.set('finding', id)
          else next.delete('finding')
          return next
        },
        { replace: true, preventScrollReset: true },
      )
    },
    [setSearchParams],
  )

  const openDeduction = (id: string, ids?: string[]) => {
    setPagerIds(ids ?? deductionIds)
    setFinding(id)
  }
  const openCheck = (id: string, ids?: string[]) => {
    setPagerIds(ids ?? checkIds)
    setFinding(id)
  }

  const goToLetter = () => {
    setFinding(null)
    window.setTimeout(() => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          next.delete('finding')
          return next
        },
        { replace: true, preventScrollReset: true },
      )
      document.getElementById('letter')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 280)
  }

  const pager = (() => {
    if (!selected) return null
    const ids = pagerIds && pagerIds.includes(selected.id) ? pagerIds : selectedDeduction ? deductionIds : checkIds
    const index = ids.indexOf(selected.id)
    return { ids, index }
  })()

  // Rows for the signature paper
  const billRows: PaperRow[] = report.deduction_findings.map((f) => ({
    id: f.id,
    verdict: f.verdict,
    title: f.description,
    code: f.line_code,
    subtitle: `Insurer: “${prettyRupees(f.insurer_reason)}”`,
    billed: f.billed,
    deducted: f.deducted,
    partial: f.verdict === 'challengeable' && f.amount_challengeable > 0 && f.amount_challengeable < f.deducted ? f.amount_challengeable : null,
    amount: findingAmount(f),
  }))
  const checkRows: PaperRow[] = checksSorted.map((c) => ({
    id: c.id,
    verdict: c.verdict,
    title: c.issue,
    subtitle: prettyRupees(c.explanation),
    strength: c.strength,
    amount: 0,
  }))

  const showBill = !shape.rejected && billRows.length > 0
  const keyFacts = shape.rejected ? checksSorted.filter((c) => needsAction(c.verdict) && hasComparison(c.computed)) : []
  const decision = claim.claim_input?.decision

  const navItems = [
    { id: 'summary', label: 'Summary' },
    showBill ? { id: 'bill', label: 'Your bill' } : null,
    shape.rejected ? { id: 'bill', label: 'The rejection' } : null,
    !shape.rejected && report.check_findings.length ? { id: 'checks', label: 'Other checks' } : null,
    report.alternate_wordings.length ? { id: 'wordings', label: 'Other wordings' } : null,
    report.similar_cases.length ? { id: 'cases', label: 'Similar decisions' } : null,
    { id: 'next-steps', label: 'Next steps' },
    { id: 'letter', label: 'Letter' },
    claim.documents.length ? { id: 'documents', label: 'Documents' } : null,
  ].filter((x): x is { id: string; label: string } => x !== null)
  const navKey = navItems.map((n) => `${n.id}:${n.label}`).join('|')
  const stableNav = useMemo(
    () => navKey.split('|').map((pair) => ({ id: pair.split(':')[0], label: pair.slice(pair.indexOf(':') + 1) })),
    [navKey],
  )

  return (
    <div className="pb-4">
      <SummaryHeader claim={claim} report={report} />
      <ReportNav items={stableNav} />

      <div className="container-page mt-14 space-y-24">
        {showBill && (
          <section id="bill" aria-labelledby="bill-heading" className="scroll-mt-32">
            <SectionHeading
              id="bill-heading"
              eyebrow="Your bill, checked"
              title="Every deduction, line by line"
              description="The colour shows what we found. Select a line to see why, with the exact clause from your policy or the rules."
            />
            <div className="mt-8">
              <FindingsPaper
                mode="bill"
                rows={billRows}
                selectedId={selectedDeduction?.id ?? null}
                onSelect={(id, visibleIds) => openDeduction(id, visibleIds)}
                header={<PaperHeader claim={claim} report={report} rejected={false} />}
                footerNote={(visible) => {
                  const challengeable = visible
                    .filter((r) => r.verdict === 'challengeable')
                    .reduce((s, r) => s + r.amount, 0)
                  const deducted = visible.reduce((s, r) => s + (r.deducted ?? 0), 0)
                  return (
                    <span className="flex flex-wrap items-center gap-x-5 gap-y-1">
                      <span className="text-stone-600">
                        Deducted <Money amount={deducted} className="font-semibold text-stone-900" />
                      </span>
                      {challengeable > 0 && (
                        <span className="font-medium text-challenge-700">
                          You can challenge <Money amount={challengeable} className="font-semibold" />
                        </span>
                      )}
                    </span>
                  )
                }}
              />
            </div>
          </section>
        )}

        {shape.rejected && (
          <section id="bill" aria-labelledby="bill-heading" className="scroll-mt-32">
            <SectionHeading
              id="bill-heading"
              eyebrow="The rejection, checked"
              title="Why the insurer said no, and whether it holds up"
              description="We checked the insurer’s reasons against your policy wording and IRDAI’s rules. Select a point to see the clause behind it."
            />
            {keyFacts.length > 0 && (
              <ul className="mt-8 grid gap-4 md:grid-cols-2" aria-label="The numbers that matter">
                {keyFacts.map((check) => (
                  <li key={check.id} className="card flex flex-col p-5">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-[15px] leading-snug font-semibold text-stone-900">{check.issue}</p>
                      <VerdictChip verdict={check.verdict} context="check" size="sm" />
                    </div>
                    <div className="mt-3">
                      <ComputedFacts computed={check.computed} comparisonsOnly />
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-8">
              <FindingsPaper
                mode="checks"
                rows={checkRows}
                selectedId={selectedCheck?.id ?? null}
                onSelect={(id, visibleIds) => openCheck(id, visibleIds)}
                header={<PaperHeader claim={claim} report={report} rejected />}
                intro={
                  decision?.repudiation_reason ? (
                    <div className="px-5 pb-5 sm:px-6">
                      <p className="text-xs font-semibold tracking-[0.06em] text-stone-500 uppercase">What the insurer wrote</p>
                      <blockquote className="mt-2 border-l-2 border-challenge-200 pl-4 font-display text-[16px] leading-relaxed text-stone-700 italic">
                        “{prettyRupees(decision.repudiation_reason)}”
                      </blockquote>
                      {decision.clauses_cited.length > 0 && (
                        <p className="mt-3 flex flex-wrap gap-1.5">
                          {decision.clauses_cited.map((c) => (
                            <span key={c} className="rounded-full bg-paper-2 px-2.5 py-1 text-xs font-medium text-stone-600 ring-1 ring-line">
                              {c}
                            </span>
                          ))}
                        </p>
                      )}
                    </div>
                  ) : undefined
                }
                footerNote={() => {
                  const grounds = report.check_findings.filter((c) => c.verdict === 'challengeable').length
                  const asks = report.check_findings.filter((c) => c.verdict === 'needs_more_info').length
                  return (
                    <span className="flex flex-wrap gap-x-5 gap-y-1">
                      {grounds > 0 && (
                        <span className="font-medium text-challenge-700">
                          {grounds} {grounds === 1 ? 'ground' : 'grounds'} to challenge
                        </span>
                      )}
                      {asks > 0 && (
                        <span className="font-medium text-info-700">
                          {asks} {asks === 1 ? 'thing' : 'things'} to ask the insurer
                        </span>
                      )}
                    </span>
                  )
                }}
              />
            </div>
          </section>
        )}

        {!shape.rejected && (
          <CheckFindingsSection
            report={report}
            onOpenCheck={(id) => openCheck(id)}
            onOpenDeduction={(id) => openDeduction(id)}
          />
        )}

        <AlternateWordingsCallout report={report} />
        <SimilarCasesSection report={report} />
        <NextStepsSection
          report={report}
          onDraftLetter={() => {
            setSearchParams(
              (prev) => {
                const next = new URLSearchParams(prev)
                next.set('letter', 'grievance')
                return next
              },
              { replace: true, preventScrollReset: true },
            )
            document.getElementById('letter')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }}
        />
        <LetterSection
          key={claim.id}
          claim={claim}
          muted={shape.nothingToChallenge}
          onLetterSaved={onLetterSaved}
        />
        <DocumentsSection claim={claim} />
        <Disclaimer text={report.disclaimer} />
      </div>

      <Sheet
        open={selected !== null}
        onClose={() => setFinding(null)}
        labelledBy="finding-title"
        header={selected ? <FindingHeader finding={selected} titleId="finding-title" /> : null}
        footer={
          pager && pager.ids.length > 1 ? (
            <FindingPager
              index={pager.index}
              total={pager.ids.length}
              onPrev={() => setFinding(pager.ids[pager.index - 1])}
              onNext={() => setFinding(pager.ids[pager.index + 1])}
            />
          ) : undefined
        }
      >
        {selected && (
          <FindingBody
            key={selected.id}
            finding={selected}
            report={report}
            onOpenDeduction={(id) => openDeduction(id)}
            onGoToLetter={goToLetter}
          />
        )}
      </Sheet>
    </div>
  )
}

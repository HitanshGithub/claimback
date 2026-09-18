import {
  ArrowRight,
  ArrowUpRight,
  CalendarClock,
  CircleCheck,
  ExternalLink,
  FileText,
  History,
  Info,
  Landmark,
  Mail,
  MapPin,
  Phone,
} from 'lucide-react'
import { useState } from 'react'
import type { Claim, DocumentKind, Report, SimilarCase } from '../../api/types'
import { documentUrl } from '../../api/client'
import { cn } from '../../lib/cn'
import { categoryLabel, formatDate, prettyRupees } from '../../lib/format'
import { isoDay, shortInsurerName, sortByVerdict } from '../../lib/report'
import { outcomeMeta } from '../../lib/verdicts'
import { CitationList } from '../CitationCard'
import { Money } from '../Money'
import { SectionHeading } from '../SectionHeading'
import { StrengthMeter, VerdictChip } from '../Verdict'
import { ComputedFacts } from './ComputedFacts'

// ---------------------------------------------------------------------------
// Other checks
// ---------------------------------------------------------------------------

export function CheckFindingsSection({
  report,
  onOpenCheck,
  onOpenDeduction,
}: {
  report: Report
  onOpenCheck: (id: string) => void
  onOpenDeduction: (id: string) => void
}) {
  const checks = sortByVerdict(report.check_findings)
  if (checks.length === 0) return null
  return (
    <section id="checks" aria-labelledby="checks-heading" className="scroll-mt-32">
      <SectionHeading
        id="checks-heading"
        eyebrow="Other checks"
        title="Beyond the line items"
        description="Checks on the whole claim: the insurer’s letter, co-pay maths, room rent, waiting periods and deadlines."
      />
      <ul className="mt-8 grid gap-4 md:grid-cols-2">
        {checks.map((check) => {
          const cites = new Set(check.citations).size
          return (
            <li key={check.id} className="card flex flex-col p-5 sm:p-6">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                <VerdictChip verdict={check.verdict} context="check" />
                {check.strength && <StrengthMeter strength={check.strength} />}
              </div>
              <h3 className="mt-3 text-[17px] leading-snug font-semibold text-stone-900">{check.issue}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-stone-600">{prettyRupees(check.explanation)}</p>
              {Object.keys(check.computed).length > 0 && (
                <div className="mt-4">
                  <ComputedFacts
                    computed={check.computed}
                    findings={report.deduction_findings}
                    onOpenFinding={onOpenDeduction}
                  />
                </div>
              )}
              {cites > 0 && (
                <div className="mt-auto pt-4">
                  <button
                    type="button"
                    onClick={() => onOpenCheck(check.id)}
                    aria-haspopup="dialog"
                    className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700 hover:text-brand-900"
                  >
                    See the {cites === 1 ? 'rule' : `${cites} rules`}
                    <ArrowRight className="size-3.5" aria-hidden="true" />
                  </button>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Alternate wordings
// ---------------------------------------------------------------------------

export function AlternateWordingsCallout({ report }: { report: Report }) {
  if (report.alternate_wordings.length === 0) return null
  const yours = shortInsurerName(report.policy_wording_name) ?? 'Your policy'
  return (
    <section
      id="wordings"
      aria-labelledby="wordings-heading"
      className="relative scroll-mt-32 overflow-hidden rounded-2xl bg-brand-800 px-5 py-8 text-white sm:px-10 sm:py-10"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-24 -right-24 size-72 rounded-full border border-white/10"
      />
      <div aria-hidden="true" className="pointer-events-none absolute -top-10 -right-10 size-44 rounded-full border border-white/10" />
      <p className="text-xs font-semibold tracking-[0.12em] text-brand-200 uppercase">Why your exact wording matters</p>
      <h2 id="wordings-heading" className="mt-2 max-w-2xl font-display text-[1.75rem] leading-tight tracking-tight sm:text-[2.1rem]">
        Same bill. Different insurer’s wording. A different answer.
      </h2>
      <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-brand-100">
        Arogya Sanjeevani is meant to be a standard product, but insurers word some clauses differently. That’s why
        ClaimBack judges your claim against your own policy wording.
      </p>
      <div className="mt-8 grid items-stretch gap-3 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
        <div className="rounded-xl bg-white p-5 text-stone-900 shadow-raised sm:p-6">
          <p className="text-xs font-semibold tracking-[0.08em] text-brand-700 uppercase">Your policy · {yours}</p>
          <p className="mt-2 text-4xl font-semibold tracking-tight text-challenge-700">
            <Money amount={report.totals.challengeable_amount} />
          </p>
          <p className="mt-1 text-sm text-stone-600">you can challenge</p>
          <p className="mt-3 border-t border-line pt-3 text-sm leading-relaxed text-stone-600">
            This is the wording your claim is judged against.
          </p>
        </div>
        <span
          aria-hidden="true"
          className="mx-auto flex size-10 items-center justify-center self-center rounded-full bg-brand-900 font-display text-sm text-brand-100 ring-1 ring-white/15"
        >
          vs
        </span>
        {report.alternate_wordings.map((alt) => (
          <div key={alt.policy_wording_id} className="rounded-xl bg-white/[0.08] p-5 ring-1 ring-white/15 sm:p-6">
            <p className="text-xs font-semibold tracking-[0.08em] text-brand-100 uppercase">
              {shortInsurerName(alt.insurer) ?? alt.insurer}’s wording
            </p>
            <p className="mt-2 text-4xl font-semibold tracking-tight text-white">
              <Money amount={alt.challengeable_amount} />
            </p>
            <p className="mt-1 text-sm text-brand-100">would be challengeable</p>
            <p className="mt-3 border-t border-white/10 pt-3 text-sm leading-relaxed text-brand-50/90">{prettyRupees(alt.note)}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Similar decisions
// ---------------------------------------------------------------------------

function CaseCard({ item }: { item: SimilarCase }) {
  const [expanded, setExpanded] = useState(false)
  const outcome = outcomeMeta(item.decision)
  return (
    <article className="card flex h-full flex-col p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={cn('rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset', outcome.classes)}>
          {outcome.label}
        </span>
        <span className="text-xs text-stone-500">{formatDate(item.decision_date)}</span>
      </div>
      <h3 className="mt-3 text-[15px] leading-snug font-semibold text-stone-900">{item.forum}</h3>
      <p className="mt-1 text-[13px] text-stone-500">
        {categoryLabel(item.category)}
        {item.amount_awarded_inr ? (
          <>
            {' · '}Awarded <Money amount={item.amount_awarded_inr} className="font-medium text-stone-700" />
          </>
        ) : null}
      </p>
      <dl className="mt-4 space-y-3.5 text-sm leading-relaxed">
        <div>
          <dt className="text-xs font-semibold tracking-[0.06em] text-stone-500 uppercase">The insurer’s reason</dt>
          <dd className={cn('mt-1 text-stone-700', !expanded && 'line-clamp-3')}>{prettyRupees(item.insurer_reason)}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold tracking-[0.06em] text-stone-500 uppercase">What was decided</dt>
          <dd className={cn('mt-1 text-stone-700', !expanded && 'line-clamp-4')}>{prettyRupees(item.reasoning)}</dd>
        </div>
      </dl>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="mt-2 self-start text-sm font-medium text-brand-700 hover:text-brand-900"
      >
        {expanded ? 'Show less' : 'Read more'}
      </button>
      <div className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        {item.decided_before_2024_health_rules ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-paper-2 px-2.5 py-1 text-xs font-medium text-stone-600">
            <History className="size-3.5" aria-hidden="true" />
            Decided before 2024 rules
          </span>
        ) : (
          <span />
        )}
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:text-brand-900 hover:underline"
        >
          Read the decision
          <ArrowUpRight className="size-3.5" aria-hidden="true" />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      </div>
    </article>
  )
}

export function SimilarCasesSection({ report }: { report: Report }) {
  const cases = report.similar_cases
  if (cases.length === 0) return null
  const won = cases.filter((c) => c.decision === 'allowed').length
  const partly = cases.filter((c) => c.decision === 'partly_allowed').length
  const lost = cases.filter((c) => c.decision === 'dismissed').length
  const tally = [won && `${won} won`, partly && `${partly} partly won`, lost && `${lost} lost`].filter(Boolean).join(' · ')
  return (
    <section id="cases" aria-labelledby="cases-heading" className="scroll-mt-32">
      <SectionHeading
        id="cases-heading"
        eyebrow="Similar real decisions"
        title="How Ombudsmen and courts decided cases like yours"
        description="Including cases the policyholder lost. Most were decided before the 2024 rules, so read them for how forums reason. The current rules cited above are what count."
        action={tally ? <p className="text-sm text-stone-500">{tally}</p> : undefined}
      />
      <ul className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cases.map((c) => (
          <li key={c.case_id}>
            <CaseCard item={c} />
          </li>
        ))}
      </ul>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Next steps
// ---------------------------------------------------------------------------

function OmbudsmanCard({ report }: { report: Report }) {
  const office = report.ombudsman_office
  if (!office) return null
  const phones = (office.phone ?? '')
    .split('/')
    .map((p) => p.trim())
    .filter(Boolean)
  const prefix = phones[0]?.match(/^(\d{2,4})-/)?.[1]
  const phoneLinks = phones.map((p) => (/^\d{6,8}$/.test(p) && prefix ? `${prefix}-${p}` : p))

  return (
    <aside aria-labelledby="ombudsman-heading" className="card self-start p-6 lg:sticky lg:top-36">
      <span className="flex size-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
        <Landmark className="size-5" aria-hidden="true" />
      </span>
      <p className="mt-4 text-xs font-semibold tracking-[0.1em] text-stone-500 uppercase">Your Insurance Ombudsman</p>
      <h3 id="ombudsman-heading" className="mt-1 font-display text-2xl tracking-tight text-stone-900">
        {office.city}
      </h3>
      <p className="mt-2 text-sm leading-relaxed text-stone-600">
        Independent and free to use. Hears claims up to ₹50 lakh once you’ve complained to the insurer first.
      </p>
      <dl className="mt-5 space-y-3.5 text-sm">
        {office.address && (
          <div className="flex gap-3">
            <dt>
              <MapPin className="mt-0.5 size-4 text-stone-400" aria-hidden="true" />
              <span className="sr-only">Address</span>
            </dt>
            <dd className="leading-relaxed text-stone-700">{office.address}</dd>
          </div>
        )}
        {office.email && (
          <div className="flex gap-3">
            <dt>
              <Mail className="mt-0.5 size-4 text-stone-400" aria-hidden="true" />
              <span className="sr-only">Email</span>
            </dt>
            <dd>
              <a href={`mailto:${office.email}`} className="link break-all">
                {office.email}
              </a>
            </dd>
          </div>
        )}
        {phoneLinks.length > 0 && (
          <div className="flex gap-3">
            <dt>
              <Phone className="mt-0.5 size-4 text-stone-400" aria-hidden="true" />
              <span className="sr-only">Phone</span>
            </dt>
            <dd className="flex flex-wrap gap-x-3 gap-y-1">
              {phoneLinks.map((p) => (
                <a key={p} href={`tel:${p.replace(/[^\d+]/g, '')}`} className="link money">
                  {p}
                </a>
              ))}
            </dd>
          </div>
        )}
      </dl>
      <a
        href="https://cioins.co.in/Complaint/Online"
        target="_blank"
        rel="noopener noreferrer"
        className="btn-secondary mt-6 w-full"
      >
        File online at cioins.co.in
        <ExternalLink className="size-4" aria-hidden="true" />
        <span className="sr-only">(opens in a new tab)</span>
      </a>
    </aside>
  )
}

export function NextStepsSection({
  report,
  onDraftLetter,
}: {
  report: Report
  onDraftLetter: () => void
}) {
  const steps = [...report.escalation].sort((a, b) => a.step - b.step)
  const today = isoDay(report.generated_at)

  return (
    <section id="next-steps" aria-labelledby="next-heading" className="scroll-mt-32">
      <SectionHeading
        id="next-heading"
        eyebrow="What to do next"
        title={steps.length ? 'Your next steps, with dates' : 'You don’t need to do anything'}
        description={
          steps.length
            ? 'Start with the insurer. Each step has a deadline set by the rules, and you only move on if the step before doesn’t fix it.'
            : undefined
        }
      />
      {steps.length === 0 ? (
        <div className="mt-8 flex gap-4 rounded-xl border border-fair-200 bg-fair-50 p-5 sm:p-6">
          <CircleCheck className="mt-0.5 size-6 shrink-0 text-fair-600" aria-hidden="true" />
          <div>
            <p className="font-semibold text-fair-800">Every deduction in this claim follows your policy.</p>
            <p className="mt-1 text-[15px] leading-relaxed text-stone-700">
              There’s nothing to complain about, so you can skip the grievance process. Keep this report with your claim
              papers in case a question comes up later.
            </p>
          </div>
        </div>
      ) : (
        <div className="mt-10 grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <ol className="relative">
            {steps.map((step, i) => {
              const last = i === steps.length - 1
              const now = step.due_date !== null && step.due_date <= today
              return (
                <li key={step.step} className={cn('relative pl-14 sm:pl-16', !last && 'pb-6')}>
                  {!last && <span aria-hidden="true" className="absolute top-11 bottom-0 left-[19px] w-px bg-line-strong" />}
                  <span
                    aria-hidden="true"
                    className={cn(
                      'absolute top-0 left-0 flex size-10 items-center justify-center rounded-full font-display text-lg',
                      i === 0 ? 'bg-brand-700 text-white' : 'bg-white text-brand-800 ring-1 ring-line-strong',
                    )}
                  >
                    {step.step}
                  </span>
                  <div className="card p-5 sm:p-6">
                    <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
                      <h3 className="text-[17px] leading-snug font-semibold text-stone-900">
                        <span className="sr-only">Step {step.step}: </span>
                        {step.title}
                      </h3>
                      {step.due_date && (
                        <span
                          className={cn(
                            'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold',
                            now && i === 0 ? 'bg-brand-700 text-white' : 'bg-paper-2 text-stone-700 ring-1 ring-line ring-inset',
                          )}
                        >
                          <CalendarClock className="size-3.5" aria-hidden="true" />
                          {now ? 'Today' : formatDate(step.due_date)}
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-[15px] leading-relaxed text-stone-700">{prettyRupees(step.action)}</p>
                    <p className="mt-3 flex gap-2 text-sm leading-relaxed text-stone-500">
                      <Info className="mt-0.5 size-4 shrink-0 text-stone-400" aria-hidden="true" />
                      <span>{prettyRupees(step.deadline_note)}</span>
                    </p>
                    <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-3">
                      {i === 0 && (
                        <button type="button" onClick={onDraftLetter} className="btn-primary btn-sm">
                          Draft my complaint letter
                          <ArrowRight className="size-3.5" aria-hidden="true" />
                        </button>
                      )}
                      {step.citations.length > 0 && (
                        <details className="group w-full [&_summary::-webkit-details-marker]:hidden">
                          <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 text-sm font-medium text-brand-700 hover:text-brand-900">
                            <span className="group-open:hidden">Show the rules behind this</span>
                            <span className="hidden group-open:inline">Hide the rules</span>
                            <span className="money rounded-full bg-brand-50 px-1.5 text-xs">{new Set(step.citations).size}</span>
                          </summary>
                          <CitationList ids={step.citations} citations={report.citations} className="mt-3" />
                        </details>
                      )}
                    </div>
                  </div>
                </li>
              )
            })}
          </ol>
          <OmbudsmanCard report={report} />
        </div>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Documents + disclaimer
// ---------------------------------------------------------------------------

const DOC_LABELS: Record<DocumentKind, string> = {
  policy_schedule: 'Policy schedule',
  hospital_bill: 'Hospital bill',
  insurer_letter: 'Insurer’s letter',
  discharge_summary: 'Discharge summary',
  other: 'Other document',
}

export function DocumentsSection({ claim }: { claim: Claim }) {
  if (claim.documents.length === 0) return null
  return (
    <section id="documents" aria-labelledby="documents-heading" className="scroll-mt-32">
      <SectionHeading id="documents-heading" eyebrow="Documents" title="What we read" />
      <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {claim.documents.map((doc) => {
          const url = documentUrl(claim.id, doc.kind)
          const inner = (
            <>
              <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-paper-2 text-stone-600 ring-1 ring-line">
                <FileText className="size-5" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold text-stone-900">{DOC_LABELS[doc.kind] ?? doc.kind}</span>
                <span className="block truncate text-[13px] text-stone-500" title={doc.filename}>
                  {doc.filename}
                </span>
              </span>
              {url ? (
                <ArrowUpRight className="size-4 shrink-0 text-stone-400 group-hover:text-brand-700" aria-hidden="true" />
              ) : null}
            </>
          )
          return (
            <li key={`${doc.kind}-${doc.filename}`}>
              {url ? (
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group card flex items-center gap-3 p-4 transition-colors hover:border-line-strong"
                >
                  {inner}
                  <span className="sr-only">(opens in a new tab)</span>
                </a>
              ) : (
                <div className="card flex items-center gap-3 p-4" title="Documents can’t be opened in demo mode">
                  {inner}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export function Disclaimer({ text }: { text: string }) {
  return (
    <aside className="flex gap-4 rounded-xl border border-line bg-paper-2/70 p-5 sm:p-6">
      <Info className="mt-0.5 size-5 shrink-0 text-stone-500" aria-hidden="true" />
      <p className="text-sm leading-relaxed text-stone-600">
        <span className="font-semibold text-stone-800">Please read: </span>
        {text}
      </p>
    </aside>
  )
}

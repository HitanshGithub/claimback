import { BadgeCheck, ChevronRight, CircleAlert, CircleCheck, CircleHelp, Cog, Hospital, ScrollText } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import type { Claim, Report } from '../../api/types'
import { cn } from '../../lib/cn'
import { formatDate, formatDateRange, formatINR, plural, prettyRupees } from '../../lib/format'
import { coPayPct, productName, reportShape, shortInsurerName } from '../../lib/report'
import { strongest } from '../../lib/verdicts'
import { CountUpMoney, Money } from '../Money'
import { StrengthMeter } from '../Verdict'

function ClaimFacts({ claim }: { claim: Claim }) {
  const input = claim.claim_input
  if (!input) return null
  const a = input.admission
  const facts = [
    { label: 'Patient', value: a.patient_name },
    { label: 'Hospital', value: a.hospital_name },
    { label: 'Stay', value: formatDateRange(a.admission_date, a.discharge_date) },
    { label: 'Claim type', value: a.claim_type === 'cashless' ? 'Cashless' : 'Reimbursement' },
    { label: 'Claim no.', value: input.decision.claim_number },
  ]
  return (
    <dl className="mt-7 flex flex-wrap gap-x-8 gap-y-4 border-t border-line pt-6">
      {facts.map((f) => (
        <div key={f.label} className="min-w-0">
          <dt className="text-xs text-stone-500">{f.label}</dt>
          <dd className="mt-0.5 text-sm font-medium break-words text-stone-800">
            {f.value}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function Figure({ label, amount, tone = 'default' }: { label: string; amount: number; tone?: 'default' | 'muted' }) {
  return (
    <div className="min-w-0 px-4 py-3.5 first:pl-5 sm:px-5 sm:first:pl-6">
      <dt className="text-xs text-stone-500">{label}</dt>
      <dd className={cn('mt-0.5 text-[15px] font-semibold', tone === 'muted' ? 'text-stone-600' : 'text-stone-900')}>
        <Money amount={amount} />
      </dd>
    </div>
  )
}

function KeyFigures({ claim, report }: { claim: Claim; report: Report }) {
  const t = report.totals
  const shape = reportShape(report)
  const pct = coPayPct(claim)
  const coPayText = pct ? `after your ${pct}% co-pay` : 'after co-pay'

  const secondary = (
    <dl className="grid grid-cols-3 divide-x divide-line border-t border-line bg-paper/50">
      <Figure label="Claimed" amount={t.claimed} />
      <Figure label="Insurer paid" amount={t.paid} />
      {shape.rejected ? (
        <Figure label="Not paid" amount={t.total_deducted} />
      ) : (
        <Figure label="Deducted" amount={t.total_deducted} />
      )}
    </dl>
  )

  const extras: { key: string; icon: typeof Hospital; text: React.ReactNode; className: string }[] = []
  if (!shape.rejected && t.challengeable_amount > 0 && t.needs_more_info_amount > 0) {
    extras.push({
      key: 'info',
      icon: CircleHelp,
      className: 'text-info-700',
      text: (
        <>
          Ask the insurer to justify another <Money amount={t.needs_more_info_amount} className="font-semibold" />
        </>
      ),
    })
  }
  if (t.ask_hospital_amount > 0) {
    extras.push({
      key: 'hospital',
      icon: Hospital,
      className: 'text-absorb-700',
      text: (
        <>
          You can ask the hospital to waive <Money amount={t.ask_hospital_amount} className="font-semibold" />
        </>
      ),
    })
  }

  let lead: React.ReactNode
  if (shape.rejected) {
    const strength = strongest(shape.actionableChecks.map((c) => c.strength))
    const strongCount = shape.actionableChecks.filter((c) => c.verdict === 'challengeable' && c.strength === 'strong').length
    lead = (
      <>
        <div className="border-b border-challenge-100 bg-challenge-50 px-5 py-6 sm:px-6">
          <p className="flex items-center gap-2 text-sm font-semibold text-challenge-700">
            <CircleAlert className="size-4" aria-hidden="true" />
            Claim rejected
          </p>
          <p className="mt-1.5 text-[2.6rem] leading-none font-semibold tracking-tight text-challenge-700 sm:text-5xl">
            <CountUpMoney amount={t.claimed} />
          </p>
          <p className="mt-2 text-sm text-challenge-800/80">Your insurer refused to pay any of it.</p>
        </div>
        <div className="px-5 py-5 sm:px-6">
          <p className="text-sm font-medium text-stone-700">How strong is your challenge?</p>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
            {strength && <StrengthMeter strength={strength} className="text-sm text-stone-900" />}
            {strongCount > 0 && (
              <span className="text-sm text-stone-500">· {plural(strongCount, 'strong ground')}</span>
            )}
          </div>
          {t.estimated_additional_payable > 0 && (
            <div className="mt-5 rounded-xl bg-brand-50 p-4">
              <p className="text-sm text-brand-900">If the rejection is overturned, you could get about</p>
              <p className="mt-1 text-3xl font-semibold tracking-tight text-brand-800">
                <CountUpMoney amount={t.estimated_additional_payable} delayMs={250} />
              </p>
              <p className="mt-1 text-xs text-brand-900/70">after non-payable items and {coPayText.replace('after ', '')}</p>
            </div>
          )}
        </div>
      </>
    )
  } else if (t.challengeable_amount > 0) {
    const n = shape.challengeableFindings.length
    lead = (
      <>
        <div className="border-b border-challenge-100 bg-challenge-50 px-5 py-6 sm:px-6">
          <p className="flex items-center gap-2 text-sm font-semibold text-challenge-700">
            <CircleAlert className="size-4" aria-hidden="true" />
            You can challenge
          </p>
          <p className="mt-1.5 text-[2.6rem] leading-none font-semibold tracking-tight text-challenge-700 sm:text-5xl">
            <CountUpMoney amount={t.challengeable_amount} />
          </p>
          {n > 0 && (
            <p className="mt-2 text-sm text-challenge-800/80">
              {n === 1 ? '1 deduction doesn’t' : `${n} deductions don’t`} hold up against your policy
            </p>
          )}
        </div>
        <div className="px-5 py-5 sm:px-6">
          <p className="text-sm text-stone-600">Estimated extra you could get</p>
          <p className="mt-1 text-3xl font-semibold tracking-tight text-brand-800">
            <CountUpMoney amount={t.estimated_additional_payable} delayMs={250} />
          </p>
          <p className="mt-1 text-xs text-stone-500">{coPayText}</p>
        </div>
      </>
    )
  } else if (t.needs_more_info_amount > 0) {
    const n = shape.needsInfoFindings.length
    const upside = pct ? t.needs_more_info_amount * (1 - pct / 100) : null
    lead = (
      <>
        <div className="border-b border-info-100 bg-info-50 px-5 py-6 sm:px-6">
          <p className="flex items-center gap-2 text-sm font-semibold text-info-700">
            <CircleHelp className="size-4" aria-hidden="true" />
            Ask your insurer to justify
          </p>
          <p className="mt-1.5 text-[2.6rem] leading-none font-semibold tracking-tight text-info-800 sm:text-5xl">
            <CountUpMoney amount={t.needs_more_info_amount} />
          </p>
          {n > 0 && (
            <p className="mt-2 text-sm text-info-800/80">
              {n === 1 ? '1 deduction has' : `${n} deductions have`} no clear basis yet
            </p>
          )}
        </div>
        {upside !== null && (
          <div className="px-5 py-5 sm:px-6">
            <p className="text-sm text-stone-600">If they can’t justify it, you could get up to about</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-brand-800">
              <CountUpMoney amount={upside} delayMs={250} />
            </p>
            <p className="mt-1 text-xs text-stone-500">{coPayText}</p>
          </div>
        )}
      </>
    )
  } else {
    lead = (
      <div className="bg-fair-50 px-5 py-6 sm:px-6">
        <p className="flex items-center gap-2 text-sm font-semibold text-fair-700">
          <CircleCheck className="size-4" aria-hidden="true" />
          Nothing to challenge
        </p>
        <p className="mt-2 font-display text-2xl leading-snug tracking-tight text-fair-800">
          {report.deduction_findings.length > 0
            ? `All ${report.deduction_findings.length} deductions match your policy.`
            : 'The insurer’s decision matches your policy.'}
        </p>
        <p className="mt-2 text-sm text-fair-800/80">You don’t need to spend time on a complaint.</p>
      </div>
    )
  }

  return (
    <div className="card overflow-hidden shadow-raised">
      {lead}
      {extras.length > 0 && (
        <ul className="space-y-2 border-t border-line px-5 py-4 text-sm sm:px-6">
          {extras.map((e) => (
            <li key={e.key} className="flex items-center gap-2 text-stone-700">
              <e.icon className={cn('size-4 shrink-0', e.className)} aria-hidden="true" />
              <span>{e.text}</span>
            </li>
          ))}
        </ul>
      )}
      {secondary}
    </div>
  )
}

type SegmentKey = 'paid' | 'challengeable' | 'absorb' | 'info' | 'fair' | 'copay'

/** "Where your money went": one stacked bar with a legend that carries every value. */
function MoneyBar({ report }: { report: Report }) {
  const t = report.totals
  const [active, setActive] = useState<SegmentKey | null>(null)
  if (t.claim_rejected || t.claimed <= 0) return null

  const copay = Math.max(0, t.claimed - t.paid - t.total_deducted)
  const fair = Math.max(0, t.total_deducted - t.challengeable_amount - t.needs_more_info_amount - t.ask_hospital_amount)
  const segments: { key: SegmentKey; label: string; amount: number; bar: string }[] = [
    { key: 'paid', label: 'Insurer paid', amount: t.paid, bar: 'bg-brand-700' },
    { key: 'challengeable', label: 'You can challenge', amount: t.challengeable_amount, bar: 'bg-challenge-500' },
    { key: 'absorb', label: 'Ask hospital to waive', amount: t.ask_hospital_amount, bar: 'bg-absorb-500' },
    { key: 'info', label: 'Ask for reasons', amount: t.needs_more_info_amount, bar: 'bg-info-500' },
    { key: 'fair', label: 'Fair deductions', amount: fair, bar: 'bg-fair-500' },
    { key: 'copay', label: 'Your co-pay', amount: copay, bar: 'bg-stone-300' },
  ].filter((s) => s.amount > 0) as { key: SegmentKey; label: string; amount: number; bar: string }[]

  return (
    <figure className="mt-10">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-sm font-semibold text-stone-800">
          Where your <Money amount={t.claimed} /> went
        </span>
      </figcaption>
      <div className="mt-3 flex h-3.5 w-full gap-[2px]" aria-hidden="true">
        {segments.map((s, i) => (
          <span
            key={s.key}
            title={`${s.label}: ${formatINR(s.amount)}`}
            onMouseEnter={() => setActive(s.key)}
            onMouseLeave={() => setActive(null)}
            className={cn(
              'h-full min-w-[3px] transition-opacity duration-200',
              s.bar,
              i === 0 && 'rounded-l-[4px]',
              i === segments.length - 1 && 'rounded-r-[4px]',
              active && active !== s.key && 'opacity-25',
            )}
            style={{ flexGrow: s.amount, flexBasis: 0 }}
          />
        ))}
      </div>
      <ul className="mt-4 flex flex-wrap gap-x-6 gap-y-2.5">
        {segments.map((s) => (
          <li key={s.key}>
            <button
              type="button"
              onMouseEnter={() => setActive(s.key)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(s.key)}
              onBlur={() => setActive(null)}
              className={cn(
                'flex cursor-default items-center gap-2 rounded text-sm transition-opacity',
                active && active !== s.key && 'opacity-40',
              )}
            >
              <span className={cn('size-2.5 rounded-[3px]', s.bar)} aria-hidden="true" />
              <span className="text-stone-600">{s.label}</span>
              <Money amount={s.amount} className="font-semibold text-stone-900" />
            </button>
          </li>
        ))}
      </ul>
    </figure>
  )
}

export function SummaryHeader({ claim, report }: { claim: Claim; report: Report }) {
  const insurer = shortInsurerName(report.policy_wording_name)
  const product = productName(report.policy_wording_name)
  const wordingLabel = insurer && product ? `${product} · ${insurer}` : (report.policy_wording_name ?? 'Standard policy terms')

  return (
    <section id="summary" aria-labelledby="report-headline" className="container-page scroll-mt-32 pt-6 sm:pt-10">
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm text-stone-500">
        <Link to="/claims" className="hover:text-stone-900">
          My claims
        </Link>
        <ChevronRight className="size-3.5" aria-hidden="true" />
        <span className="truncate text-stone-700" aria-current="page">
          {claim.sample_id ? `Sample ${claim.sample_id}` : 'Your claim'}
        </span>
      </nav>

      <div className="mt-6 grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_25rem] lg:gap-12">
        <div className="animate-fade-up">
          <div className="flex flex-wrap gap-2">
            <span
              className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-xs font-medium text-stone-700"
              title={report.policy_wording_name ?? undefined}
            >
              <ScrollText className="size-3.5 shrink-0 text-brand-700" aria-hidden="true" />
              <span className="truncate">Judged against: {wordingLabel}</span>
            </span>
            {report.reviewed_by_ai ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-800">
                <BadgeCheck className="size-3.5" aria-hidden="true" />
                Reviewed by Claude
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-xs font-medium text-stone-600">
                <Cog className="size-3.5 text-stone-500" aria-hidden="true" />
                Checked by rules only · no AI review
              </span>
            )}
          </div>
          <h1
            id="report-headline"
            className="mt-5 font-display text-[2.1rem] leading-[1.1] tracking-tight text-balance text-stone-900 sm:text-[2.9rem]"
          >
            {prettyRupees(report.headline)}
          </h1>
          <p className="mt-4 max-w-2xl text-[17px] leading-relaxed text-stone-600">{prettyRupees(report.summary)}</p>
          <p className="mt-3 text-xs text-stone-500">Report prepared {formatDate(report.generated_at)}</p>
          <ClaimFacts claim={claim} />
        </div>
        <div className="animate-fade-up [animation-delay:120ms]">
          <KeyFigures claim={claim} report={report} />
        </div>
      </div>
      <MoneyBar report={report} />
    </section>
  )
}

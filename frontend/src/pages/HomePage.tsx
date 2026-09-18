import { ArrowRight, FileSearch, FileUp, Info, Send, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router'
import type { Verdict } from '../api/types'
import { SampleClaims } from '../components/SampleClaims'
import { SectionHeading } from '../components/SectionHeading'
import { VerdictChip } from '../components/Verdict'
import { cn } from '../lib/cn'
import { formatINR } from '../lib/format'
import { usePageTitle } from '../lib/usePageTitle'
import { VERDICTS } from '../lib/verdicts'

const HERO_ROWS: { item: string; code: string; amount: number; verdict: Verdict }[] = [
  { item: 'Sutures', code: 'CS01', amount: 3600, verdict: 'challengeable' },
  { item: 'Ligation clips', code: 'CS02', amount: 4200, verdict: 'challengeable' },
  { item: 'Histopathology test', code: 'IN02', amount: 2350, verdict: 'challengeable' },
  { item: 'Admission kit', code: 'MS01', amount: 1200, verdict: 'fair_ask_hospital_to_absorb' },
  { item: 'Examination gloves', code: 'CS04', amount: 1240, verdict: 'fair' },
]

function HeroIllustration() {
  return (
    <div className="relative mx-auto w-full max-w-[34rem] min-w-0 sm:pb-20" aria-hidden="true">
      <div className="absolute -top-3 right-2 left-10 h-44 rotate-[2.5deg] rounded-xl border border-line bg-paper-2" />
      <div className="absolute -top-1 right-6 left-4 h-44 -rotate-[1.2deg] rounded-xl border border-line bg-white/70" />

      <figure className="paper relative overflow-hidden rounded-xl">
        <div className="flex items-start justify-between gap-4 px-5 pt-5 pb-4 sm:px-6">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.1em] text-stone-500 uppercase">Your bill, checked</p>
            <p className="mt-1 font-display text-lg leading-tight tracking-tight text-stone-900">
              Lakeview Multispeciality Hospital
            </p>
          </div>
          <div className="text-right">
            <p className="text-[11px] text-stone-500">Claimed</p>
            <p className="money text-sm font-semibold text-stone-900">{formatINR(139700)}</p>
          </div>
        </div>
        <div className="perforation mx-5 sm:mx-6" />
        <ul className="px-2 py-2 sm:px-3">
          {HERO_ROWS.map((row, i) => (
            <li
              key={row.code}
              className="animate-fade-up relative flex items-center gap-3 rounded-lg px-3 py-2.5"
              style={{ animationDelay: `${150 + i * 90}ms` }}
            >
              <span className={cn('absolute top-2.5 bottom-2.5 left-0 w-[3px] rounded-full', VERDICTS[row.verdict].classes.bar)} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-stone-900">{row.item}</span>
                <span className="font-mono text-[11px] text-stone-400">{row.code}</span>
              </span>
              <span className="money text-sm font-semibold text-stone-800">{formatINR(row.amount)}</span>
              <span className="hidden w-[9.5rem] sm:block">
                <VerdictChip verdict={row.verdict} size="sm" />
              </span>
              <span className={cn('size-2.5 rounded-full sm:hidden', VERDICTS[row.verdict].classes.dot)} />
            </li>
          ))}
        </ul>
        <div className="flex items-end justify-between gap-4 border-t border-line bg-challenge-50/70 px-5 pt-3 pb-4 sm:justify-end sm:px-6 sm:pb-10">
          <span className="text-sm text-stone-600 sm:hidden">
            Deducted <span className="money font-semibold text-stone-800">{formatINR(19840)}</span>
          </span>
          <span className="text-right">
            <span className="hidden text-xs text-stone-500 sm:block">
              of <span className="money font-medium text-stone-700">{formatINR(19840)}</span> deducted
            </span>
            <span className="block text-xs font-medium text-challenge-700">You can challenge</span>
            <span className="money block text-2xl font-semibold tracking-tight text-challenge-700">{formatINR(11600)}</span>
          </span>
        </div>
      </figure>

      <div className="relative mx-3 -mt-3 rounded-xl border border-line bg-white p-4 shadow-raised sm:absolute sm:right-auto sm:bottom-0 sm:-left-8 sm:mx-0 sm:mt-0 sm:max-w-[19rem] lg:-left-12">
        <p className="text-[11px] font-semibold tracking-[0.08em] text-brand-700 uppercase">IRDAI Master Circular, 2024 · para 16.3</p>
        <p className="mt-1.5 font-display text-[15px] leading-snug text-stone-700 italic">
          “No further deductions shall be made from the claim amount in the name of any other exclusions.”
        </p>
      </div>
    </div>
  )
}

const TRUST = [
  { figure: '2024', label: 'IRDAI regulations, checked as they stand today' },
  { figure: '60', label: 'rules, each with its exact quote' },
  { figure: '146', label: 'non-payable items from the policy lists' },
  { figure: '40', label: 'real Ombudsman & court decisions' },
]

const STEPS = [
  {
    Icon: FileUp,
    title: 'Upload',
    text: 'Add your policy schedule, the hospital bill and the insurer’s letter. Clear phone photos are fine.',
  },
  {
    Icon: FileSearch,
    title: 'Check',
    text: 'Every deduction is compared with your own policy wording, IRDAI’s current rules and past decisions.',
  },
  {
    Icon: Send,
    title: 'Act',
    text: 'See what you can challenge and why, then send a complaint letter we draft for you.',
  },
]

export function HomePage() {
  usePageTitle(null)

  return (
    <>
      <section className="container-page grid grid-cols-1 items-center gap-12 pt-10 pb-16 sm:pt-16 lg:grid-cols-[1.08fr_1fr] lg:gap-16 lg:pt-20 lg:pb-24">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1 text-xs font-medium text-stone-600">
            <ShieldCheck className="size-3.5 text-brand-700" aria-hidden="true" />
            For health insurance claims in India
          </p>
          <h1 className="mt-5 font-display text-[2.55rem] leading-[1.05] tracking-tight text-stone-900 sm:text-[3.5rem] lg:text-[3.85rem]">
            Your insurer cut your hospital claim.{' '}
            <span className="text-brand-700">Find out if they were allowed to.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-stone-600">
            ClaimBack reads your policy, hospital bill and the insurer’s letter. It checks every deduction against your
            policy wording, IRDAI’s rules and real Ombudsman decisions, then shows what you can challenge, with the exact
            clause for each point.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link to="/new" className="btn-primary btn-lg">
              Check my claim
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
            <a href="#samples" className="btn-secondary btn-lg">
              Try a sample claim
            </a>
          </div>
          <p className="mt-4 text-sm text-stone-500">Takes about a minute · Plain-language report · Not legal advice</p>
        </div>
        <HeroIllustration />
      </section>

      <section aria-labelledby="trust-heading" className="border-y border-line bg-white/70">
        <div className="container-page py-8">
          <h2 id="trust-heading" className="text-center text-xs font-semibold tracking-[0.12em] text-stone-500 uppercase lg:text-left">
            Every report is checked against
          </h2>
          <ul className="mt-5 grid grid-cols-2 gap-x-6 gap-y-6 lg:grid-cols-4 lg:divide-x lg:divide-line">
            {TRUST.map((t) => (
              <li key={t.figure} className="lg:px-6 lg:first:pl-0">
                <p className="font-display text-[2.1rem] leading-none tracking-tight text-brand-800">{t.figure}</p>
                <p className="mt-2 text-sm leading-snug text-stone-600">{t.label}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="how-heading" className="container-page py-20">
        <SectionHeading id="how-heading" eyebrow="How it works" title="Three steps from “is this right?” to a letter you can send" />
        <ol className="mt-10 grid gap-4 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="card relative p-6">
              <div className="flex items-center justify-between">
                <span className="flex size-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                  <step.Icon className="size-5" aria-hidden="true" />
                </span>
                <span className="font-display text-4xl leading-none text-stone-200" aria-hidden="true">
                  {String(i + 1).padStart(2, '0')}
                </span>
              </div>
              <h3 className="mt-5 text-lg font-semibold text-stone-900">
                <span className="sr-only">Step {i + 1}: </span>
                {step.title}
              </h3>
              <p className="mt-1.5 text-[15px] leading-relaxed text-stone-600">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section id="samples" aria-labelledby="samples-heading" className="container-page scroll-mt-20 pb-6">
        <SectionHeading
          id="samples-heading"
          eyebrow="See it work"
          title="Try a sample claim"
          description="Five common situations, with made-up names. Open one to see a full report in a few seconds, no upload needed."
        />
        <div className="mt-8">
          <SampleClaims />
        </div>
      </section>

      <section className="container-page pt-16">
        <div className="flex gap-4 rounded-xl border border-line bg-paper-2/70 p-5 sm:p-6">
          <Info className="mt-0.5 size-5 shrink-0 text-stone-500" aria-hidden="true" />
          <p className="text-sm leading-relaxed text-stone-600">
            <span className="font-semibold text-stone-800">Information, not legal advice.</span> ClaimBack explains what
            your policy and the regulations say, and links every point to its source so you can check it yourself. For a
            complex or high-value dispute, consider talking to a lawyer or a consumer rights group.
          </p>
        </div>
      </section>
    </>
  )
}

import { ArrowRight, FileUp } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { api, errorMessage } from '../api/client'
import type { SampleSummary } from '../api/types'
import { cn } from '../lib/cn'
import { formatINR, splitTitle } from '../lib/format'
import { useAsync } from '../lib/hooks'
import { ErrorNotice, Skeleton, Spinner } from './States'

/** Short, plain-language card copy for the bundled samples. Falls back to the API's title and summary. */
const SAMPLE_DISPLAY: Record<string, { heading: string; hook: string }> = {
  S1: { heading: 'Gallbladder surgery', hook: "14 items cut as ‘non-payable’. Four of them aren’t on any list." },
  S2: { heading: 'Pneumonia admission', hook: 'A room-rent cut was stretched to medicines and tests the policy protects.' },
  S3: { heading: 'Heart attack, claim rejected', hook: 'Rejected for ‘non-disclosure’ after 84 months of cover, well past the 60-month limit.' },
  S4: { heading: 'ACL knee surgery', hook: 'The surgeon’s fee was halved, with no local rates shown to justify it.' },
  S5: { heading: 'Dengue admission', hook: 'Every deduction here is genuine, and ClaimBack says so plainly.' },
}

function SampleCard({
  sample,
  pending,
  disabled,
  onOpen,
}: {
  sample: SampleSummary
  pending: boolean
  disabled: boolean
  onOpen: () => void
}) {
  const display = SAMPLE_DISPLAY[sample.id.toUpperCase()]
  const heading = display?.heading ?? splitTitle(sample.title).heading
  const hook = display?.hook ?? sample.summary
  const rejected = sample.letter_type === 'repudiation' || sample.paid <= 0
  const paidPct = sample.claimed > 0 ? Math.max(0, Math.min(100, (sample.paid / sample.claimed) * 100)) : 0
  const cut = Math.max(0, sample.claimed - sample.paid)

  return (
    <button
      type="button"
      onClick={onOpen}
      disabled={disabled}
      aria-busy={pending}
      className={cn(
        'group card relative flex h-full flex-col p-5 text-left transition-[box-shadow,border-color,transform] duration-200',
        'hover:-translate-y-0.5 hover:border-line-strong hover:shadow-raised focus-visible:-translate-y-0.5 motion-reduce:hover:translate-y-0',
        'disabled:cursor-wait disabled:hover:translate-y-0',
        disabled && !pending && 'opacity-60',
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-xs font-medium text-stone-500">Sample {sample.id}</span>
        <span
          className={cn(
            'rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset',
            rejected ? 'bg-challenge-50 text-challenge-700 ring-challenge-200' : 'bg-paper-2 text-stone-600 ring-line',
          )}
        >
          {rejected ? 'Claim rejected' : 'Partly paid'}
        </span>
      </div>
      <h3 className="mt-3 font-display text-[1.35rem] leading-snug tracking-tight text-stone-900">{heading}</h3>
      <p className="mt-1.5 line-clamp-3 text-sm leading-relaxed text-stone-600">{hook}</p>

      <div className="mt-auto pt-6">
        <div className="flex items-end justify-between gap-3 text-xs text-stone-500">
          <span>
            Claimed
            <span className="money mt-0.5 block text-[15px] font-semibold text-stone-900">{formatINR(sample.claimed)}</span>
          </span>
          <span className="text-right">
            Insurer paid
            <span className="money mt-0.5 block text-[15px] font-semibold text-stone-900">{formatINR(sample.paid)}</span>
          </span>
        </div>
        <div
          className="mt-2.5 flex h-2 gap-[2px] overflow-hidden rounded-full"
          role="img"
          aria-label={`Insurer paid ${formatINR(sample.paid)} of ${formatINR(sample.claimed)}; ${formatINR(cut)} was not paid`}
        >
          {paidPct > 0 && <span className="h-full rounded-l-full bg-brand-700" style={{ width: `${paidPct}%` }} />}
          {cut > 0 && <span className={cn('h-full flex-1 bg-challenge-500/80', paidPct === 0 && 'rounded-l-full', 'rounded-r-full')} />}
        </div>
        <p className="mt-1.5 text-xs text-stone-500">
          <span className="money font-medium text-stone-700">{formatINR(cut)}</span> not paid
        </p>
        <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700">
          {pending ? (
            <Spinner label="Opening…" />
          ) : (
            <>
              See the report
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
            </>
          )}
        </span>
      </div>
    </button>
  )
}

export function SampleClaims() {
  const navigate = useNavigate()
  const { data: samples, error, loading, reload } = useAsync(() => api.samples(), [])
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [openError, setOpenError] = useState<string | null>(null)

  const open = async (sampleId: string) => {
    setPendingId(sampleId)
    setOpenError(null)
    try {
      const claim = await api.createSampleClaim(sampleId)
      navigate(`/claims/${encodeURIComponent(claim.id)}`)
    } catch (err) {
      setOpenError(errorMessage(err))
      setPendingId(null)
    }
  }

  if (error) {
    return (
      <ErrorNotice
        title="We couldn’t load the sample claims"
        action={
          <button type="button" className="btn-secondary btn-sm" onClick={reload}>
            Try again
          </button>
        }
      >
        {errorMessage(error)}
      </ErrorNotice>
    )
  }

  return (
    <div>
      {openError && (
        <ErrorNotice title="That sample didn’t open" className="mb-5">
          {openError}
        </ErrorNotice>
      )}
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy={loading}>
        {loading &&
          Array.from({ length: 5 }).map((_, i) => (
            <li key={i} className="card h-[18.5rem] p-5">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="mt-4 h-6 w-2/3" />
              <Skeleton className="mt-3 h-4 w-full" />
              <Skeleton className="mt-2 h-4 w-4/5" />
              <Skeleton className="mt-16 h-2 w-full" />
            </li>
          ))}
        {samples?.map((sample) => (
          <li key={sample.id}>
            <SampleCard
              sample={sample}
              pending={pendingId === sample.id}
              disabled={pendingId !== null}
              onOpen={() => void open(sample.id)}
            />
          </li>
        ))}
        {samples && (
          <li>
            <Link
              to="/new"
              className="group flex h-full min-h-[14rem] flex-col justify-between rounded-xl border border-dashed border-line-strong p-5 transition-colors hover:border-brand-400 hover:bg-white"
            >
              <span className="flex size-10 items-center justify-center rounded-full bg-brand-50 text-brand-700">
                <FileUp className="size-5" aria-hidden="true" />
              </span>
              <span>
                <span className="block font-display text-[1.35rem] leading-snug tracking-tight text-stone-900">
                  Have your own claim?
                </span>
                <span className="mt-1.5 block text-sm leading-relaxed text-stone-600">
                  Add your policy schedule, hospital bill and the insurer’s letter.
                </span>
                <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700">
                  Check my claim
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </span>
              </span>
            </Link>
          </li>
        )}
      </ul>
    </div>
  )
}

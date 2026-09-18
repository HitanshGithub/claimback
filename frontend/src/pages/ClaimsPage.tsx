import { ArrowRight, CircleAlert, CircleCheck, CircleHelp, FileUp, FolderOpen, Trash2, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { api, errorMessage } from '../api/client'
import type { ClaimSummary } from '../api/types'
import { ErrorNotice, Skeleton, Spinner } from '../components/States'
import { cn } from '../lib/cn'
import { formatDateTime, splitTitle } from '../lib/format'
import { useAsync } from '../lib/hooks'
import { usePageTitle } from '../lib/usePageTitle'
import { Money } from '../components/Money'

function Outcome({ claim }: { claim: ClaimSummary }) {
  if (claim.status === 'processing') {
    return <Spinner className="text-sm font-medium text-brand-700" label="Checking…" />
  }
  if (claim.status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm font-medium text-challenge-700">
        <TriangleAlert className="size-4" aria-hidden="true" />
        Couldn’t finish
      </span>
    )
  }
  const t = claim.totals
  if (!t) return <span className="text-sm text-stone-500">Report ready</span>
  if (t.claim_rejected) {
    return (
      <span className="sm:text-right">
        <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-challenge-700">
          <CircleAlert className="size-4" aria-hidden="true" />
          {t.challengeable_amount > 0 ? 'Rejected, can be challenged' : 'Claim rejected'}
        </span>
        <span className="block text-xs text-stone-500">
          Claimed <Money amount={t.claimed} />
        </span>
      </span>
    )
  }
  if (t.challengeable_amount > 0) {
    return (
      <span className="sm:text-right">
        <span className="block text-xs text-stone-500">You can challenge</span>
        <Money amount={t.challengeable_amount} className="text-lg font-semibold text-challenge-700" />
      </span>
    )
  }
  if (t.needs_more_info_amount > 0) {
    return (
      <span className="sm:text-right">
        <span className="inline-flex items-center gap-1 text-xs text-info-700">
          <CircleHelp className="size-3.5" aria-hidden="true" />
          Ask for reasons
        </span>
        <Money amount={t.needs_more_info_amount} className="block text-lg font-semibold text-info-800" />
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-sm font-medium text-fair-700">
      <CircleCheck className="size-4" aria-hidden="true" />
      Nothing to challenge
    </span>
  )
}

function ClaimRow({ claim, onDeleted }: { claim: ClaimSummary; onDeleted: (id: string) => void }) {
  const [confirming, setConfirming] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { heading, rest } = splitTitle(claim.title)

  const remove = async () => {
    setDeleting(true)
    setError(null)
    try {
      await api.deleteClaim(claim.id)
      onDeleted(claim.id)
    } catch (err) {
      setError(errorMessage(err))
      setDeleting(false)
    }
  }

  return (
    <li className="card relative transition-shadow hover:shadow-raised">
      <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:gap-6 sm:p-6">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500">
            <span
              className={cn(
                'rounded-full px-2 py-0.5 font-semibold ring-1 ring-inset',
                claim.source === 'sample' ? 'bg-paper-2 text-stone-600 ring-line' : 'bg-brand-50 text-brand-800 ring-brand-200',
              )}
            >
              {claim.source === 'sample' ? `Sample ${claim.sample_id ?? ''}`.trim() : 'Uploaded'}
            </span>
            <span>{formatDateTime(claim.created_at)}</span>
          </div>
          <h2 className="mt-2 text-[17px] leading-snug font-semibold text-stone-900">
            <Link
              to={`/claims/${encodeURIComponent(claim.id)}`}
              className="after:absolute after:inset-0 after:rounded-xl after:content-[''] hover:text-brand-800 focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:outline-offset-2 focus-visible:after:outline-brand-600"
            >
              {heading}
            </Link>
          </h2>
          {rest && <p className="mt-0.5 truncate text-sm text-stone-500">{rest}</p>}
        </div>

        <div className="flex items-center justify-between gap-4 sm:justify-end">
          <Outcome claim={claim} />
          <div className="relative z-10 flex items-center gap-1">
            {confirming ? (
              <span className="flex items-center gap-1.5" role="group" aria-label="Confirm delete">
                <button type="button" className="btn-ghost btn-sm" onClick={() => setConfirming(false)} disabled={deleting}>
                  Keep
                </button>
                <button
                  type="button"
                  className="btn btn-sm bg-challenge-600 text-white hover:bg-challenge-700"
                  onClick={() => void remove()}
                  disabled={deleting}
                >
                  {deleting ? <Spinner label="Deleting…" /> : 'Delete'}
                </button>
              </span>
            ) : (
              <button
                type="button"
                onClick={() => setConfirming(true)}
                className="rounded-lg p-2 text-stone-400 transition-colors hover:bg-challenge-50 hover:text-challenge-700"
                aria-label={`Delete ${heading}`}
              >
                <Trash2 className="size-4" aria-hidden="true" />
              </button>
            )}
            <ArrowRight className="hidden size-4 text-stone-300 sm:block" aria-hidden="true" />
          </div>
        </div>
      </div>
      {error && <p className="px-6 pb-4 text-sm font-medium text-challenge-700">{error}</p>}
    </li>
  )
}

export function ClaimsPage() {
  usePageTitle('My claims')
  const { data, error, loading, reload } = useAsync(() => api.listClaims(), [])
  const [removed, setRemoved] = useState<string[]>([])
  const claims = data?.filter((c) => !removed.includes(c.id))

  return (
    <div className="container-page pt-10 sm:pt-14">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">My claims</p>
          <h1 className="mt-3 font-display text-[2.3rem] leading-tight tracking-tight text-stone-900 sm:text-5xl">
            Your checked claims
          </h1>
          <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-stone-600">
            Claims you’ve checked in this browser, newest first.
          </p>
        </div>
        <Link to="/new" className="btn-primary">
          <FileUp className="size-4" aria-hidden="true" />
          Check a new claim
        </Link>
      </div>

      <div className="mt-10">
        {error ? (
          <ErrorNotice
            title="We couldn’t load your claims"
            action={
              <button type="button" className="btn-secondary btn-sm" onClick={reload}>
                Try again
              </button>
            }
          >
            {errorMessage(error)}
          </ErrorNotice>
        ) : loading && !data ? (
          <ul className="space-y-3" aria-busy="true">
            {[0, 1, 2].map((i) => (
              <li key={i} className="card p-6">
                <Skeleton className="h-3 w-40" />
                <Skeleton className="mt-3 h-5 w-64" />
              </li>
            ))}
          </ul>
        ) : claims && claims.length > 0 ? (
          <ul className="space-y-3">
            {claims.map((claim) => (
              <ClaimRow key={claim.id} claim={claim} onDeleted={(id) => setRemoved((r) => [...r, id])} />
            ))}
          </ul>
        ) : (
          <div className="rounded-2xl border border-dashed border-line-strong px-6 py-16 text-center">
            <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-white text-stone-500 ring-1 ring-line">
              <FolderOpen className="size-6" aria-hidden="true" />
            </span>
            <h2 className="mt-5 font-display text-2xl tracking-tight text-stone-900">No claims yet</h2>
            <p className="mx-auto mt-2 max-w-sm text-[15px] text-stone-600">
              Check your own claim, or open a sample to see what a report looks like.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Link to="/#samples" className="btn-secondary">
                Try a sample claim
              </Link>
              <Link to="/new" className="btn-primary">
                Check my claim
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

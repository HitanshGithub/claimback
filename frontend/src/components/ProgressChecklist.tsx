import { ArrowLeft, Check, Minus, RotateCcw, TriangleAlert, X } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { api, errorMessage } from '../api/client'
import type { Claim, ProgressStep } from '../api/types'
import { cn } from '../lib/cn'
import { Spinner } from './States'

function StepIcon({ status }: { status: ProgressStep['status'] }) {
  switch (status) {
    case 'done':
      return (
        <span className="animate-pop flex size-8 items-center justify-center rounded-full bg-brand-700 text-white shadow-sm">
          <Check className="size-4" strokeWidth={3} aria-hidden="true" />
        </span>
      )
    case 'running':
      return (
        <span className="relative flex size-8 items-center justify-center">
          <svg viewBox="0 0 32 32" className="absolute inset-0 size-8 animate-spin-slow" aria-hidden="true">
            <circle cx="16" cy="16" r="14" fill="none" strokeWidth="2.5" className="stroke-brand-100" />
            <circle
              cx="16"
              cy="16"
              r="14"
              fill="none"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeDasharray="28 88"
              className="stroke-brand-600"
            />
          </svg>
          <span className="size-2 animate-pulse rounded-full bg-brand-600" aria-hidden="true" />
        </span>
      )
    case 'skipped':
      return (
        <span className="animate-pop flex size-8 items-center justify-center rounded-full border border-line-strong bg-paper-2 text-stone-400">
          <Minus className="size-4" strokeWidth={2.5} aria-hidden="true" />
        </span>
      )
    case 'failed':
      return (
        <span className="animate-pop flex size-8 items-center justify-center rounded-full bg-challenge-600 text-white">
          <X className="size-4" strokeWidth={3} aria-hidden="true" />
        </span>
      )
    default:
      return <span className="block size-8 rounded-full border-2 border-dashed border-line-strong bg-white" />
  }
}

const STATUS_TEXT: Record<ProgressStep['status'], string> = {
  pending: 'Waiting',
  running: 'In progress',
  done: 'Done',
  skipped: 'Skipped',
  failed: 'Failed',
}

export function ProgressList({ steps }: { steps: ProgressStep[] }) {
  return (
    <ol className="relative">
      {steps.map((step, i) => {
        const last = i === steps.length - 1
        const complete = step.status === 'done' || step.status === 'skipped'
        return (
          <li key={step.name} className={cn('relative flex gap-4', !last && 'pb-6')}>
            {!last && (
              <span
                aria-hidden="true"
                className={cn(
                  'absolute top-9 bottom-1 left-[15.5px] w-px transition-colors duration-500',
                  complete ? 'bg-brand-300' : 'bg-line',
                )}
              />
            )}
            <span className="relative z-10 shrink-0">
              <StepIcon status={step.status} />
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <p
                className={cn(
                  'text-[15px] leading-snug font-medium transition-colors duration-300',
                  step.status === 'pending' && 'text-stone-400',
                  step.status === 'running' && 'text-stone-900',
                  step.status === 'done' && 'text-stone-800',
                  step.status === 'skipped' && 'text-stone-500',
                  step.status === 'failed' && 'text-challenge-700',
                )}
              >
                {step.label}
                <span className="sr-only"> ({STATUS_TEXT[step.status]})</span>
              </p>
              {step.status === 'running' && !step.detail && (
                <p className="mt-1 text-[13px] text-brand-700">Working on it…</p>
              )}
              {step.detail && step.status !== 'pending' && (
                <p
                  className={cn(
                    'animate-fade-up mt-1 text-[13px] leading-snug',
                    step.status === 'failed' ? 'text-challenge-700' : 'text-stone-500',
                  )}
                >
                  {step.status === 'skipped' && <span className="font-medium text-stone-600">Skipped · </span>}
                  {step.detail}
                </p>
              )}
              {step.status === 'skipped' && !step.detail && <p className="mt-1 text-[13px] text-stone-500">Skipped</p>}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export function ProcessingView({ claim }: { claim: Claim }) {
  const steps = claim.progress
  const finished = steps.filter((s) => s.status === 'done' || s.status === 'skipped').length
  const current = steps.find((s) => s.status === 'running')
  const pct = steps.length ? Math.round((finished / steps.length) * 100) : 0

  return (
    <div className="container-page py-12 sm:py-20">
      <div className="mx-auto max-w-xl">
        <div className="text-center">
          <p className="eyebrow">Checking your claim</p>
          <h1 className="mt-3 font-display text-[2.2rem] leading-tight tracking-tight text-balance text-stone-900 sm:text-[2.75rem]">
            We’re going through it line by line
          </h1>
          <p className="mx-auto mt-3 max-w-md text-[15px] leading-relaxed text-balance text-stone-600">{claim.title}</p>
        </div>

        <div className="card mt-10 p-6 sm:p-8">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-stone-700">
              {finished} of {steps.length} checks done
            </span>
            <span className="money text-stone-500">{pct}%</span>
          </div>
          <div
            className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-paper-3"
            role="progressbar"
            aria-label="Progress"
            aria-valuemin={0}
            aria-valuemax={steps.length}
            aria-valuenow={finished}
          >
            <div
              className="h-full rounded-full bg-brand-600 transition-[width] duration-500 ease-out"
              style={{ width: `${Math.max(4, pct)}%` }}
            />
          </div>
          <div className="sr-only" aria-live="polite">
            {current ? `Now: ${current.label}` : finished === steps.length ? 'All checks done. Preparing your report.' : ''}
          </div>
          <div className="mt-8">
            <ProgressList steps={steps} />
          </div>
        </div>
        <p className="mt-6 text-center text-sm text-stone-500">
          This usually takes under a minute. Keep this page open and your report will appear here.
        </p>
      </div>
    </div>
  )
}

export function FailedView({ claim, onRestarted }: { claim: Claim; onRestarted: () => void }) {
  const navigate = useNavigate()
  const [retrying, setRetrying] = useState(false)
  const [retryError, setRetryError] = useState<string | null>(null)

  const retrySample = async () => {
    if (!claim.sample_id) return
    setRetrying(true)
    setRetryError(null)
    try {
      const next = await api.createSampleClaim(claim.sample_id)
      if (next.id === claim.id) {
        setRetrying(false)
        onRestarted()
      } else {
        navigate(`/claims/${encodeURIComponent(next.id)}`)
      }
    } catch (err) {
      setRetryError(errorMessage(err))
      setRetrying(false)
    }
  }

  return (
    <div className="container-page py-12 sm:py-20">
      <div className="card mx-auto max-w-xl p-6 sm:p-10">
        <div className="text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-challenge-50 text-challenge-600 ring-1 ring-challenge-100">
            <TriangleAlert className="size-6" aria-hidden="true" />
          </span>
          <h1 className="mt-5 font-display text-3xl tracking-tight text-stone-900">We couldn’t finish checking this claim</h1>
          <p className="mx-auto mt-3 max-w-md text-[15px] leading-relaxed text-stone-600" role="alert">
            {claim.error ?? 'Something went wrong while we were reading your documents.'}
          </p>
        </div>

        {claim.progress.length > 0 && (
          <div className="mt-8 rounded-xl border border-line bg-paper/60 p-5">
            <ProgressList steps={claim.progress} />
          </div>
        )}

        {retryError && <p className="mt-4 text-center text-sm font-medium text-challenge-700">{retryError}</p>}

        <div className="mt-8 flex flex-col-reverse justify-center gap-3 sm:flex-row">
          <Link to="/" className="btn-secondary">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to home
          </Link>
          {claim.source === 'sample' && claim.sample_id ? (
            <button type="button" className="btn-primary" onClick={() => void retrySample()} disabled={retrying}>
              {retrying ? <Spinner label="Starting again…" /> : (
                <>
                  <RotateCcw className="size-4" aria-hidden="true" />
                  Try again
                </>
              )}
            </button>
          ) : (
            <Link to="/new" className="btn-primary">
              <RotateCcw className="size-4" aria-hidden="true" />
              Upload the documents again
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}

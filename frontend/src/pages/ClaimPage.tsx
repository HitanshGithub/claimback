import { ArrowLeft, SearchX } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, errorMessage } from '../api/client'
import { FailedView, ProcessingView } from '../components/ProgressChecklist'
import { ReportView } from '../components/report/ReportView'
import { ErrorNotice, Skeleton } from '../components/States'
import { useClaim } from '../lib/useClaim'
import { usePageTitle } from '../lib/usePageTitle'
import { splitTitle } from '../lib/format'

function LoadingReport() {
  return (
    <div className="container-page pt-10" aria-busy="true" aria-label="Loading your report">
      <Skeleton className="h-4 w-40" />
      <div className="mt-8 grid gap-10 lg:grid-cols-[minmax(0,1fr)_25rem]">
        <div>
          <Skeleton className="h-6 w-64" />
          <Skeleton className="mt-6 h-12 w-full" />
          <Skeleton className="mt-3 h-12 w-3/4" />
          <Skeleton className="mt-6 h-5 w-full" />
          <Skeleton className="mt-2 h-5 w-5/6" />
        </div>
        <Skeleton className="h-72 w-full rounded-xl" />
      </div>
    </div>
  )
}

export function ClaimPage() {
  const { id = '' } = useParams()
  const { claim, error, setClaim, reload } = useClaim(id)
  const previousStatus = useRef<string | null>(null)

  usePageTitle(
    claim?.status === 'complete'
      ? `Report: ${splitTitle(claim.title).heading}`
      : claim?.status === 'processing'
        ? 'Checking your claim'
        : claim?.status === 'failed'
          ? 'Check failed'
          : 'Your claim',
  )

  // When processing finishes, start the report at the top.
  useEffect(() => {
    if (!claim) return
    if (previousStatus.current === 'processing' && claim.status !== 'processing') {
      window.scrollTo({ top: 0 })
    }
    previousStatus.current = claim.status
  }, [claim])

  if (!claim) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <div className="container-page py-24 text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-paper-2 text-stone-500 ring-1 ring-line">
            <SearchX className="size-6" aria-hidden="true" />
          </span>
          <h1 className="mt-5 font-display text-4xl tracking-tight text-stone-900">We couldn’t find that claim</h1>
          <p className="mx-auto mt-3 max-w-md text-stone-600">
            It may have been deleted, or it was checked in a different browser.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/claims" className="btn-secondary">
              <ArrowLeft className="size-4" aria-hidden="true" />
              My claims
            </Link>
            <Link to="/#samples" className="btn-primary">
              Try a sample claim
            </Link>
          </div>
        </div>
      )
    }
    if (error) {
      return (
        <div className="container-page py-16">
          <ErrorNotice
            title="We couldn’t load this claim"
            action={
              <button type="button" className="btn-secondary btn-sm" onClick={reload}>
                Try again
              </button>
            }
          >
            {errorMessage(error)}
          </ErrorNotice>
        </div>
      )
    }
    return <LoadingReport />
  }

  if (claim.status === 'processing') return <ProcessingView claim={claim} />
  if (claim.status === 'failed') return <FailedView claim={claim} onRestarted={reload} />
  if (!claim.report) {
    return <FailedView claim={{ ...claim, error: claim.error ?? 'The report for this claim is missing.' }} onRestarted={reload} />
  }

  return (
    <div className="animate-fade-up">
      <ReportView
        claim={claim}
        report={claim.report}
        onLetterSaved={(letter) =>
          setClaim((prev) => (prev ? { ...prev, letters: { ...prev.letters, [letter.kind]: letter } } : prev))
        }
      />
    </div>
  )
}

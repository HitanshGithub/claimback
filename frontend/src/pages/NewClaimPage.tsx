import { ArrowRight, FileText, Hospital, Lock, Mail, PlugZap, ScrollText } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { api, ApiError, errorMessage } from '../api/client'
import { Dropzone } from '../components/Dropzone'
import { ErrorNotice, Spinner } from '../components/States'
import { cn } from '../lib/cn'
import { useAsync } from '../lib/hooks'
import { usePageTitle } from '../lib/usePageTitle'

type Slot = 'hospital_bill' | 'insurer_letter' | 'policy_schedule' | 'discharge_summary'

export function NewClaimPage() {
  usePageTitle('Check my claim')
  const navigate = useNavigate()
  const health = useAsync(() => api.health(), [])
  const wordings = useAsync(() => api.wordings(), [])

  const [files, setFiles] = useState<Record<Slot, File | null>>({
    hospital_bill: null,
    insurer_letter: null,
    policy_schedule: null,
    discharge_summary: null,
  })
  const [wordingId, setWordingId] = useState('')
  const [consent, setConsent] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [triedSubmit, setTriedSubmit] = useState(false)

  const offline = health.data?.llm === 'offline'
  const requiredReady = Boolean(files.hospital_bill && files.insurer_letter && files.policy_schedule)
  const missingCount = [files.hospital_bill, files.insurer_letter, files.policy_schedule].filter((f) => !f).length
  const canSubmit = requiredReady && consent && !offline && !submitting

  const setFile = (slot: Slot) => (file: File | null) => setFiles((prev) => ({ ...prev, [slot]: file }))

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setTriedSubmit(true)
    if (!canSubmit || !files.hospital_bill || !files.insurer_letter || !files.policy_schedule) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const claim = await api.createClaim({
        hospital_bill: files.hospital_bill,
        insurer_letter: files.insurer_letter,
        policy_schedule: files.policy_schedule,
        discharge_summary: files.discharge_summary,
        policy_wording_id: wordingId || null,
      })
      navigate(`/claims/${encodeURIComponent(claim.id)}`)
    } catch (err) {
      setSubmitError(
        err instanceof ApiError && err.status === 503
          ? `${err.message} You can still try a sample claim to see how ClaimBack works.`
          : errorMessage(err),
      )
      setSubmitting(false)
    }
  }

  return (
    <div className="container-page pt-10 pb-4 sm:pt-14">
      <div className="max-w-2xl">
        <p className="eyebrow">Check my claim</p>
        <h1 className="mt-3 font-display text-[2.3rem] leading-[1.08] tracking-tight text-stone-900 sm:text-5xl">
          Add your documents
        </h1>
        <p className="mt-4 text-lg leading-relaxed text-stone-600">
          We need three documents to check your claim. Clear phone photos work too.
        </p>
      </div>

      {offline && (
        <div
          role="status"
          className="mt-8 flex flex-col gap-4 rounded-xl border border-brand-200 bg-brand-50 p-5 sm:flex-row sm:items-center sm:p-6"
        >
          <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-white text-brand-700 ring-1 ring-brand-100">
            <PlugZap className="size-5" aria-hidden="true" />
          </span>
          <div className="flex-1">
            <p className="font-semibold text-brand-900">Checking your own documents isn’t switched on here</p>
            <p className="mt-1 text-sm leading-relaxed text-brand-900/80">
              Reading your documents needs Claude on Amazon Bedrock, which isn’t switched on in this local build. You can
              still see exactly how ClaimBack works with a sample claim.
            </p>
          </div>
          <Link to="/#samples" className="btn-primary shrink-0">
            Try a sample claim
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <form onSubmit={onSubmit} noValidate className="card p-5 sm:p-8" aria-describedby={offline ? 'offline-note' : undefined}>
          <fieldset disabled={submitting}>
            <legend className="text-lg font-semibold text-stone-900">Your documents</legend>
            <p className="mt-1 text-sm text-stone-500">The first three are required.</p>

            <div className="mt-6 grid gap-6 md:grid-cols-2">
              <Dropzone
                label="Hospital bill"
                hint="The final itemised bill, with every line and amount."
                icon={<Hospital className="size-5" aria-hidden="true" />}
                required
                file={files.hospital_bill}
                onChange={setFile('hospital_bill')}
              />
              <Dropzone
                label="Insurer’s letter"
                hint="The settlement or rejection letter listing what was cut and why."
                icon={<Mail className="size-5" aria-hidden="true" />}
                required
                file={files.insurer_letter}
                onChange={setFile('insurer_letter')}
              />
              <Dropzone
                label="Policy schedule"
                hint="The page with your policy number, sum insured and policy dates."
                icon={<ScrollText className="size-5" aria-hidden="true" />}
                required
                file={files.policy_schedule}
                onChange={setFile('policy_schedule')}
              />
              <Dropzone
                label="Discharge summary"
                hint="Helps us understand the treatment. Add it if you have it."
                icon={<FileText className="size-5" aria-hidden="true" />}
                file={files.discharge_summary}
                onChange={setFile('discharge_summary')}
              />
            </div>

            <div className="mt-8 border-t border-line pt-7">
              <label htmlFor="wording" className="text-sm font-semibold text-stone-900">
                Which policy wording is yours?
              </label>
              <p id="wording-hint" className="mt-1 text-[13px] text-stone-500">
                The product name is on your policy schedule. If you’re not sure, choose “Not listed”.
              </p>
              <div className="relative mt-2.5">
                <select
                  id="wording"
                  value={wordingId}
                  onChange={(e) => setWordingId(e.target.value)}
                  aria-describedby="wording-hint"
                  className="w-full appearance-none rounded-lg border border-line-strong bg-white py-2.5 pr-10 pl-3.5 text-[15px] text-stone-900 shadow-card transition-colors hover:border-stone-400 focus:border-brand-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600/30"
                >
                  <option value="">Not listed / I’m not sure</option>
                  {wordings.data?.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.insurer.replace(/ (Company|Co\.) Limited$| Co\.? Ltd\.?$/i, '')} · Arogya Sanjeevani (UIN {w.uin})
                    </option>
                  ))}
                </select>
                <svg
                  aria-hidden="true"
                  viewBox="0 0 20 20"
                  className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-stone-500"
                >
                  <path d="M5 7.5l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              {wordings.error ? (
                <p className="mt-2 text-[13px] text-stone-500">We couldn’t load the list of wordings. You can continue without choosing one.</p>
              ) : null}
            </div>

            <div className="mt-7 flex gap-3 rounded-xl bg-paper-2/70 p-4">
              <input
                id="consent"
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5 size-[18px] shrink-0 cursor-pointer rounded accent-brand-700"
                aria-describedby={triedSubmit && !consent ? 'consent-error' : undefined}
              />
              <label htmlFor="consent" className="cursor-pointer text-sm leading-relaxed text-stone-700">
                I agree to ClaimBack reading these documents to check my claim. I understand the report is information,
                not legal advice.
              </label>
            </div>
            {triedSubmit && !consent && (
              <p id="consent-error" className="mt-2 text-[13px] font-medium text-challenge-700">
                Please tick the box to continue.
              </p>
            )}
          </fieldset>

          {submitError && (
            <ErrorNotice title="We couldn’t start checking your claim" className="mt-6">
              {submitError}
            </ErrorNotice>
          )}

          <div className="mt-7 flex flex-col-reverse gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p id="offline-note" className="text-[13px] text-stone-500">
              {offline
                ? 'Uploads are switched off in this build.'
                : !requiredReady
                  ? `Add ${missingCount} more required ${missingCount === 1 ? 'document' : 'documents'} to continue.`
                  : !consent
                    ? 'Tick the box above to continue.'
                    : 'Ready when you are.'}
            </p>
            <button
              type="submit"
              className={cn('btn-primary btn-lg', !canSubmit && 'opacity-50')}
              aria-disabled={!canSubmit}
              disabled={offline || submitting}
            >
              {submitting ? <Spinner label="Uploading…" /> : 'Check my claim'}
              {!submitting && <ArrowRight className="size-4" aria-hidden="true" />}
            </button>
          </div>
        </form>

        <aside className="space-y-4 lg:pt-1">
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-stone-900">What we check</h2>
            <ul className="mt-3 space-y-2.5 text-sm leading-relaxed text-stone-600">
              <li>Each deduction against your policy’s lists of non-payable items</li>
              <li>Room rent limits, proportionate deductions and co-pay maths</li>
              <li>Waiting periods, the 5-year moratorium and claim deadlines</li>
              <li>How Ombudsmen and courts decided similar cases</li>
            </ul>
          </div>
          <div className="rounded-xl border border-line p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-stone-900">
              <Lock className="size-4 text-stone-500" aria-hidden="true" />
              Your documents
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-stone-600">
              Your files are kept with this claim so you can come back to the report. Claims are linked to this browser,
              and you can delete one at any time from{' '}
              <Link to="/claims" className="link">
                My claims
              </Link>
              .
            </p>
          </div>
        </aside>
      </div>
    </div>
  )
}

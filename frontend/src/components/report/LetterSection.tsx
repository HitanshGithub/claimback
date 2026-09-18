import { Check, Copy, Download, FileSignature, Landmark, Printer, RotateCcw, Send, TriangleAlert } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router'
import { api, errorMessage } from '../../api/client'
import type { Claim, Letter, LetterKind } from '../../api/types'
import { cn } from '../../lib/cn'
import { SectionHeading } from '../SectionHeading'
import { ErrorNotice, Skeleton, Spinner } from '../States'

const KIND_META: Record<LetterKind, { action: string; open: string; title: string; description: string; Icon: typeof Send }> = {
  grievance: {
    action: 'Draft my complaint letter',
    open: 'Open my complaint letter',
    title: 'Complaint to your insurer',
    description: 'Start here. The insurer must reply within 14 days.',
    Icon: Send,
  },
  ombudsman: {
    action: 'Draft Ombudsman complaint',
    open: 'Open my Ombudsman complaint',
    title: 'Complaint to the Ombudsman',
    description: 'Use this if the insurer says no, or doesn’t reply within 30 days.',
    Icon: Landmark,
  },
}

function letterText(letter: Letter): string {
  if (/^\s*subject\s*:/im.test(letter.body)) return letter.body
  return `To: ${letter.to}\nSubject: ${letter.subject}\n\n${letter.body}`
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    const area = document.createElement('textarea')
    area.value = text
    area.setAttribute('readonly', '')
    area.style.position = 'fixed'
    area.style.opacity = '0'
    document.body.appendChild(area)
    area.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(area)
    return ok
  }
}

function LetterEditor({
  claim,
  original,
  draft,
  onChange,
}: {
  claim: Claim
  original: Letter
  draft: Letter
  onChange: (letter: Letter) => void
}) {
  const bodyRef = useRef<HTMLTextAreaElement>(null)
  const [copied, setCopied] = useState(false)
  const edited = draft.body !== original.body || draft.subject !== original.subject || draft.to !== original.to
  const placeholders = (draft.body.match(/\[[^\]\n]{2,80}\]/g) ?? []).length
  const meta = KIND_META[draft.kind]

  useLayoutEffect(() => {
    const el = bodyRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight + 2}px`
  }, [draft.body])

  useEffect(() => {
    if (!copied) return
    const t = window.setTimeout(() => setCopied(false), 2000)
    return () => window.clearTimeout(t)
  }, [copied])

  const download = () => {
    const blob = new Blob([letterText(draft)], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const ref = claim.claim_input?.decision.claim_number ?? claim.id
    a.href = url
    a.download = `claimback-${draft.kind}-${ref}.txt`.replace(/[^\w.-]+/g, '-')
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const print = () => {
    const done = () => {
      document.body.classList.remove('printing-letter')
      window.removeEventListener('afterprint', done)
    }
    document.body.classList.add('printing-letter')
    window.addEventListener('afterprint', done)
    window.print()
    window.setTimeout(done, 1000)
  }

  const inputClass =
    'block w-full resize-none rounded-lg border border-transparent bg-transparent px-2 py-1.5 text-[15px] leading-6 text-stone-900 [field-sizing:content] transition-colors hover:border-line focus:border-brand-600 focus:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600/25'

  return (
    <div className="animate-fade-up mt-6">
      <div className="paper overflow-hidden rounded-xl">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-paper/70 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <FileSignature className="size-4 shrink-0 text-brand-700" aria-hidden="true" />
            <span className="truncate text-sm font-semibold text-stone-900">{meta.title}</span>
            <span className="hidden rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-stone-500 ring-1 ring-line sm:inline">
              {draft.generated_by === 'claude' ? 'Drafted by Claude' : 'Drafted from your report'}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={async () => setCopied(await copyText(letterText(draft)))}
            >
              {copied ? <Check className="size-4 text-fair-600" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
              <span aria-live="polite">{copied ? 'Copied' : 'Copy'}</span>
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={download}>
              <Download className="size-4" aria-hidden="true" />
              Download .txt
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={print}>
              <Printer className="size-4" aria-hidden="true" />
              Print
            </button>
          </div>
        </div>

        <div className="mx-auto max-w-[48rem] px-3 pt-4 sm:px-8 sm:pt-8">
          <div className="grid gap-1 border-b border-dashed border-line pb-3 sm:grid-cols-[5.5rem_minmax(0,1fr)] sm:items-center sm:gap-x-3">
            <label htmlFor={`letter-to-${draft.kind}`} className="px-2 text-xs font-semibold tracking-[0.06em] text-stone-500 uppercase sm:px-0">
              Send to
            </label>
            <textarea
              id={`letter-to-${draft.kind}`}
              rows={1}
              value={draft.to}
              onChange={(e) => onChange({ ...draft, to: e.target.value })}
              className={inputClass}
            />
            <label htmlFor={`letter-subject-${draft.kind}`} className="mt-2 px-2 text-xs font-semibold tracking-[0.06em] text-stone-500 uppercase sm:mt-0 sm:px-0">
              Subject
            </label>
            <textarea
              id={`letter-subject-${draft.kind}`}
              rows={1}
              value={draft.subject}
              onChange={(e) => onChange({ ...draft, subject: e.target.value })}
              className={cn(inputClass, 'font-medium')}
            />
          </div>
          <label htmlFor={`letter-body-${draft.kind}`} className="sr-only">
            Letter text
          </label>
          <textarea
            id={`letter-body-${draft.kind}`}
            ref={bodyRef}
            value={draft.body}
            spellCheck
            onChange={(e) => onChange({ ...draft, body: e.target.value })}
            className="mt-3 mb-4 block min-h-[24rem] w-full resize-none overflow-hidden rounded-lg border border-transparent bg-transparent px-2 py-3 font-sans text-[15px] leading-7 whitespace-pre-wrap text-stone-800 transition-colors hover:border-line focus:border-brand-600 focus:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600/25"
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-paper/70 px-4 py-3 text-[13px] sm:px-6">
          {placeholders > 0 ? (
            <span className="inline-flex items-center gap-1.5 font-medium text-info-700">
              <TriangleAlert className="size-4" aria-hidden="true" />
              Fill in {placeholders === 1 ? 'the part' : `the ${placeholders} parts`} in [square brackets] before sending
            </span>
          ) : (
            <span className="text-stone-500">Read it through and add anything we missed before sending.</span>
          )}
          <span className="flex items-center gap-3 text-stone-500">
            Edits stay on this page. Copy or download before you leave.
            {edited && (
              <button type="button" onClick={() => onChange(original)} className="inline-flex items-center gap-1 font-medium text-stone-700 hover:text-stone-900">
                <RotateCcw className="size-3.5" aria-hidden="true" />
                Undo my edits
              </button>
            )}
          </span>
        </div>
      </div>

      <div id="print-letter">
        <p>To: {draft.to}</p>
        <p>Subject: {draft.subject}</p>
        <br />
        <div style={{ whiteSpace: 'pre-wrap' }}>{draft.body}</div>
      </div>
    </div>
  )
}

export function LetterSection({
  claim,
  muted,
  onLetterSaved,
}: {
  claim: Claim
  /** Nothing to challenge: keep letters available but out of the way. */
  muted: boolean
  onLetterSaved: (letter: Letter) => void
}) {
  const [searchParams, setSearchParams] = useSearchParams()
  const requested = searchParams.get('letter')
  const initialKind: LetterKind | null = requested === 'grievance' || requested === 'ombudsman' ? requested : null

  const [active, setActive] = useState<LetterKind | null>(initialKind)
  const [drafts, setDrafts] = useState<Partial<Record<LetterKind, Letter>>>({})
  const [loadingKind, setLoadingKind] = useState<LetterKind | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showAnyway, setShowAnyway] = useState(Boolean(initialKind))

  const open = async (kind: LetterKind) => {
    setActive(kind)
    setError(null)
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('letter', kind)
        return next
      },
      { replace: true, preventScrollReset: true },
    )
    if (claim.letters[kind]) return
    setLoadingKind(kind)
    try {
      const letter = await api.createLetter(claim.id, kind)
      onLetterSaved(letter)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoadingKind(null)
    }
  }

  // Deep link: /claims/:id?letter=grievance drafts (or opens) that letter.
  const autoOpened = useRef(false)
  useEffect(() => {
    if (autoOpened.current || !initialKind) return
    autoOpened.current = true
    void open(initialKind)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialKind])

  const original = active ? claim.letters[active] : undefined
  const draft = active ? (drafts[active] ?? original) : undefined

  const choices = (
    <div className="grid gap-3 sm:grid-cols-2">
      {(Object.keys(KIND_META) as LetterKind[]).map((kind) => {
        const meta = KIND_META[kind]
        const exists = Boolean(claim.letters[kind])
        const selected = active === kind
        const loading = loadingKind === kind
        return (
          <button
            key={kind}
            type="button"
            onClick={() => void open(kind)}
            aria-pressed={selected}
            disabled={loadingKind !== null}
            className={cn(
              'group flex items-start gap-4 rounded-xl border p-4 text-left transition-[border-color,box-shadow,background-color] sm:p-5',
              selected
                ? 'border-brand-600 bg-white shadow-raised ring-1 ring-brand-600'
                : 'border-line bg-white shadow-card hover:border-line-strong hover:shadow-raised',
              'disabled:cursor-wait',
            )}
          >
            <span
              className={cn(
                'flex size-10 shrink-0 items-center justify-center rounded-xl transition-colors',
                selected ? 'bg-brand-700 text-white' : 'bg-brand-50 text-brand-700',
              )}
            >
              <meta.Icon className="size-5" aria-hidden="true" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[15px] font-semibold text-stone-900">
                {loading ? <Spinner label="Drafting your letter…" /> : exists ? meta.open : meta.action}
              </span>
              <span className="mt-0.5 block text-sm text-stone-600">
                {meta.title}. {meta.description}
              </span>
            </span>
          </button>
        )
      })}
    </div>
  )

  return (
    <section id="letter" aria-labelledby="letter-heading" className="scroll-mt-32">
      <SectionHeading
        id="letter-heading"
        eyebrow="Your complaint letter"
        title={muted ? 'No letter needed' : 'A letter you can send today'}
        description={
          muted
            ? 'Nothing in this claim needs challenging, so you don’t need to write to anyone.'
            : 'We draft it from this report, with the clause or rule for every point. Read it, fill in anything in [square brackets], then send it.'
        }
      />

      <div className="mt-8">
        {muted && !showAnyway ? (
          <button
            type="button"
            onClick={() => setShowAnyway(true)}
            className="text-sm font-medium text-stone-600 underline decoration-stone-300 underline-offset-4 hover:text-stone-900"
          >
            I still want to write to my insurer
          </button>
        ) : (
          choices
        )}
      </div>

      {error && (
        <ErrorNotice title="We couldn’t draft that letter" className="mt-6">
          {error}
        </ErrorNotice>
      )}

      {active && loadingKind === active && !original && (
        <div className="paper mt-6 space-y-3 rounded-xl p-6 sm:p-8" aria-hidden="true">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="mt-6 h-4 w-full" />
          <Skeleton className="h-4 w-11/12" />
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="mt-6 h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      )}

      {active && original && draft && (
        <LetterEditor
          key={active}
          claim={claim}
          original={original}
          draft={draft}
          onChange={(letter) => setDrafts((prev) => ({ ...prev, [letter.kind]: letter }))}
        />
      )}
    </section>
  )
}

import { ArrowUpRight, Landmark, ListChecks, ScrollText } from 'lucide-react'
import type { Citation } from '../api/types'
import { cn } from '../lib/cn'
import { prettyRupees } from '../lib/format'

const KIND_META: Record<Citation['kind'], { label: string; Icon: typeof Landmark }> = {
  rule: { label: 'Regulation', Icon: Landmark },
  policy_clause: { label: 'Your policy wording', Icon: ScrollText },
  non_payable_item: { label: "Policy's non-payable list", Icon: ListChecks },
}

function titleCase(text: string): string {
  if (text !== text.toUpperCase()) return text
  return text.toLowerCase().replace(/(^|[\s(/-])([a-z])/g, (_m, sep: string, ch: string) => sep + ch.toUpperCase())
}

/** "Items that are to be subsumed into Room Charges: ADMISSION KIT" -> heading + context */
function splitTitle(citation: Citation): { heading: string; context: string | null } {
  if (citation.kind === 'non_payable_item') {
    const idx = citation.title.lastIndexOf(': ')
    if (idx > 0) {
      return { heading: titleCase(citation.title.slice(idx + 2)), context: citation.title.slice(0, idx) }
    }
  }
  return { heading: citation.title, context: null }
}

export function CitationCard({ citation, className }: { citation: Citation; className?: string }) {
  const meta = KIND_META[citation.kind] ?? KIND_META.rule
  const { heading, context } = splitTitle(citation)
  const isVerbatim = citation.kind !== 'non_payable_item'
  const page = citation.page !== null && citation.page !== undefined && citation.page !== '' ? `p. ${citation.page}` : null

  return (
    <article className={cn('rounded-xl border border-line bg-paper/50 p-4', className)}>
      <p className="flex items-center gap-1.5 text-[11px] font-semibold tracking-[0.08em] text-brand-700 uppercase">
        <meta.Icon className="size-3.5" aria-hidden="true" />
        {meta.label}
      </p>
      <h4 className="mt-1.5 text-[15px] leading-snug font-semibold text-stone-900">{heading}</h4>
      {context && <p className="mt-0.5 text-[13px] text-stone-500">{context}</p>}

      {citation.quote &&
        (isVerbatim ? (
          <blockquote className="relative mt-3 border-l-2 border-brand-300 pl-3.5 font-display text-[15px] leading-relaxed text-stone-700 italic">
            <span className="sr-only">Quote: </span>“{prettyRupees(citation.quote)}”
          </blockquote>
        ) : (
          <p className="mt-2.5 text-sm leading-relaxed text-stone-600">{prettyRupees(citation.quote)}</p>
        ))}

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[13px] text-stone-500">
        <span title={citation.source_detail ?? undefined} className="font-medium text-stone-600">
          {citation.source}
        </span>
        {citation.clause_ref && (
          <>
            <span aria-hidden="true" className="text-stone-300">
              ·
            </span>
            <span>{citation.clause_ref}</span>
          </>
        )}
        {page && (
          <>
            <span aria-hidden="true" className="text-stone-300">
              ·
            </span>
            <span>{page}</span>
          </>
        )}
      </div>
      {citation.url && (
        <a
          href={citation.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex items-center gap-1 text-[13px] font-semibold text-brand-700 hover:text-brand-900 hover:underline"
        >
          Open the source document
          <ArrowUpRight className="size-3.5" aria-hidden="true" />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      )}
    </article>
  )
}

export function CitationList({
  ids,
  citations,
  className,
}: {
  ids: string[]
  citations: Record<string, Citation>
  className?: string
}) {
  const unique = [...new Set(ids)]
  if (unique.length === 0) return null
  return (
    <div className={cn('space-y-3', className)}>
      {unique.map((id) => {
        const citation = citations[id]
        if (!citation) {
          return (
            <p key={id} className="rounded-xl border border-dashed border-line-strong p-3 text-sm text-stone-500">
              Reference {id}
            </p>
          )
        }
        return <CitationCard key={id} citation={citation} />
      })}
    </div>
  )
}

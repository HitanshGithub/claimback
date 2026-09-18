import { ChevronRight } from 'lucide-react'
import { useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import type { Strength, Verdict } from '../../api/types'
import { cn } from '../../lib/cn'
import { formatINR, plural } from '../../lib/format'
import { VERDICT_ORDER, VERDICTS } from '../../lib/verdicts'
import { Money } from '../Money'
import { StrengthMeter, VerdictChip } from '../Verdict'

export interface PaperRow {
  id: string
  verdict: Verdict
  title: string
  code?: string | null
  subtitle?: string | null
  billed?: number | null
  deducted?: number
  /** Challengeable part when less than the full deduction */
  partial?: number | null
  strength?: Strength | null
  /** Amount this row adds to its verdict tab */
  amount: number
}

type Filter = Verdict | 'all'

/**
 * The signature "paper" list. `mode="bill"` shows billed/deducted columns;
 * `mode="checks"` shows a strength column instead (used for rejected claims).
 */
export function FindingsPaper({
  mode,
  rows,
  selectedId,
  onSelect,
  header,
  intro,
  footerNote,
}: {
  mode: 'bill' | 'checks'
  rows: PaperRow[]
  selectedId: string | null
  onSelect: (id: string, visibleIds: string[]) => void
  header: ReactNode
  intro?: ReactNode
  footerNote?: (visible: PaperRow[]) => ReactNode
}) {
  const [filter, setFilter] = useState<Filter>('all')
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([])

  const groups = VERDICT_ORDER.map((verdict) => {
    const items = rows.filter((r) => r.verdict === verdict)
    return { verdict, count: items.length, amount: items.reduce((sum, r) => sum + r.amount, 0) }
  }).filter((g) => g.count > 0)

  const tabs: { key: Filter; label: string; count: number; amount: number }[] = [
    { key: 'all', label: 'All', count: rows.length, amount: rows.reduce((s, r) => s + (r.deducted ?? 0), 0) },
    ...groups.map((g) => ({ key: g.verdict as Filter, label: VERDICTS[g.verdict].tab, count: g.count, amount: g.amount })),
  ]
  const visible = filter === 'all' ? rows : rows.filter((r) => r.verdict === filter)
  const visibleIds = visible.map((r) => r.id)
  const activeIndex = Math.max(0, tabs.findIndex((t) => t.key === filter))

  const onTabKey = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next = index
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length
    else if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = tabs.length - 1
    else return
    event.preventDefault()
    setFilter(tabs[next].key)
    tabRefs.current[next]?.focus()
  }

  const showAmounts = mode === 'bill'

  return (
    <div>
      {tabs.length > 2 && (
        <div className="-mx-4 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0 scrollbar-none">
          <div role="tablist" aria-label="Filter by what we found" className="flex w-max gap-2">
            {tabs.map((tab, i) => {
              const selected = tab.key === filter
              return (
                <button
                  key={tab.key}
                  ref={(el) => {
                    tabRefs.current[i] = el
                  }}
                  role="tab"
                  id={`tab-${mode}-${tab.key}`}
                  aria-selected={selected}
                  aria-controls={`panel-${mode}`}
                  tabIndex={i === activeIndex ? 0 : -1}
                  onClick={() => setFilter(tab.key)}
                  onKeyDown={(e) => onTabKey(e, i)}
                  className={cn(
                    'flex items-center gap-2 rounded-full border py-1.5 pr-3 pl-2.5 text-sm transition-colors',
                    selected
                      ? 'border-stone-900 bg-stone-900 text-white'
                      : 'border-line-strong bg-white text-stone-700 hover:border-stone-400',
                  )}
                >
                  {tab.key === 'all' ? (
                    <span className={cn('size-2 rounded-full', selected ? 'bg-white/70' : 'bg-stone-400')} aria-hidden="true" />
                  ) : (
                    <span className={cn('size-2 rounded-full', VERDICTS[tab.key].classes.dot)} aria-hidden="true" />
                  )}
                  <span className="font-medium">{tab.label}</span>
                  <span
                    className={cn(
                      'money rounded-full px-1.5 text-xs font-semibold',
                      selected ? 'bg-white/15 text-white' : 'bg-paper-2 text-stone-600',
                    )}
                  >
                    {tab.count}
                  </span>
                  {showAmounts && tab.amount > 0 && (
                    <span className={cn('money text-xs', selected ? 'text-white/75' : 'text-stone-500')}>
                      {formatINR(tab.amount)}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}

      <div className="mt-5">
        <div className="paper overflow-hidden rounded-t-xl">
          {header}
          {intro}
          <div className="perforation mx-5 sm:mx-6" aria-hidden="true" />

          <div
            aria-hidden="true"
            className={cn(
              'hidden gap-x-4 px-6 pt-4 pb-2 text-[11px] font-semibold tracking-[0.08em] text-stone-400 uppercase sm:grid',
              showAmounts
                ? 'grid-cols-[minmax(0,1fr)_6.5rem_7rem_11.5rem_1rem]'
                : 'grid-cols-[minmax(0,1fr)_9rem_11.5rem_1rem]',
            )}
          >
            <span>{showAmounts ? 'Item' : 'What we checked'}</span>
            {showAmounts ? (
              <>
                <span className="text-right">Billed</span>
                <span className="text-right">Deducted</span>
              </>
            ) : (
              <span>Strength</span>
            )}
            <span>What we found</span>
            <span />
          </div>

          <ul
            id={`panel-${mode}`}
            role={tabs.length > 2 ? 'tabpanel' : undefined}
            aria-labelledby={tabs.length > 2 ? `tab-${mode}-${filter}` : undefined}
            className="pb-2"
          >
            {visible.map((row) => {
              const selected = row.id === selectedId
              const meta = VERDICTS[row.verdict]
              const aria = [
                row.title,
                showAmounts && row.deducted !== undefined ? `deducted ${formatINR(row.deducted)}` : null,
                meta.label,
                row.strength ? `${row.strength} case` : null,
              ]
                .filter(Boolean)
                .join(', ')
              return (
                <li key={row.id} className="border-t border-line/70 first:border-t-0">
                  <button
                    type="button"
                    onClick={() => onSelect(row.id, visibleIds)}
                    aria-haspopup="dialog"
                    aria-label={`${aria}. Show why`}
                    className={cn(
                      'group relative grid w-full items-center gap-x-4 gap-y-2 px-5 py-3.5 text-left transition-colors sm:px-6',
                      showAmounts
                        ? 'grid-cols-[minmax(0,1fr)_auto] sm:grid-cols-[minmax(0,1fr)_6.5rem_7rem_11.5rem_1rem]'
                        : 'grid-cols-[minmax(0,1fr)_auto] sm:grid-cols-[minmax(0,1fr)_9rem_11.5rem_1rem]',
                      selected ? 'bg-brand-50/70' : 'hover:bg-paper/80',
                      'focus-visible:bg-paper focus-visible:outline-offset-[-2px]',
                    )}
                  >
                    <span
                      aria-hidden="true"
                      className={cn('absolute top-3 bottom-3 left-0 w-[3px] rounded-r-full', meta.classes.bar)}
                    />
                    <span className="min-w-0">
                      <span className="flex items-baseline gap-2">
                        {row.code !== undefined &&
                          (row.code ? (
                            <span className="shrink-0 font-mono text-[11px] text-stone-400">{row.code}</span>
                          ) : (
                            <span className="shrink-0 text-[11px] font-medium text-stone-400">Across the bill</span>
                          ))}
                      </span>
                      <span className="block text-[15px] leading-snug font-medium text-stone-900 group-hover:text-stone-950">
                        {row.title}
                      </span>
                      {row.subtitle && (
                        <span className="mt-0.5 block truncate text-[13px] text-stone-500">{row.subtitle}</span>
                      )}
                    </span>

                    {showAmounts ? (
                      <>
                        <span className="hidden text-right text-sm text-stone-500 sm:block">
                          {row.billed ? <Money amount={row.billed} /> : <span className="text-stone-300">—</span>}
                        </span>
                        <span className="text-right">
                          <Money
                            amount={row.deducted}
                            className={cn('text-[15px] font-semibold', row.verdict === 'challengeable' ? 'text-challenge-700' : 'text-stone-900')}
                          />
                          {row.partial ? (
                            <span className="money block text-[11px] font-medium text-challenge-700">
                              {formatINR(row.partial)} to challenge
                            </span>
                          ) : null}
                        </span>
                      </>
                    ) : (
                      <span className="hidden sm:block">{row.strength && <StrengthMeter strength={row.strength} />}</span>
                    )}

                    <span className="col-span-2 flex items-center justify-between gap-3 sm:col-span-1 sm:block">
                      <VerdictChip verdict={row.verdict} context={mode === 'bill' ? 'deduction' : 'check'} />
                      {!showAmounts && row.strength && <StrengthMeter strength={row.strength} className="sm:hidden" />}
                    </span>
                    <ChevronRight
                      className="hidden size-4 text-stone-300 transition-transform group-hover:translate-x-0.5 group-hover:text-stone-500 sm:block"
                      aria-hidden="true"
                    />
                  </button>
                </li>
              )
            })}
          </ul>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-paper/70 px-5 py-4 text-sm sm:px-6">
            <span className="text-stone-500">
              {filter === 'all' ? plural(rows.length, mode === 'bill' ? 'deduction' : 'check') : `Showing ${visible.length} of ${rows.length}`}
            </span>
            {footerNote?.(visible)}
          </div>
        </div>
        <div className="paper-tear" aria-hidden="true" />
      </div>
    </div>
  )
}

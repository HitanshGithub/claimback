import type { ComputedValue, DeductionFinding } from '../../api/types'
import { cn } from '../../lib/cn'
import { formatDate, formatINR, formatNumber, humanizeKey } from '../../lib/format'

interface Comparison {
  value: number
  /** e.g. "months of continuous cover" -> "84 months of continuous cover" */
  valueLabel: string
  limit: number
  /** builds e.g. "60-month moratorium" from the formatted limit */
  limitText: (formatted: string) => string
  unit: 'number' | 'money'
  /** true when the value being past the limit helps the policyholder */
  overIsGood: boolean
}

const MONEY_KEY = /(amount|admissible|payment|payable|rent|per_day|base|claimed|paid|inr)/i
const DATE_VALUE = /^\d{4}-\d{2}-\d{2}$/

function num(v: ComputedValue | undefined): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

const PAIRS: { a: string; b: string; build: (x: number, y: number) => Comparison }[] = [
  {
    a: 'continuous_months',
    b: 'moratorium_months',
    build: (x, y) => ({ value: x, valueLabel: 'months of continuous cover', limit: y, limitText: (f) => `${f}-month moratorium`, unit: 'number', overIsGood: true }),
  },
  {
    a: 'computed_months',
    b: 'required_months',
    build: (x, y) => ({ value: x, valueLabel: 'months of cover', limit: y, limitText: (f) => `${f}-month waiting period`, unit: 'number', overIsGood: true }),
  },
  {
    a: 'continuous_months',
    b: 'waiting_period_months',
    build: (x, y) => ({ value: x, valueLabel: 'months of cover', limit: y, limitText: (f) => `${f}-month waiting period`, unit: 'number', overIsGood: true }),
  },
  {
    a: 'days_taken',
    b: 'allowed_days',
    build: (x, y) => ({ value: x, valueLabel: x === 1 ? 'day to decide' : 'days to decide', limit: y, limitText: (f) => `${f} days allowed`, unit: 'number', overIsGood: true }),
  },
  {
    a: 'actual_per_day',
    b: 'eligible_per_day',
    build: (x, y) => ({ value: x, valueLabel: 'a day for the room', limit: y, limitText: (f) => `${f} a day allowed`, unit: 'money', overIsGood: false }),
  },
]

function comparisonsFrom(computed: Record<string, ComputedValue>): { comparisons: Comparison[]; used: Set<string> } {
  const used = new Set<string>()
  const comparisons: Comparison[] = []
  for (const { a, b, build } of PAIRS) {
    if (used.has(a) || used.has(b)) continue
    const x = num(computed[a])
    const y = num(computed[b])
    if (x === null || y === null) continue
    comparisons.push(build(x, y))
    used.add(a)
    used.add(b)
  }
  return { comparisons, used }
}

function CompareMeter({ c }: { c: Comparison }) {
  const fmt = (n: number) => (c.unit === 'money' ? formatINR(n) : formatNumber(n))
  const max = Math.max(c.value, c.limit) * 1.12 || 1
  const over = c.value > c.limit
  return (
    <div className="rounded-lg border border-line bg-white p-3.5">
      <p className="flex flex-wrap items-baseline gap-x-1.5 gap-y-1 text-sm text-stone-600">
        <span className="money text-xl font-semibold text-stone-900">{fmt(c.value)}</span>
        <span>{c.valueLabel}</span>
        <span className="px-0.5 text-stone-400">vs</span>
        <span className="font-medium text-stone-800">{c.limitText(fmt(c.limit))}</span>
      </p>
      <div className="relative mt-3 h-2 rounded-full bg-paper-3" aria-hidden="true">
        <div
          className={cn('h-full rounded-full', over && !c.overIsGood ? 'bg-stone-500' : 'bg-brand-600')}
          style={{ width: `${(c.value / max) * 100}%` }}
        />
        <div
          className="absolute -top-1 h-4 w-[2px] rounded-full bg-stone-800"
          style={{ left: `calc(${(c.limit / max) * 100}% - 1px)` }}
        />
      </div>
    </div>
  )
}

function formatValue(key: string, value: ComputedValue): string {
  if (value === null) return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') {
    if (/pct|percent|ratio/i.test(key)) return value <= 1 && /ratio/i.test(key) ? `${formatNumber(value * 100)}%` : `${formatNumber(value)}%`
    return MONEY_KEY.test(key) ? formatINR(value) : formatNumber(value)
  }
  if (typeof value === 'string') return DATE_VALUE.test(value) ? formatDate(value) : value
  if (Array.isArray(value)) return value.map((v) => formatValue(key, v)).join(', ')
  return JSON.stringify(value)
}

const KEY_LABELS: Record<string, string> = {
  admissible: 'Admissible amount',
  co_payment: 'Co-payment',
  documents_received: 'Documents received',
  decision_date: 'Decision',
  continuous_cover_start: 'Cover started',
  admission_date: 'Admitted',
}

export function hasComparison(computed: Record<string, ComputedValue>): boolean {
  return comparisonsFrom(computed).comparisons.length > 0
}

export function ComputedFacts({
  computed,
  findings,
  onOpenFinding,
  compact,
  comparisonsOnly,
}: {
  computed: Record<string, ComputedValue>
  findings?: DeductionFinding[]
  onOpenFinding?: (id: string) => void
  compact?: boolean
  comparisonsOnly?: boolean
}) {
  const { comparisons, used } = comparisonsFrom(computed)
  if (comparisonsOnly) {
    return (
      <div className="space-y-3">
        {comparisons.map((c) => (
          <CompareMeter key={c.valueLabel} c={c} />
        ))}
      </div>
    )
  }
  const refs = Array.isArray(computed.deductions)
    ? (computed.deductions.filter((d) => typeof d === 'string') as string[])
    : []
  if (refs.length) used.add('deductions')
  const rest = Object.entries(computed).filter(([k]) => !used.has(k))
  if (!comparisons.length && !refs.length && !rest.length) return null

  return (
    <div className="space-y-3">
      {comparisons.map((c) => (
        <CompareMeter key={c.valueLabel} c={c} />
      ))}
      {rest.length > 0 && (
        <dl className={cn('grid gap-x-5 gap-y-2.5', compact ? 'grid-cols-2' : 'grid-cols-2 sm:grid-cols-3')}>
          {rest.map(([key, value]) => (
            <div key={key} className="min-w-0">
              <dt className="text-xs text-stone-500">{KEY_LABELS[key] ?? humanizeKey(key)}</dt>
              <dd className="money mt-0.5 truncate text-sm font-semibold text-stone-800">{formatValue(key, value)}</dd>
            </div>
          ))}
        </dl>
      )}
      {refs.length > 0 && (
        <div>
          <p className="text-xs text-stone-500">Applies to</p>
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {refs.map((id) => {
              const f = findings?.find((x) => x.id === id)
              const label = f ? f.description : id
              return (
                <li key={id}>
                  {onOpenFinding && f ? (
                    <button
                      type="button"
                      onClick={() => onOpenFinding(id)}
                      className="max-w-[16rem] truncate rounded-full border border-line bg-white px-2.5 py-1 text-xs font-medium text-stone-700 transition-colors hover:border-brand-300 hover:text-brand-800"
                    >
                      {label}
                    </button>
                  ) : (
                    <span className="inline-block max-w-[16rem] truncate rounded-full border border-line bg-white px-2.5 py-1 text-xs font-medium text-stone-700">
                      {label}
                    </span>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}

const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

const plainNumber = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })

/** 139700 -> "₹1,39,700" */
export function formatINR(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return '—'
  return inr.format(Math.round(amount))
}

/** 139700 -> "1,39,700" */
export function formatNumber(value: number): string {
  return plainNumber.format(value)
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function parseDateParts(value: string): { y: number; m: number; d: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) return null
  return { y: Number(match[1]), m: Number(match[2]), d: Number(match[3]) }
}

/** "2026-08-14" -> "14 Aug 2026". Timestamps use the viewer's local date. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const p = parseDateParts(value)
    if (p) return `${p.d} ${MONTHS[p.m - 1]} ${p.y}`
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`
}

/** "2026-09-17T10:42:11Z" -> "17 Sep 2026, 4:12 pm" */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const time = date
    .toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true })
    .replace(/\s?(AM|PM)$/i, (m) => ` ${m.trim().toLowerCase()}`)
  return `${formatDate(value)}, ${time}`
}

/** "3 Aug 2026 – 6 Aug 2026" shortened to "3–6 Aug 2026" when possible */
export function formatDateRange(start: string, end: string): string {
  const a = parseDateParts(start)
  const b = parseDateParts(end)
  if (!a || !b) return `${formatDate(start)} – ${formatDate(end)}`
  if (a.y === b.y && a.m === b.m) return `${a.d}–${b.d} ${MONTHS[a.m - 1]} ${a.y}`
  if (a.y === b.y) return `${a.d} ${MONTHS[a.m - 1]} – ${b.d} ${MONTHS[b.m - 1]} ${a.y}`
  return `${formatDate(start)} – ${formatDate(end)}`
}

/** Whole days between two ISO dates (b - a). */
export function daysBetween(a: string, b: string): number {
  const pa = parseDateParts(a)
  const pb = parseDateParts(b)
  if (!pa || !pb) return 0
  const ta = Date.UTC(pa.y, pa.m - 1, pa.d)
  const tb = Date.UTC(pb.y, pb.m - 1, pb.d)
  return Math.round((tb - ta) / 86_400_000)
}

export function plural(n: number, word: string, pluralWord?: string): string {
  return `${formatNumber(n)} ${n === 1 ? word : (pluralWord ?? `${word}s`)}`
}

/**
 * The engine writes money in prose as "Rs 1,39,700" (and sometimes "Rs 40,000.00").
 * Show it as "₹1,39,700" so prose and figures match.
 */
export function prettyRupees(text: string): string {
  return text
    .replace(/\bRs\.?\s?(\d[\d,]*)(\.00)?(?!\d)/g, (_m, digits: string) => `₹${digits}`)
    .replace(/\bINR\s?(\d[\d,]*)(\.00)?(?!\d)/g, (_m, digits: string) => `₹${digits}`)
}

/** "continuous_cover_start" -> "Continuous cover start" */
export function humanizeKey(key: string): string {
  const words = key.replace(/[_-]+/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Split "Gallbladder surgery - 'non-payable consumables' deductions (cashless)" into a heading and a subheading. */
export function splitTitle(title: string): { heading: string; rest: string | null } {
  const idx = title.indexOf(' - ')
  if (idx === -1) return { heading: title, rest: null }
  return { heading: title.slice(0, idx), rest: title.slice(idx + 3) }
}

const CATEGORY_LABELS: Record<string, string> = {
  non_payable_item: 'Non-payable item',
  non_payable_consumables: 'Non-payable consumables',
  not_in_lists: 'Not on any non-payable list',
  proportionate_deduction: 'Proportionate deduction',
  reasonable_customary: 'Reasonable & customary charges',
  exclusion: 'Policy exclusion',
  policy_limit: 'Policy limit',
  ped_non_disclosure: 'Non-disclosure of an existing illness',
  waiting_period: 'Waiting period',
  room_rent_cap: 'Room rent cap',
  modern_treatment: 'Modern treatment',
  sub_limit: 'Sub-limit',
  co_payment: 'Co-payment',
  day_care: 'Day care',
  hospitalization_24h: '24-hour hospitalisation',
  delayed_intimation: 'Late intimation',
  documents: 'Documents',
  unknown: 'Other',
  other: 'Other',
}

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? humanizeKey(category)
}

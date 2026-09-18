import { CircleAlert, CircleCheck, CircleHelp, CircleMinus, Hospital, type LucideProps } from 'lucide-react'
import type { Strength, Verdict } from '../api/types'
import { cn } from '../lib/cn'
import { STRENGTH_LABEL, STRENGTH_LEVEL, VERDICTS } from '../lib/verdicts'

export function VerdictIcon({ verdict, ...props }: { verdict: Verdict } & LucideProps) {
  switch (verdict) {
    case 'challengeable':
      return <CircleAlert {...props} />
    case 'needs_more_info':
      return <CircleHelp {...props} />
    case 'fair_ask_hospital_to_absorb':
      return <Hospital {...props} />
    case 'fair':
      return <CircleCheck {...props} />
    default:
      return <CircleMinus {...props} />
  }
}

export function VerdictChip({
  verdict,
  className,
  size = 'md',
  context = 'deduction',
}: {
  verdict: Verdict
  className?: string
  size?: 'sm' | 'md'
  context?: 'deduction' | 'check'
}) {
  const meta = VERDICTS[verdict]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-semibold whitespace-nowrap ring-1 ring-inset',
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
        meta.classes.chip,
        className,
      )}
    >
      <VerdictIcon verdict={verdict} aria-hidden="true" className={size === 'sm' ? 'size-3' : 'size-3.5'} strokeWidth={2.25} />
      {context === 'check' ? meta.checkLabel : meta.label}
    </span>
  )
}

export function StrengthMeter({ strength, className }: { strength: Strength; className?: string }) {
  const level = STRENGTH_LEVEL[strength]
  return (
    <span className={cn('inline-flex items-center gap-2 text-xs font-medium text-stone-600', className)}>
      <span className="flex items-end gap-[3px]" aria-hidden="true">
        {[1, 2, 3].map((i) => (
          <span
            key={i}
            className={cn('w-[5px] rounded-[2px]', i <= level ? 'bg-brand-700' : 'bg-stone-300/70')}
            style={{ height: `${4 + i * 3}px` }}
          />
        ))}
      </span>
      {STRENGTH_LABEL[strength]}
    </span>
  )
}

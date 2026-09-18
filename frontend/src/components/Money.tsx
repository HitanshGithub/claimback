import { cn } from '../lib/cn'
import { formatINR } from '../lib/format'
import { useCountUp } from '../lib/hooks'

export function Money({ amount, className }: { amount: number | null | undefined; className?: string }) {
  return <span className={cn('money', className)}>{formatINR(amount)}</span>
}

/** Counts up to the amount on first render; screen readers get the final value. */
export function CountUpMoney({
  amount,
  className,
  delayMs = 0,
}: {
  amount: number
  className?: string
  delayMs?: number
}) {
  const value = useCountUp(amount, 1100, delayMs)
  return (
    <span className={cn('money', className)}>
      <span className="sr-only">{formatINR(amount)}</span>
      <span aria-hidden="true">{formatINR(value)}</span>
    </span>
  )
}

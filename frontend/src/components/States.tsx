import { LoaderCircle, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../lib/cn'

export function Spinner({ className, label }: { className?: string; label?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)} role={label ? 'status' : undefined}>
      <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
      {label && <span>{label}</span>}
    </span>
  )
}

export function ErrorNotice({
  title,
  children,
  action,
  className,
}: {
  title: string
  children?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col gap-3 rounded-xl border border-challenge-200 bg-challenge-50 p-4 text-sm text-challenge-800 sm:flex-row sm:items-start',
        className,
      )}
    >
      <TriangleAlert className="size-5 shrink-0 text-challenge-600" aria-hidden="true" />
      <div className="flex-1">
        <p className="font-semibold">{title}</p>
        {children && <div className="mt-1 text-challenge-700">{children}</div>}
      </div>
      {action}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-lg bg-paper-3/70', className)} aria-hidden="true" />
}

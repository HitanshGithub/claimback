import type { ReactNode } from 'react'
import { cn } from '../lib/cn'

export function SectionHeading({
  id,
  eyebrow,
  title,
  description,
  className,
  action,
}: {
  id?: string
  eyebrow?: string
  title: ReactNode
  description?: ReactNode
  className?: string
  action?: ReactNode
}) {
  return (
    <div className={cn('flex flex-wrap items-end justify-between gap-4', className)}>
      <div className="max-w-2xl">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2 id={id} className="mt-2 font-display text-[1.75rem] leading-tight tracking-tight text-balance text-stone-900 sm:text-[2rem]">
          {title}
        </h2>
        {description && <p className="mt-2 text-[15px] leading-relaxed text-stone-600">{description}</p>}
      </div>
      {action}
    </div>
  )
}

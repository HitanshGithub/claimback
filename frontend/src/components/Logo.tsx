import { cn } from '../lib/cn'

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true" className={cn('size-8', className)}>
      <rect width="32" height="32" rx="8" className="fill-brand-700" />
      <path d="M10 8.5h9.5L23 12v11.5H10z" fill="#FAF7F2" />
      <path d="M13 14h7M13 17h5" className="stroke-brand-700" strokeWidth="1.6" strokeLinecap="round" />
      <path
        d="M13.2 20.6l1.9 1.8 3.7-3.9"
        className="stroke-challenge-500"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <LogoMark />
      <span className="font-display text-[1.35rem] leading-none font-semibold tracking-tight text-stone-900">
        ClaimBack
      </span>
    </span>
  )
}

import { X } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '../lib/cn'
import { useBodyScrollLock } from '../lib/hooks'

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Side drawer on large screens, bottom sheet on small ones.
 * Modal: traps focus, closes on Escape or backdrop click, restores focus on close.
 */
export function Sheet({
  open,
  onClose,
  labelledBy,
  header,
  footer,
  children,
}: {
  open: boolean
  onClose: () => void
  labelledBy: string
  header?: ReactNode
  footer?: ReactNode
  children: ReactNode
}) {
  const [mounted, setMounted] = useState(open)
  const [visible, setVisible] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)
  const returnFocusRef = useRef<HTMLElement | null>(null)
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  useEffect(() => {
    if (open) {
      returnFocusRef.current = document.activeElement as HTMLElement | null
      setMounted(true)
      const frame = requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)))
      return () => cancelAnimationFrame(frame)
    }
    setVisible(false)
    const timer = window.setTimeout(() => {
      setMounted(false)
      returnFocusRef.current?.focus?.({ preventScroll: true })
    }, 260)
    return () => window.clearTimeout(timer)
  }, [open])

  useEffect(() => {
    if (mounted && open) panelRef.current?.focus({ preventScroll: true })
  }, [mounted, open])

  useBodyScrollLock(mounted)

  useEffect(() => {
    if (!mounted) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onCloseRef.current()
        return
      }
      if (event.key !== 'Tab' || !panelRef.current) return
      const nodes = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null,
      )
      if (nodes.length === 0) {
        event.preventDefault()
        return
      }
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      const active = document.activeElement
      if (event.shiftKey && (active === first || active === panelRef.current)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [mounted])

  if (!mounted) return null

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div
        className={cn(
          'absolute inset-0 bg-stone-900/35 transition-opacity duration-300',
          visible ? 'opacity-100' : 'opacity-0',
        )}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        tabIndex={-1}
        className={cn(
          'absolute flex flex-col bg-white outline-none',
          'inset-x-0 bottom-0 max-h-[90dvh] rounded-t-2xl shadow-[0_-12px_40px_-12px_rgb(28_25_23/0.3)]',
          'lg:inset-y-0 lg:right-0 lg:left-auto lg:max-h-none lg:w-[32rem] lg:rounded-none lg:shadow-drawer',
          'transition-transform duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)] motion-reduce:transition-none',
          visible ? 'translate-y-0 lg:translate-x-0' : 'translate-y-full lg:translate-x-full lg:translate-y-0',
        )}
      >
        <div className="mx-auto mt-2.5 h-1 w-10 shrink-0 rounded-full bg-stone-300 lg:hidden" aria-hidden="true" />
        <div className="flex items-start gap-3 border-b border-line px-5 pt-3 pb-4 sm:px-6 lg:pt-5">
          <div className="min-w-0 flex-1">{header}</div>
          <button
            type="button"
            onClick={onClose}
            className="-mr-2 rounded-lg p-2 text-stone-500 transition-colors hover:bg-paper-2 hover:text-stone-900"
            aria-label="Close details"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5 sm:px-6">{children}</div>
        {footer && <div className="border-t border-line bg-paper/60 px-5 py-3 sm:px-6">{footer}</div>}
      </div>
    </div>,
    document.body,
  )
}

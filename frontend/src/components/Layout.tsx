import { FileUp, FolderOpen } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, ScrollRestoration, useLocation } from 'react-router'
import { IS_MOCK } from '../api/client'
import { cn } from '../lib/cn'
import { Logo } from './Logo'

function Header() {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const navClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
      isActive ? 'text-stone-900' : 'text-stone-600 hover:bg-paper-2 hover:text-stone-900',
    )

  return (
    <header
      className={cn(
        'sticky top-0 z-40 border-b bg-paper/95 transition-[border-color,box-shadow] duration-200 supports-[backdrop-filter]:bg-paper/85 supports-[backdrop-filter]:backdrop-blur-sm print:hidden',
        scrolled ? 'border-line shadow-[0_1px_0_rgb(28_25_23/0.02)]' : 'border-transparent',
      )}
    >
      <div className="container-page flex h-16 items-center justify-between gap-3">
        <Link to="/" className="-ml-1 rounded-lg px-1 py-1" aria-label="ClaimBack home">
          <Logo />
        </Link>
        <nav aria-label="Main" className="flex items-center gap-1">
          <Link to="/#samples" className="hidden rounded-lg px-3 py-2 text-sm font-medium text-stone-600 transition-colors hover:bg-paper-2 hover:text-stone-900 md:inline-flex">
            Sample claims
          </Link>
          <NavLink to="/claims" end className={navClass} aria-label="My claims">
            <FolderOpen className="size-5 sm:hidden" aria-hidden="true" />
            <span className="hidden sm:inline">My claims</span>
          </NavLink>
          <Link to="/new" className="btn-primary btn-sm ml-1 whitespace-nowrap sm:ml-2 sm:px-3.5 sm:py-2 sm:text-sm">
            <FileUp className="size-4" aria-hidden="true" />
            Check my claim
          </Link>
        </nav>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="mt-24 border-t border-line bg-paper-2/60 print:hidden">
      <div className="container-page flex flex-col gap-6 py-10 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-md">
          <Logo />
          <p className="mt-3 text-sm leading-relaxed text-stone-600">
            ClaimBack gives information, not legal advice. Always check the cited clauses and rules before relying on
            them. Sample claims use fictional people, hospitals and insurers.
          </p>
        </div>
        <div className="flex flex-col gap-2 text-sm text-stone-600 sm:items-end">
          <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2">
            <Link className="hover:text-stone-900" to="/new">
              Check my claim
            </Link>
            <Link className="hover:text-stone-900" to="/#samples">
              Sample claims
            </Link>
            <Link className="hover:text-stone-900" to="/claims">
              My claims
            </Link>
          </nav>
          <p className="text-stone-500">
            Rules checked against IRDAI regulations in force on 17 Sep 2026
            {IS_MOCK && <span className="ml-2 rounded-full bg-paper-3 px-2 py-0.5 text-xs font-medium text-stone-600">Demo data</span>}
          </p>
        </div>
      </div>
    </footer>
  )
}

/** Scrolls to `#hash` targets after navigation (e.g. /#samples). */
function HashScroller() {
  const { hash, pathname } = useLocation()
  useEffect(() => {
    if (!hash) return
    const id = decodeURIComponent(hash.slice(1))
    let tries = 0
    const attempt = () => {
      const el = document.getElementById(id)
      if (el) {
        el.scrollIntoView({ block: 'start' })
        return
      }
      if (tries++ < 20) window.setTimeout(attempt, 50)
    }
    attempt()
  }, [hash, pathname])
  return null
}

export function Layout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only z-50 rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>
      <Header />
      <main id="main" className="flex-1" tabIndex={-1}>
        <Outlet />
      </main>
      <Footer />
      <ScrollRestoration />
      <HashScroller />
    </div>
  )
}

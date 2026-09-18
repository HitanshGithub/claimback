import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router'
import { usePageTitle } from '../lib/usePageTitle'

export function NotFoundPage() {
  usePageTitle('Page not found')
  return (
    <div className="container-page py-24 text-center">
      <p className="eyebrow">404</p>
      <h1 className="mt-3 font-display text-4xl tracking-tight text-stone-900">We couldn’t find that page</h1>
      <p className="mx-auto mt-3 max-w-md text-stone-600">The link may be old or mistyped.</p>
      <Link to="/" className="btn-secondary mt-8">
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to home
      </Link>
    </div>
  )
}

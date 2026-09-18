import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import type { Claim } from '../api/types'

const POLL_MS = 1000
const RETRY_MS = 2500

/**
 * Loads a claim and polls it about once a second while it is processing.
 * Transient network errors while polling keep the last good claim and retry.
 */
export function useClaim(id: string) {
  const [claim, setClaim] = useState<Claim | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    let timer: number | undefined
    setError(null)

    const tick = async () => {
      try {
        const next = await api.getClaim(id)
        if (cancelled) return
        setClaim(next)
        setError(null)
        if (next.status === 'processing') timer = window.setTimeout(tick, POLL_MS)
      } catch (err) {
        if (cancelled) return
        setError(err)
        const notFound = err instanceof ApiError && err.status === 404
        if (!notFound) timer = window.setTimeout(tick, RETRY_MS)
      }
    }
    void tick()

    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [id, nonce])

  // Reset when navigating between claims.
  useEffect(() => {
    setClaim(null)
  }, [id])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { claim, error, setClaim, reload }
}

import { useEffect } from 'react'

export function usePageTitle(title: string | null | undefined) {
  useEffect(() => {
    document.title = title ? `${title} · ClaimBack` : 'ClaimBack · Was your health claim cut fairly?'
  }, [title])
}

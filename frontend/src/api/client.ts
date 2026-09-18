import type {
  Claim,
  ClaimSummary,
  DocumentKind,
  Health,
  Letter,
  LetterKind,
  NewClaimUpload,
  PolicyWording,
  SampleSummary,
} from './types'

/** Base URL of a deployed API, e.g. https://api.example.com (no trailing slash). Empty = same origin / dev proxy. */
export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/+$/, '')

/** `VITE_MOCK=1` serves fixtures from src/mocks instead of the network. */
export const IS_MOCK = import.meta.env.VITE_MOCK === '1'

export class ApiError extends Error {
  readonly status: number
  readonly detail: string | null

  constructor(status: number, message: string, detail: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export interface ClaimBackApi {
  health(): Promise<Health>
  wordings(): Promise<PolicyWording[]>
  samples(): Promise<SampleSummary[]>
  createSampleClaim(sampleId: string): Promise<Claim>
  createClaim(upload: NewClaimUpload): Promise<Claim>
  listClaims(): Promise<ClaimSummary[]>
  getClaim(id: string): Promise<Claim>
  deleteClaim(id: string): Promise<void>
  createLetter(claimId: string, kind: LetterKind): Promise<Letter>
}

function friendlyMessage(status: number): string {
  if (status === 404) return "We couldn't find that."
  if (status === 409) return "This claim isn't ready yet."
  if (status === 413) return 'That file is too large.'
  if (status === 503) return 'This feature is switched off right now.'
  if (status >= 500) return 'Something went wrong on our side. Please try again in a moment.'
  return 'Something went wrong. Please try again.'
}

function extractDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object' || !('detail' in body)) return null
  const detail = (body as { detail: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : null))
      .filter(Boolean)
    return messages.length ? messages.join('; ') : null
  }
  return null
}

// ---------------------------------------------------------------------------
// Owner id: the API scopes claims to this browser. Sent as a header on every
// request, and as `?o=` on document links (new tabs can't send headers).
// ---------------------------------------------------------------------------
const OWNER_KEY = 'claimback.owner'
const OWNER_HEADER = 'X-ClaimBack-Owner'
let memoryOwnerId: string | null = null

function randomId(): string {
  try {
    return crypto.randomUUID()
  } catch {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`
  }
}

export function ownerId(): string {
  try {
    const stored = localStorage.getItem(OWNER_KEY)
    if (stored) return stored
    const id = memoryOwnerId ?? randomId()
    localStorage.setItem(OWNER_KEY, id)
    memoryOwnerId = id
    return id
  } catch {
    memoryOwnerId ??= randomId()
    return memoryOwnerId
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { Accept: 'application/json', [OWNER_HEADER]: ownerId(), ...init?.headers },
    })
  } catch {
    throw new ApiError(0, "We can't reach ClaimBack right now. Check your connection and try again.")
  }

  if (!res.ok) {
    let detail: string | null = null
    try {
      detail = extractDetail(await res.json())
    } catch {
      // body was not JSON
    }
    throw new ApiError(res.status, detail ?? friendlyMessage(res.status), detail)
  }

  if (res.status === 204) return undefined as T
  const text = await res.text()
  return (text ? JSON.parse(text) : undefined) as T
}

function json(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

const httpApi: ClaimBackApi = {
  health: () => request<Health>('/api/health'),
  wordings: () => request<PolicyWording[]>('/api/wordings'),
  samples: () => request<SampleSummary[]>('/api/samples'),
  createSampleClaim: (sampleId) => request<Claim>('/api/claims/sample', json({ sample_id: sampleId })),
  createClaim: (upload) => {
    const form = new FormData()
    form.append('hospital_bill', upload.hospital_bill)
    form.append('insurer_letter', upload.insurer_letter)
    form.append('policy_schedule', upload.policy_schedule)
    if (upload.discharge_summary) form.append('discharge_summary', upload.discharge_summary)
    if (upload.policy_wording_id) form.append('policy_wording_id', upload.policy_wording_id)
    return request<Claim>('/api/claims', { method: 'POST', body: form })
  },
  listClaims: () => request<ClaimSummary[]>('/api/claims'),
  getClaim: (id) => request<Claim>(`/api/claims/${encodeURIComponent(id)}`),
  deleteClaim: (id) => request<void>(`/api/claims/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  createLetter: (claimId, kind) =>
    request<Letter>(`/api/claims/${encodeURIComponent(claimId)}/letters`, json({ kind })),
}

let mockApiPromise: Promise<ClaimBackApi> | null = null
function loadMockApi(): Promise<ClaimBackApi> {
  mockApiPromise ??= import('./mock').then((m) => m.mockApi)
  return mockApiPromise
}

/** Lazily delegates every call to the mock implementation (kept out of the main bundle). */
const mockProxy: ClaimBackApi = {
  health: () => loadMockApi().then((m) => m.health()),
  wordings: () => loadMockApi().then((m) => m.wordings()),
  samples: () => loadMockApi().then((m) => m.samples()),
  createSampleClaim: (sampleId) => loadMockApi().then((m) => m.createSampleClaim(sampleId)),
  createClaim: (upload) => loadMockApi().then((m) => m.createClaim(upload)),
  listClaims: () => loadMockApi().then((m) => m.listClaims()),
  getClaim: (id) => loadMockApi().then((m) => m.getClaim(id)),
  deleteClaim: (id) => loadMockApi().then((m) => m.deleteClaim(id)),
  createLetter: (claimId, kind) => loadMockApi().then((m) => m.createLetter(claimId, kind)),
}

export const api: ClaimBackApi = IS_MOCK ? mockProxy : httpApi

/** URL of an original uploaded document, or null when not available (mock mode). */
export function documentUrl(claimId: string, kind: DocumentKind): string | null {
  if (IS_MOCK) return null
  return `${API_BASE}/api/claims/${encodeURIComponent(claimId)}/documents/${kind}?o=${encodeURIComponent(ownerId())}`
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return 'Something went wrong. Please try again.'
}

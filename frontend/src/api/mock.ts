/**
 * Mock implementation of the ClaimBack API (VITE_MOCK=1).
 *
 * - Fixtures in src/mocks are real API responses (claim-S1.json ... claim-S5.json,
 *   samples.json, wordings.json, health.json).
 * - `POST /api/claims/sample` returns that sample's claim (id `sample-s2` etc.) and
 *   simulates processing: progress steps flip to done ~500 ms apart.
 * - Claims, deletions and drafted letters persist in localStorage so /claims works
 *   across reloads.
 *
 * Handy URLs for demos and screenshots:
 *   /claims/sample-s1        complete report (letters as exported)
 *   /claims/mock-live-s1     processing that starts when the page first loads it
 *   /claims/mock-failed-s1   a failed claim
 *   ?mock_llm=bedrock        pretend Claude on Bedrock is on (enables uploads)
 */
import healthJson from '../mocks/health.json'
import { buildMockLetter } from '../mocks/letter-template'
import samplesJson from '../mocks/samples.json'
import wordingsJson from '../mocks/wordings.json'
import { ApiError, type ClaimBackApi } from './client'
import type {
  Claim,
  ClaimDocument,
  ClaimSummary,
  Health,
  Letter,
  LetterKind,
  PolicyWording,
  ProgressStep,
  SampleSummary,
} from './types'

const STEP_MS = 500
const SETTLE_MS = 600
const STORAGE_KEY = 'claimback.mock.v2'
const LLM_KEY = 'claimback.mock.llm'

// Fixtures, keyed by upper-case sample id ("S1").
const fixtureModules = import.meta.glob('../mocks/claim-*.json', { eager: true, import: 'default' })
const fixtures = new Map<string, Claim>()
for (const [path, mod] of Object.entries(fixtureModules)) {
  const claim = mod as Claim
  const fromName = /claim-([^/]+)\.json$/.exec(path)?.[1]
  const sampleId = (claim.sample_id ?? fromName ?? '').toUpperCase()
  if (sampleId) fixtures.set(sampleId, claim)
}

const DEFAULT_STEPS: ProgressStep[] = [
  { name: 'read_documents', label: 'Reading your documents', status: 'pending', detail: null },
  { name: 'check_items', label: "Checking every deduction against the policy's non-payable lists", status: 'pending', detail: null },
  { name: 'check_policy', label: 'Checking your policy wording', status: 'pending', detail: null },
  { name: 'check_rules', label: 'Checking IRDAI rules and deadlines', status: 'pending', detail: null },
  { name: 'similar_cases', label: 'Finding similar Ombudsman and court decisions', status: 'pending', detail: null },
  { name: 'ai_review', label: "Claude reviews anything the rules can't settle", status: 'pending', detail: null },
  { name: 'write_report', label: 'Writing your report', status: 'pending', detail: null },
]

interface MockRecord {
  id: string
  sampleId: string
  source: 'sample' | 'upload'
  createdAt: number
  documents?: ClaimDocument[]
}

interface MockState {
  records: MockRecord[]
  deleted: string[]
  letters: Record<string, Partial<Record<LetterKind, Letter>>>
}

let memoryState: MockState = { records: [], deleted: [], letters: {} }
const liveStarts = new Map<string, number>()

function loadState(): MockState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) memoryState = { ...memoryState, ...(JSON.parse(raw) as MockState) }
  } catch {
    // storage unavailable - keep in-memory state
  }
  return memoryState
}

function saveState(state: MockState) {
  memoryState = state
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // ignore
  }
}

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

function llmMode(): Health['llm'] {
  try {
    const param = new URLSearchParams(window.location.search).get('mock_llm')
    if (param === 'bedrock' || param === 'offline') sessionStorage.setItem(LLM_KEY, param)
    const stored = sessionStorage.getItem(LLM_KEY)
    if (stored === 'bedrock' || stored === 'offline') return stored
  } catch {
    // ignore
  }
  return (healthJson as Health).llm
}

function fixtureFor(sampleId: string): Claim {
  const fixture = fixtures.get(sampleId.toUpperCase()) ?? fixtures.values().next().value
  if (!fixture) throw new ApiError(404, 'No mock fixtures found in src/mocks.')
  return clone(fixture)
}

function sampleIdForClaimId(id: string): string | null {
  for (const [sampleId, claim] of fixtures) {
    if (claim.id === id) return sampleId
  }
  return null
}

interface MaterializeOptions {
  id: string
  createdAt: string
  source: 'sample' | 'upload'
  documents?: ClaimDocument[]
  elapsedMs: number
  /** Keep letters that ship with the fixture (true for fixtures opened directly). */
  keepFixtureLetters: boolean
}

function materialize(sampleId: string, opts: MaterializeOptions): Claim {
  const fixture = fixtureFor(sampleId)
  const stored = loadState().letters[opts.id] ?? {}
  const base: Claim = {
    ...fixture,
    id: opts.id,
    created_at: opts.createdAt,
    source: opts.source,
    sample_id: opts.source === 'sample' ? (fixture.sample_id ?? sampleId.toUpperCase()) : null,
    title: opts.source === 'upload' ? 'Your uploaded claim' : fixture.title,
    documents: opts.documents ?? fixture.documents,
    letters: { ...(opts.keepFixtureLetters ? fixture.letters : {}), ...stored },
  }
  const steps = fixture.progress.length ? fixture.progress : DEFAULT_STEPS
  const total = steps.length * STEP_MS + SETTLE_MS
  if (opts.elapsedMs >= total) return base

  const doneCount = Math.floor(opts.elapsedMs / STEP_MS)
  return {
    ...base,
    status: 'processing',
    report: null,
    claim_input: null,
    letters: {},
    progress: steps.map((s, i) => {
      const finished = s.status === 'skipped' ? 'skipped' : 'done'
      if (i < doneCount) return { ...s, status: finished }
      if (i === doneCount) return { ...s, status: 'running', detail: null }
      return { ...s, status: 'pending', detail: null }
    }),
  }
}

function failedClaim(sampleId: string, id: string): Claim {
  const fixture = fixtureFor(sampleId)
  const steps = fixture.progress.length ? fixture.progress : DEFAULT_STEPS
  return {
    ...fixture,
    id,
    status: 'failed',
    report: null,
    claim_input: null,
    letters: {},
    error: "We couldn't read the policy schedule. The scan may be too blurry, or a page may be missing.",
    progress: steps.map((s, i) => {
      if (i === 0) return { ...s, status: 'done' }
      if (i === 1) return { ...s, status: 'failed', detail: 'Policy schedule unreadable' }
      return { ...s, status: 'pending', detail: null }
    }),
  }
}

async function getClaim(id: string): Promise<Claim> {
  await delay(140)
  const state = loadState()
  if (state.deleted.includes(id)) throw new ApiError(404, "We couldn't find that claim.")

  const record = state.records.find((r) => r.id === id)
  if (record) {
    return materialize(record.sampleId, {
      id: record.id,
      createdAt: new Date(record.createdAt).toISOString(),
      source: record.source,
      documents: record.documents,
      elapsedMs: Date.now() - record.createdAt,
      keepFixtureLetters: false,
    })
  }

  const live = /^mock-live-(s\d+)$/i.exec(id)
  if (live) {
    if (!liveStarts.has(id)) liveStarts.set(id, Date.now())
    const started = liveStarts.get(id) ?? Date.now()
    return materialize(live[1], {
      id,
      createdAt: new Date(started).toISOString(),
      source: 'sample',
      elapsedMs: Date.now() - started,
      keepFixtureLetters: false,
    })
  }

  const failed = /^mock-failed-(s\d+)$/i.exec(id)
  if (failed) return failedClaim(failed[1], id)

  const sampleId = sampleIdForClaimId(id)
  if (sampleId) {
    const fixture = fixtureFor(sampleId)
    return materialize(sampleId, {
      id,
      createdAt: fixture.created_at,
      source: fixture.source,
      elapsedMs: Number.POSITIVE_INFINITY,
      keepFixtureLetters: true,
    })
  }

  throw new ApiError(404, "We couldn't find that claim.")
}

export const mockApi: ClaimBackApi = {
  async health() {
    await delay(100)
    return { ...(healthJson as Health), llm: llmMode() }
  },

  async wordings() {
    await delay(120)
    return clone(wordingsJson as PolicyWording[])
  },

  async samples() {
    await delay(180)
    return clone(samplesJson as unknown as SampleSummary[]).filter((s) => fixtures.has(s.id.toUpperCase()))
  },

  async createSampleClaim(sampleId) {
    await delay(300)
    const key = sampleId.toUpperCase()
    const fixture = fixtures.get(key)
    if (!fixture) throw new ApiError(404, `Sample ${sampleId} isn't available.`)
    const state = loadState()
    const record: MockRecord = { id: fixture.id, sampleId: key, source: 'sample', createdAt: Date.now() }
    const letters = { ...state.letters }
    delete letters[fixture.id]
    saveState({
      records: [...state.records.filter((r) => r.id !== fixture.id), record],
      deleted: state.deleted.filter((d) => d !== fixture.id),
      letters,
    })
    return getClaim(record.id)
  },

  async createClaim(upload) {
    await delay(600)
    if (llmMode() === 'offline') {
      throw new ApiError(
        503,
        "Reading your own documents needs Claude on Amazon Bedrock, which isn't switched on in this build.",
      )
    }
    const doc = (kind: ClaimDocument['kind'], file: File): ClaimDocument => ({
      kind,
      filename: file.name,
      content_type: file.type || 'application/octet-stream',
    })
    const documents = [
      doc('policy_schedule', upload.policy_schedule),
      doc('hospital_bill', upload.hospital_bill),
      doc('insurer_letter', upload.insurer_letter),
      ...(upload.discharge_summary ? [doc('discharge_summary', upload.discharge_summary)] : []),
    ]
    const state = loadState()
    const record: MockRecord = {
      id: `upload-${Date.now().toString(36)}`,
      sampleId: 'S1',
      source: 'upload',
      createdAt: Date.now(),
      documents,
    }
    saveState({ ...state, records: [...state.records, record] })
    return getClaim(record.id)
  },

  async listClaims() {
    await delay(200)
    const state = loadState()
    const fixtureIds = [...fixtures.values()].map((c) => c.id)
    const ids = [...new Set([...state.records.map((r) => r.id), ...fixtureIds])].filter(
      (id) => !state.deleted.includes(id),
    )
    const claims = await Promise.all(ids.map((id) => getClaim(id).catch(() => null)))
    return claims
      .filter((c): c is Claim => c !== null)
      .map<ClaimSummary>((c) => ({
        id: c.id,
        created_at: c.created_at,
        status: c.status,
        source: c.source,
        sample_id: c.sample_id,
        title: c.title,
        totals: c.report?.totals ?? null,
      }))
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
  },

  getClaim,

  async deleteClaim(id) {
    await delay(220)
    const state = loadState()
    const letters = { ...state.letters }
    delete letters[id]
    saveState({
      records: state.records.filter((r) => r.id !== id),
      deleted: [...new Set([...state.deleted, id])],
      letters,
    })
  },

  async createLetter(claimId, kind) {
    const claim = await getClaim(claimId)
    if (claim.status !== 'complete' || !claim.report) {
      throw new ApiError(409, "Your report isn't ready yet.")
    }
    await delay(1100)
    const record = loadState().records.find((r) => r.id === claimId)
    const sampleId = record?.sampleId ?? sampleIdForClaimId(claimId)
    const exported = sampleId ? fixtures.get(sampleId)?.letters[kind] : undefined
    const letter = exported ? clone(exported) : buildMockLetter(claim, kind)
    const state = loadState()
    saveState({
      ...state,
      letters: { ...state.letters, [claimId]: { ...state.letters[claimId], [kind]: letter } },
    })
    return letter
  },
}

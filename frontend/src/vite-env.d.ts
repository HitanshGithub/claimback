/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of a deployed ClaimBack API, e.g. https://api.example.com. Empty for same origin / dev proxy. */
  readonly VITE_API_BASE?: string
  /** "1" serves fixtures from src/mocks instead of the network. */
  readonly VITE_MOCK?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

# ClaimBack frontend

The web app for ClaimBack. It shows a family whether their insurer was allowed to cut or reject a health claim, with the exact clause for every point, and drafts the complaint letter.

Vite + React 19 + TypeScript (strict) + Tailwind CSS v4 + React Router. Icons come from `lucide-react`, and the fonts are Fraunces (display) and Inter (UI) via `@fontsource`.

## Run it

Requires Node 24 and npm 11.

```bash
npm install
npm run dev          # http://localhost:5173, /api is proxied to http://127.0.0.1:8000
```

The FastAPI backend (`../backend`) must be running on port 8000 for `npm run dev`.

### Mock mode (no backend needed)

```bash
npm run dev:mock     # works on Windows, macOS and Linux (vite --mode mock reads .env.mock)
```

Or set the variable yourself:

| Shell | Command |
|---|---|
| macOS / Linux / Git Bash | `VITE_MOCK=1 npm run dev` |
| Windows cmd | `set VITE_MOCK=1 && npm run dev` |
| PowerShell | `$env:VITE_MOCK=1; npm run dev` |

In mock mode the API client serves the fixtures in `src/mocks/`, which are real API responses exported by the backend:

- `POST /api/claims/sample` returns that sample's claim (`sample-s1` … `sample-s5`), and its progress steps flip to done about 500 ms apart.
- Letters, new claims and deletions persist in `localStorage`.
- Uploads return a 503 because `health.json` says `llm: "offline"`. Add `?mock_llm=bedrock` to any URL to pretend Claude on Bedrock is on and try the upload flow.

Useful demo URLs:

| URL | Shows |
|---|---|
| `/claims/sample-s1` | Consumables deductions: ₹11,600 you can challenge |
| `/claims/sample-s2` | Proportionate deduction, with the "same bill under Star Health" callout |
| `/claims/sample-s3` | Rejected claim (non-disclosure after the moratorium) |
| `/claims/sample-s4` | "Ask your insurer to justify ₹60,000" |
| `/claims/sample-s5` | Nothing to challenge |
| `/claims/sample-s1?finding=D01` | Report with a finding's detail drawer open |
| `/claims/sample-s1?letter=grievance#letter` | Report with the complaint letter open |
| `/claims/mock-live-s1` | Processing checklist (runs from page load) |
| `/claims/mock-failed-s1` | Failed claim |

## Build

```bash
npm run build        # tsc -b && vite build -> dist/
npm run build:mock   # static demo build that serves fixtures, no backend
npm run lint         # oxlint
npm run typecheck
```

Set `VITE_API_BASE` (for example `https://api.example.com`, with no trailing slash) when the API is on another origin. Leave it empty for a same-origin deployment or the dev proxy. See `.env.example`.

`dist/` is a single-page app, so the host must rewrite unknown paths to `/index.html` (for example CloudFront or Amplify rewrites, or a 404 fallback to `index.html`).

## How it talks to the API

- `src/api/types.ts` mirrors `backend/claimback/models.py` and `backend/API.md` field for field.
- `src/api/client.ts` is the typed client. It sends `X-ClaimBack-Owner` on every request with a random id stored in `localStorage` under `claimback.owner`. Document links add `?o=<id>` because a new tab can't send headers.
- `src/api/mock.ts` is the mock implementation. It is loaded only when `VITE_MOCK=1`.
- `GET /api/claims/{id}` is polled every second while `status === "processing"`.
- Report text from the engine ("Rs 1,39,700") is shown as "₹1,39,700". All money uses `Intl.NumberFormat('en-IN')` with tabular numerals, and dates look like "14 Aug 2026".

## Structure

```
src/
  api/         types.ts, client.ts, mock.ts
  mocks/       claim-S1..S5.json, samples.json, wordings.json, health.json, letter-template.ts
  lib/         formatters, verdict colours and labels, report helpers, hooks
  components/  Layout, Sheet (drawer / bottom sheet), CitationCard, Dropzone, ProgressChecklist, SampleClaims, ...
  components/report/  SummaryHeader, FindingsPaper ("Your bill, checked"), FindingDetail, ComputedFacts,
                      Sections (checks, alternate wordings, similar decisions, next steps, documents), LetterSection, ReportView
  pages/       HomePage, NewClaimPage, ClaimPage, ClaimsPage, NotFoundPage
```

## Accessibility and motion

- Rows, filter tabs (arrow keys, Home and End) and the drawer all work from the keyboard. The drawer traps focus, closes on Escape and returns focus to the row.
- Verdicts always pair colour with an icon and a label. The verdict fill colours were checked as a colour-blind-safe set, and text uses darker steps that pass WCAG AA.
- Count-up, the progress checklist and the drawer slide are all turned off under `prefers-reduced-motion`.

## Screenshots

See `screenshots/`. They were captured from mock mode with headless Chrome at 1440 px and at a true 400 px mobile viewport.

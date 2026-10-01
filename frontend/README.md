# TrustLens AI — Frontend

Evidence-first media review UI built with Next.js, React, and TypeScript.

## Run locally

1. Start the TrustLens FastAPI backend at `http://localhost:8000`.
2. Copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_URL` if the backend runs elsewhere.
3. Install frontend dependencies with `npm install`.
4. Start the frontend with `npm run dev`.
5. Open `http://localhost:3000`.

The Gemini API key must remain in the backend environment; the frontend does not read or store it.

## API expectations

The UI expects these backend routes from T1SPEC:

- `GET /api/health` — status plus optional `gemini_configured` boolean.
- `POST /api/analyze` — multipart form upload using the field name `file`. Return a completed analysis directly, or return an analysis `id`/`analysis_id` and a queued/processing status.
- `GET /api/analyze/{id}` — return processing status/stage or the completed analysis. The UI polls this route while the job is active.
- `GET /api/analyze/{id}/report.pdf` — optional printable PDF export.

Completed analysis fields accepted by the UI include `trust_state`/`state`, `summary`, `explanation`, `evidence`, `conflicts`, `limitations`, `timeline`/`events`, `metadata`, `provenance`/`c2pa`, and `media_info`. Evidence items may include `source`, `type`, `category`, `timestamp`, `observation`, `strength`, and `uncertainty`.

Allow CORS from `http://localhost:3000` in FastAPI. The frontend does not invent a result when the backend is unavailable; backend/API errors are displayed to the user.

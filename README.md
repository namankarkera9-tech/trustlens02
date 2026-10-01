# TrustLens AI

TrustLens is an evidence-first local prototype for inspecting suspicious images and short videos. It combines file metadata, C2PA provenance (when available), FFmpeg/OpenCV media observations, and structured observations from the **real Google Gemini API**. A deterministic fusion layer produces one of the three states from the spec. Gemini does not determine the final state.

> Missing metadata or C2PA is not proof of manipulation. Gemini observations are not calibrated probabilities. TrustLens communicates uncertainty and is not an authenticity certification service.

## Project layout

- `T1SPEC.md` — single source of truth for the project requirements.
- `frontend/` — Next.js, React, TypeScript frontend.
- `backend/` — FastAPI, Pydantic, SQLite, media and Gemini services.
- `data/samples/` — instructions for adding rights-cleared local demo samples; uploaded/raw sample media is gitignored.

## Requirements

- Node.js 20+ (Next.js 16 is used; use a current Node 20 LTS patch or Node 22).
- Python 3.9+ (backend uses Pydantic v2).
- FFmpeg (`ffmpeg` and `ffprobe`) is needed for the specified primary video-processing path, video metadata, and frame extraction. OpenCV is installed and provides a bounded validation/sampling fallback when FFmpeg is absent.
- ExifTool is recommended for richer image/video metadata.
- `c2patool` is optional; when absent, provenance is explicitly reported as unavailable.
- A Google Gemini API key and selected model are required for real Gemini observations. Without them the API explicitly reports Gemini as not configured and returns an insufficient result; it never substitutes fake AI output.

On macOS, install command-line media tools with your preferred package manager. For example, if Homebrew is installed, `brew install ffmpeg exiftool` installs the first two. Install a C2PA tool separately if desired. Without these command-line tools the backend reports metadata/provenance unavailability and uses OpenCV for video; it does not pretend those checks succeeded.

## Configure the real Gemini call

Copy `backend/.env.example` to `backend/.env`, then set the real `GEMINI_API_KEY` and `GEMINI_MODEL` in that backend-only file. Do not put the key in a frontend environment variable or commit `backend/.env`.

Set `FRONTEND_URL` and `BACKEND_URL` there if using different local ports. `MAX_UPLOAD_BYTES`, `MAX_VIDEO_SECONDS`, and `DATABASE_PATH` can be adjusted for local resource limits.

## Run locally

Terminal 1 — backend:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# From repository root, copy backend/.env.example to backend/.env and configure it.
uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend:

```sh
cd frontend
npm install
# Optional: copy .env.example to .env.local; default API URL is http://localhost:8000.
npm run dev
```

Open `http://localhost:3000`. FastAPI docs are at `http://localhost:8000/docs` and its health endpoint at `http://localhost:8000/api/health`.

## What happens during analysis

1. The API validates the extension, declared MIME type, size, and media readability. The upload is placed in a temporary file and deleted after analysis.
2. Metadata and C2PA are inspected independently. Missing tools/results remain explicit, non-negative observations.
3. Images are inspected directly; videos are probed and at most eight timestamped frames are extracted. Video duration defaults to a 90 second maximum.
4. If configured, `google-genai` makes a server-side Gemini request using structured output. Videos are sent as timestamped sampled frames; the model name comes from `GEMINI_MODEL`.
5. The normalized evidence records go through deterministic fusion. Conflicts, missing sources, and limitations are retained.
6. The result is persisted in SQLite without retaining raw uploaded media. JSON, evidence, timeline, and printable PDF endpoints are available.

## API

See [docs/API_SPEC.md](docs/API_SPEC.md) for routes, payload shape, and error behavior.

## Tests

From `backend/`, activate the virtual environment and run:

```sh
python -m pytest -q
```

For Python analysis/runtime verification use that same backend environment. Frontend checks from `frontend/`:

```sh
npm run lint
npx tsc --noEmit
npm run build
```

See [docs/TEST_PLAN.md](docs/TEST_PLAN.md) for integration/manual checks and external-tool cases.

## Demo media

No media is manufactured or assigned an expected verdict. Add only rights-cleared examples locally and document their known context and limitations. Follow the guidance in [data/samples/README.md](data/samples/README.md). Real sample files are ignored by Git to avoid accidentally committing private media.

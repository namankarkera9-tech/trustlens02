# TrustLens local API contract

Base URL: `http://localhost:8000`. JSON responses use UTF-8. Upload `POST` requests use `multipart/form-data`. FastAPI interactive docs are served at `/docs`.

## `GET /api/health`

Safe backend status. The API key is never included.

```json
{
  "status": "ok",
  "gemini_configured": false,
  "gemini_model": null
}
```

`gemini_configured` is true only when both backend-only `GEMINI_API_KEY` and `GEMINI_MODEL` are set.

## `POST /api/analyze`

Form field: `file` (one image or short video). Supported extensions: JPG/JPEG, PNG, WEBP, GIF, MP4, MOV, M4V, WEBM. Default size limit is 100 MiB; videos default to a 90-second duration limit. The backend validates declared content type, decodes the media, and stores the media only in a temporary file while the analysis runs.

Initial response:

```json
{
  "id": "<uuid>",
  "analysis_id": "<uuid>",
  "status": "queued",
  "stage": "queued",
  "progress": 0,
  "message": "Upload validated. Analysis has been queued."
}
```

The frontend polls `GET /api/analyze/{id}`. Upload validation errors are JSON `detail` values with standard HTTP status codes (415 unsupported/mismatched type, 413 size/dimension limit, 422 empty/corrupt media). Missing required fields use FastAPI validation responses.

## `GET /api/analyze/{id}`

While running, returns `id`, `status`, `stage`, `progress`, `filename`, and `content_type`. Terminal failure returns `status: "failed"` and a sanitized error message. On success, returns the complete result below.

## Completed result

```json
{
  "id": "<uuid>",
  "status": "completed",
  "stage": "complete",
  "progress": 100,
  "filename": "upload.png",
  "content_type": "image/png",
  "media_kind": "image",
  "trust_state": "INSUFFICIENT / CONFLICTING",
  "state": "INSUFFICIENT / CONFLICTING",
  "summary": "...",
  "explanation": "...",
  "evidence": [
    {
      "id": "<uuid>",
      "source": "metadata",
      "type": "metadata_observation",
      "category": "metadata",
      "timestamp": null,
      "observation": "...",
      "value": "...",
      "strength": "informational",
      "uncertainty": "low",
      "supporting_data": {}
    }
  ],
  "conflicts": [],
  "limitations": [],
  "timeline": [],
  "metadata": {},
  "metadata_tool": "Pillow",
  "provenance": {"status": "inspection_unavailable"},
  "media_info": {"kind": "image", "width": 1200, "height": 800},
  "gemini": {
    "provider": "Google Gemini API",
    "configured": false,
    "model": null,
    "status": "not_configured",
    "observations": [],
    "limitations": ["..."]
  },
  "fusion": {}
}
```

Exactly three `trust_state` values are emitted: `CONSISTENT EVIDENCE`, `INSUFFICIENT / CONFLICTING`, or `HIGH MANIPULATION RISK`. The fusion engine requires independent evidence-source agreement for a non-uncertain state. Tool failures and absent metadata/C2PA do not themselves indicate manipulation. Gemini failures are reported as limitations and do not produce fabricated observations.

Evidence sources: `metadata`, `c2pa`, `ffmpeg`, `opencv`, `gemini`. The timeline contains only evidence with an observed timestamp, primarily sampled video frames.

## `GET /api/analyze/{id}/evidence`

Returns `{ "id": "...", "evidence": [...] }`. Before completion returns 409; unknown IDs return 404.

## `GET /api/analyze/{id}/timeline`

Returns `{ "id": "...", "timeline": [...] }`. Before completion returns 409; unknown IDs return 404.

## `GET /api/analyze/{id}/report`

Returns the complete result JSON after analysis completion.

## `GET /api/analyze/{id}/report.pdf`

Returns a downloadable `application/pdf` report. If ReportLab is unavailable, returns 503.

## CORS

The backend allows the comma-separated origins in `FRONTEND_URL` (default `http://localhost:3000`), GET/POST/OPTIONS, and `Content-Type`/`Accept` headers. No credentialed CORS is enabled.

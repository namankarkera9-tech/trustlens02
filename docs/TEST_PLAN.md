# TrustLens MVP test plan

## Automated backend checks

From `backend/` with the backend venv active: `python -m pytest -q`.

- Fusion state thresholds: risk needs two independent concern sources; single-source concern stays insufficient; contradictory signals remain conflicting; consistency needs two independent sources.
- Health never returns the API key.
- Unsupported upload is rejected.
- Valid generated in-memory PNG is accepted, persisted as a result, returns evidence, and reports Gemini as not configured when no key is provided.

The integration image is generated in memory during tests; it is not a pre-labelled demo fixture or a fake model result.

## Manual tool matrix

| Capability | Available | Missing/unavailable behavior |
| --- | --- | --- |
| ExifTool | Extract useful grouped metadata | Pillow handles common image dimensions/EXIF; video metadata may be limited |
| FFmpeg/ffprobe | Probe streams and extract up to 8 time-sampled frames | OpenCV attempts video validation, probe, and frame sampling |
| OpenCV | Image statistics / conservative sampled-frame difference observations | Explicit processing-unavailable evidence |
| c2patool | Inspect manifest and validation result | Explicit provenance inspection unavailable; no fake C2PA status |
| Gemini configured | Real structured Google GenAI API observations | On absent keys, explicit `not_configured`; on runtime exception, sanitized unavailable/error result, never a fake observation |
| ReportLab | Download PDF report | 503 on PDF route; browser print remains available |

## Upload checks

- Valid PNG/JPEG/WebP/GIF image.
- Valid short MP4/MOV/M4V/WEBM with FFmpeg or OpenCV installed.
- Unsupported extension and MIME/extension mismatch.
- Empty file, corrupt image/video, excessive byte size, huge raster dimensions, and overlong video.
- Check temporary uploaded media is removed on success and failure; no raw media bytes are written to SQLite.

## Gemini checks (requires user-provided credentials)

- Set `GEMINI_API_KEY` and `GEMINI_MODEL` in backend `.env`; `/api/health` reports configured/model only.
- Submit an image, then a short video. Confirm one real `client.models.generate_content` call, valid schema output, and Gemini evidence enters fusion.
- Verify invalid key, quota/network error, malformed response, and unsupported model remain handled without exposing the key.
- Never commit or print the actual key in test output.

## Browser end-to-end checks

- Backend online/offline indicator updates.
- Drag/drop and browse select; verify preview, size/type, remove, and extension/size validation.
- Submit image and video. Confirm polling and stage labels correspond to API-reported processing.
- Verify all three states via suitable evidence payloads; ensure metadata/provenance missing does not render a fake manipulation claim.
- Inspect source-separated evidence, conflict/limitations, video frame markers and seeking, responsive mobile navigation, print layout, and the PDF route.

## Remaining human acceptance

Provide three rights-cleared, provenance-documented local media examples (normal context, known manipulation, and ambiguous/conflicting context) and use the exact backend dependencies/tools intended for the demonstration. Do not force a desired state for any fixture; note the observed output and limitations.

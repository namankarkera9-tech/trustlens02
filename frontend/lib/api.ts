import type { AnalysisResult, EvidenceItem, TimelineEvent, TrustState } from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const ACTIVE_STATUSES = new Set(["queued", "pending", "processing", "running", "started", "in_progress"]);

function asObject(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function first(...values: unknown[]): unknown {
  return values.find((value) => value !== undefined && value !== null && value !== "");
}

function asStrings(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === "string" && value) return [value];
  return [];
}

function toTrustState(value: unknown): TrustState {
  const normalized = String(value ?? "").toUpperCase().replace(/[_-]+/g, " ").trim();
  if (normalized.includes("HIGH") || normalized.includes("MANIPULATION") || normalized.includes("RISK")) {
    return "HIGH MANIPULATION RISK";
  }
  if (normalized.includes("CONSISTENT")) return "CONSISTENT EVIDENCE";
  return "INSUFFICIENT / CONFLICTING";
}

function normalizeEvidence(value: unknown): EvidenceItem[] {
  if (Array.isArray(value)) return value.map((item) => asObject(item) as EvidenceItem);
  const object = asObject(value);
  return Object.entries(object).map(([key, item]) => ({
    source: key,
    observation: typeof item === "string" ? item : undefined,
    value: item,
  }));
}

function normalizeTimeline(value: unknown, evidence: EvidenceItem[]): TimelineEvent[] {
  const items = Array.isArray(value) ? value : evidence;
  return items.flatMap((item, index) => {
    const event = asObject(item);
    const timestamp = Number(first(event.timestamp, event.time, event.seconds));
    if (!Number.isFinite(timestamp)) return [];
    return [{
      id: String(first(event.id, `event-${index}`)),
      timestamp,
      source: String(first(event.source, "Evidence")),
      category: String(first(event.category, "observation")),
      title: String(first(event.title, event.type, event.category, "Evidence marker")),
      observation: String(first(event.observation, event.description, "Evidence recorded at this moment.")),
      strength: String(first(event.strength, "informational")),
    }];
  });
}

export function normalizeAnalysis(payload: unknown, fallback: { id?: string; filename: string; contentType?: string }): AnalysisResult {
  const root = asObject(payload);
  const nested = asObject(first(root.result, root.analysis, root.data, root));
  const evidence = normalizeEvidence(first(nested.evidence, nested.evidence_records, nested.observations, []));
  const fusion = asObject(first(nested.fusion, nested.fusion_result, nested.result));
  const explanationObject = asObject(nested.explanation);
  const metadata = asObject(first(nested.metadata, nested.metadata_summary, {}));
  const provenanceValue = first(nested.provenance, nested.c2pa, nested.provenance_summary, null);
  const mediaInfo = asObject(first(nested.media_info, nested.media, nested.video_info, {}));
  const gemini = asObject(first(nested.gemini, nested.gemini_analysis, {}));
  const report = asObject(nested.report);
  const stateValue = first(
    nested.trust_state,
    nested.state,
    nested.verdict,
    nested.status_label,
    fusion.trust_state,
    fusion.state,
  );
  const explanation = String(first(
    explanationObject.summary,
    explanationObject.explanation,
    nested.explanation,
    nested.summary,
    fusion.explanation,
    "The analysis completed without a narrative explanation. Review the evidence and limitations below.",
  ));

  return {
    id: String(first(nested.id, nested.analysis_id, fallback.id, "analysis")),
    filename: String(first(nested.filename, nested.file_name, report.filename, fallback.filename)),
    contentType: fallback.contentType,
    mediaKind: String(first(nested.media_kind, mediaInfo.kind, "" )).toLowerCase().includes("video")
      || Boolean(fallback.contentType?.startsWith("video/")) ? "video" : "image",
    state: toTrustState(stateValue),
    summary: String(first(nested.summary, fusion.summary, explanationObject.headline, explanation)),
    explanation,
    evidence,
    conflicts: asStrings(first(nested.conflicts, fusion.conflicts, nested.evidence_conflicts, [])),
    limitations: asStrings(first(nested.limitations, explanationObject.limitations, [])),
    timeline: normalizeTimeline(first(nested.timeline, nested.events, nested.timeline_events), evidence),
    metadata,
    provenance: provenanceValue as Record<string, unknown> | string | null,
    mediaInfo,
    gemini,
    raw: { ...root, ...nested },
  };
}

async function readResponse(response: Response): Promise<Record<string, unknown>> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = asObject(body).detail;
    throw new Error(String(first(detail, asObject(body).message, `Request failed (${response.status})`)));
  }
  return asObject(body);
}

function getStatus(body: Record<string, unknown>): string {
  const data = asObject(first(body.result, body.analysis, body.data, body));
  return String(first(data.status, body.status, "")).toLowerCase().replaceAll(" ", "_");
}

export async function analyzeMedia(file: File, onStatus: (status: string, message?: string) => void): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file);
  onStatus("uploading", "Sending the selected file to the local analysis service.");

  const initial = await fetch(`${API_URL}/api/analyze`, {
    method: "POST",
    body: form,
  }).then(readResponse);
  const initialStatus = getStatus(initial);
  const initialData = asObject(first(initial.result, initial.analysis, initial.data, initial));
  const id = String(first(initialData.id, initialData.analysis_id, initial.id, initial.analysis_id, ""));

  if (!ACTIVE_STATUSES.has(initialStatus) && (initialStatus === "failed" || initialStatus === "error")) {
    throw new Error(String(first(initialData.message, initialData.error, "The analysis service could not complete this file.")));
  }
  if (!ACTIVE_STATUSES.has(initialStatus) && (initial.trust_state || initial.state || initialData.trust_state || initialData.state || initialData.evidence)) {
    onStatus("complete", "Analysis complete.");
    return normalizeAnalysis(initial, { id, filename: file.name, contentType: file.type });
  }
  if (!id) {
    throw new Error("The analysis service accepted the upload but did not return a result or analysis ID.");
  }

  const startedAt = Date.now();
  while (Date.now() - startedAt < 5 * 60 * 1000) {
    const statusResponse = await fetch(`${API_URL}/api/analyze/${encodeURIComponent(id)}`, { cache: "no-store" }).then(readResponse);
    const status = getStatus(statusResponse);
    const statusData = asObject(first(statusResponse.result, statusResponse.analysis, statusResponse.data, statusResponse));
    const message = first(statusData.message, statusData.stage, statusResponse.message);
    onStatus(status || "processing", message ? String(message) : undefined);

    if (["failed", "error", "cancelled"].includes(status)) {
      throw new Error(String(first(statusData.error, statusData.message, "The analysis service could not complete this file.")));
    }
    if (!ACTIVE_STATUSES.has(status)) {
      const hasResult = statusData.trust_state || statusData.state || statusData.evidence || statusData.result;
      if (hasResult) {
        onStatus("complete", "Analysis complete.");
        return normalizeAnalysis(statusResponse, { id, filename: file.name, contentType: file.type });
      }
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1400));
  }
  throw new Error("Analysis is taking longer than expected. Check the backend and try again.");
}

export function analysisEndpoint(path: string): string {
  return `${API_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

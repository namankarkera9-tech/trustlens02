export type TrustState =
  | "CONSISTENT EVIDENCE"
  | "INSUFFICIENT / CONFLICTING"
  | "HIGH MANIPULATION RISK";

export type EvidenceStrength = "weak" | "moderate" | "strong" | "informational" | string;

export interface EvidenceItem {
  id?: string;
  source?: string;
  type?: string;
  category?: string;
  timestamp?: number | string | null;
  observation?: string;
  value?: unknown;
  strength?: EvidenceStrength;
  uncertainty?: string;
  supporting_data?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface TimelineEvent {
  id?: string;
  timestamp: number;
  source?: string;
  category?: string;
  title?: string;
  observation?: string;
  strength?: EvidenceStrength;
}

export interface AnalysisResult {
  id: string;
  filename: string;
  contentType?: string;
  mediaKind: "image" | "video";
  state: TrustState;
  summary: string;
  explanation: string;
  evidence: EvidenceItem[];
  conflicts: string[];
  limitations: string[];
  timeline: TimelineEvent[];
  metadata: Record<string, unknown>;
  provenance: Record<string, unknown> | string | null;
  mediaInfo: Record<string, unknown>;
  gemini: Record<string, unknown>;
  raw: Record<string, unknown>;
}

export interface ProcessingStatus {
  status?: string;
  stage?: string;
  message?: string;
  progress?: number;
}

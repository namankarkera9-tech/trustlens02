"use client";

import { useMemo } from "react";
import { AlertTriangle, ArrowDownToLine, BadgeCheck, CircleHelp, FileText, Info, Printer, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";
import { analysisEndpoint } from "@/lib/api";
import type { AnalysisResult, EvidenceItem, TrustState } from "@/lib/types";
import { EvidenceTimeline } from "./evidence-timeline";

const SOURCE_ORDER = ["metadata", "c2pa", "ffmpeg", "opencv", "gemini"];
const SOURCE_NAMES: Record<string, string> = {
  metadata: "File metadata",
  c2pa: "Content provenance",
  ffmpeg: "Media properties",
  opencv: "Frame analysis",
  gemini: "Gemini observations",
};

function stateCopy(state: TrustState, hasConflicts: boolean) {
  if (state === "CONSISTENT EVIDENCE") return {
    icon: <ShieldCheck size={22} />,
    eyebrow: "EVIDENCE ALIGNMENT",
    description: "Available signals are broadly consistent. This is not a guarantee of authenticity; review the source and context before relying on the media.",
    className: "state-consistent",
  };
  if (state === "HIGH MANIPULATION RISK") return {
    icon: <ShieldAlert size={22} />,
    eyebrow: "MULTIPLE CONCERNING SIGNALS",
    description: "Several evidence signals indicate elevated manipulation risk. Treat this media cautiously and verify it through independent sources.",
    className: "state-risk",
  };
  return {
    icon: <CircleHelp size={22} />,
    eyebrow: "UNCERTAINTY REMAINS",
    description: hasConflicts
      ? "Evidence is incomplete and some sources disagree. TrustLens preserves that conflict rather than forcing a verdict."
      : "Evidence is incomplete. No explicit source conflicts were reported, but there is not enough independent evidence for a well-supported conclusion.",
    className: "state-uncertain",
  };
}

function sourceFor(item: EvidenceItem) {
  return String(item.source ?? item.category ?? "other").toLowerCase();
}

function labelize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function displayValue(value: unknown): string {
  if (value === undefined || value === null || value === "") return "Not available";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function metadataRows(metadata: Record<string, unknown>) {
  const rows: [string, string][] = [];
  for (const [key, rawValue] of Object.entries(metadata)) {
    if (rawValue === null || rawValue === undefined || rawValue === "") continue;
    if (rawValue && typeof rawValue === "object" && !Array.isArray(rawValue)) {
      for (const [nestedKey, nestedValue] of Object.entries(rawValue as Record<string, unknown>)) {
        if (nestedValue !== null && nestedValue !== undefined && nestedValue !== "") rows.push([`${key} · ${nestedKey}`, displayValue(nestedValue)]);
      }
    } else {
      rows.push([key, displayValue(rawValue)]);
    }
  }
  return rows.slice(0, 12);
}

function EvidenceCard({ source, items, emptyMessage }: { source: string; items: EvidenceItem[]; emptyMessage?: string }) {
  return (
    <article className="evidence-source-card">
      <div className="source-card-top">
        <div className={`source-symbol source-${source}`}>
          {source === "gemini" ? <Sparkles size={16} /> : source === "c2pa" ? <BadgeCheck size={16} /> : source === "metadata" ? <FileText size={16} /> : <Info size={16} />}
        </div>
        <div className="source-title"><strong>{SOURCE_NAMES[source] ?? labelize(source)}</strong><span>{items.length ? `${items.length} ${items.length === 1 ? "observation" : "observations"}` : "No data returned"}</span></div>
        <span className={`availability-dot${items.length ? " is-available" : ""}`} />
      </div>
      {items.length ? (
        <ul className="evidence-items">
          {items.slice(0, 4).map((item, index) => (
            <li key={item.id ?? `${source}-${index}`}>
              <span className="evidence-bullet" />
              <div>
                <p>{String(item.observation ?? item.value ?? item.type ?? "Evidence item returned without a description.")}</p>
                <div className="evidence-meta">
                  {item.strength && <span>{labelize(String(item.strength))} signal</span>}
                  {item.uncertainty && <span>{labelize(String(item.uncertainty))} uncertainty</span>}
                  {item.timestamp !== undefined && item.timestamp !== null && <span>{Number(item.timestamp).toFixed(1)}s</span>}
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="source-unavailable">{emptyMessage ?? "No observations were reported for this source. Missing data is not evidence of manipulation."}</p>
      )}
    </article>
  );
}

export function ResultDashboard({ result, file, onNewAnalysis }: { result: AnalysisResult; file: File | null; onNewAnalysis: () => void }) {
  const state = stateCopy(result.state, result.conflicts.length > 0);
  const grouped = useMemo(() => {
    const groups: Record<string, EvidenceItem[]> = {};
    for (const item of result.evidence) {
      const source = sourceFor(item);
      const key = SOURCE_ORDER.includes(source) ? source : "other";
      groups[key] = [...(groups[key] ?? []), item];
    }
    return groups;
  }, [result.evidence]);
  const rows = metadataRows(result.metadata);
  const provenance = typeof result.provenance === "string" ? result.provenance : result.provenance ? JSON.stringify(result.provenance) : "No provenance result returned";
  const pdfUrl = result.id && result.id !== "analysis" ? analysisEndpoint(`/api/analyze/${encodeURIComponent(result.id)}/report.pdf`) : null;

  return (
    <div className="result-dashboard" id="results">
      <div className="result-toolbar screen-only">
        <div><span className="result-ready-dot" /> ANALYSIS COMPLETE <span className="toolbar-divider">/</span> {result.filename}</div>
        <div className="toolbar-actions">
          <button className="button button-secondary button-small" type="button" onClick={() => window.print()}><Printer size={15} /> Print report</button>
          {pdfUrl && <a className="button button-secondary button-small" href={pdfUrl} target="_blank" rel="noreferrer"><ArrowDownToLine size={15} /> Export PDF</a>}
          <button className="button button-primary button-small" type="button" onClick={onNewAnalysis}>New analysis</button>
        </div>
      </div>

      <section className={`state-card ${state.className}`} aria-labelledby="trust-state-title">
        <div className="state-icon">{state.icon}</div>
        <div className="state-copy">
          <div className="eyebrow">{state.eyebrow}</div>
          <h2 id="trust-state-title">{result.state}</h2>
          <p>{state.description}</p>
        </div>
        <div className="state-file"><span>ANALYZED MEDIA</span><strong title={result.filename}>{result.filename}</strong><span>{result.contentType || (result.mediaKind === "video" ? "Video" : "Image")}</span></div>
      </section>

      <div className="summary-grid">
        <section className="dashboard-card explanation-card" aria-labelledby="explanation-title">
          <div className="card-heading">
            <div><div className="eyebrow">WHY THIS RESULT</div><h2 id="explanation-title">Evidence-led explanation</h2></div>
            <div className="card-heading-icon"><Sparkles size={18} /></div>
          </div>
          <p className="explanation-text">{result.explanation}</p>
          <div className="explanation-note"><Info size={15} /><span>{result.summary}</span></div>
        </section>

        <section className="dashboard-card conflict-card" aria-labelledby="conflict-title">
          <div className="card-heading">
            <div><div className="eyebrow">TRANSPARENCY CHECK</div><h2 id="conflict-title">Signals &amp; conflicts</h2></div>
            <div className={`card-heading-icon${result.conflicts.length ? " icon-warning" : ""}`}>{result.conflicts.length ? <AlertTriangle size={18} /> : <ShieldCheck size={18} />}</div>
          </div>
          {result.conflicts.length ? (
            <ul className="conflict-list">{result.conflicts.map((conflict, index) => <li key={`${conflict}-${index}`}><span />{conflict}</li>)}</ul>
          ) : (
            <p className="no-conflicts">No explicit conflicts were reported. The absence of a conflict report does not establish authenticity.</p>
          )}
          {result.limitations.length > 0 && <div className="limitations"><strong>LIMITATIONS</strong>{result.limitations.map((item, index) => <p key={`${item}-${index}`}>{item}</p>)}</div>}
        </section>
      </div>

      <section className="evidence-section" id="evidence">
        <div className="section-heading">
          <div><div className="eyebrow">THE EVIDENCE RECORD</div><h2>What the system observed</h2><p>Evidence from separate sources stays visible—including what could not be checked.</p></div>
          <span className="evidence-total">{result.evidence.length} evidence {result.evidence.length === 1 ? "item" : "items"}</span>
        </div>
        <div className="evidence-grid">
          {SOURCE_ORDER.map((source) => {
            let emptyMessage: string | undefined;
            if (source === "gemini" && !grouped.gemini?.length) {
              emptyMessage = result.gemini.status === "not_configured"
                ? "Gemini was not run because the server-side API key/model are not configured. Add them to backend/.env and restart FastAPI. No AI observations were invented."
                : result.gemini.status === "error"
                  ? String(result.gemini.error ?? "The Gemini request failed, so no AI observations are available for this result. Review the service limitations.")
                  : "Gemini returned no visual observations for this file. Missing AI observations are not evidence of manipulation.";
            } else if (source === "c2pa" && !grouped.c2pa?.length) {
              emptyMessage = `Provenance status: ${String(result.provenance && typeof result.provenance === "object" ? result.provenance.status ?? "unavailable" : "unavailable")}. Missing C2PA is not evidence of manipulation.`;
            }
            return <EvidenceCard key={source} source={source} items={grouped[source] ?? []} emptyMessage={emptyMessage} />;
          })}
          {grouped.other?.length ? <EvidenceCard source="other" items={grouped.other} /> : null}
        </div>
      </section>

      <EvidenceTimeline result={result} file={file} />

      <section className="dashboard-card report-card" id="report" aria-labelledby="report-title">
        <div className="card-heading">
          <div><div className="eyebrow">PORTABLE SUMMARY</div><h2 id="report-title">Trust report</h2><p>A concise record for review and sharing.</p></div>
          <div className="card-heading-actions screen-only"><button className="button button-secondary button-small" type="button" onClick={() => window.print()}><Printer size={15} /> Print</button>{pdfUrl && <a className="button button-secondary button-small" href={pdfUrl} target="_blank" rel="noreferrer"><ArrowDownToLine size={15} /> PDF</a>}</div>
        </div>
        <div className="report-sheet">
          <div className="report-sheet-header"><div className="brand-mark mini-mark"><ShieldCheck size={15} /></div><span>TRUSTLENS <b>/</b> ANALYSIS REPORT</span><span className="report-id">ID {result.id}</span></div>
          <div className="report-state-row"><div><span>TRUSTLENS STATE</span><strong className={state.className}>{result.state}</strong></div><div><span>FILE</span><strong>{result.filename}</strong></div><div><span>MEDIA TYPE</span><strong>{result.contentType || result.mediaKind}</strong></div></div>
          <p className="report-explanation">{result.explanation}</p>
          <div className="report-details-grid">
            <div><h3>Evidence summary</h3><p>{result.evidence.length ? `${result.evidence.length} normalized evidence item(s) returned across ${new Set(result.evidence.map(sourceFor)).size} source(s).` : "No normalized evidence items were returned."}</p></div>
            <div><h3>Conflicts</h3><p>{result.conflicts.length ? result.conflicts.join(" · ") : "No explicit conflicts reported."}</p></div>
            <div><h3>Provenance</h3><p>{provenance}</p></div>
            <div><h3>Limitations</h3><p>{result.limitations.length ? result.limitations.join(" · ") : "No additional limitations were returned."}</p></div>
          </div>
          {rows.length > 0 && <div className="metadata-table"><h3>File metadata</h3>{rows.map(([key, value]) => <div key={key}><span>{labelize(key)}</span><strong>{value}</strong></div>)}</div>}
          <p className="report-footnote">TrustLens provides evidence for human review, not a definitive authenticity determination. Missing metadata or provenance is not proof of manipulation. AI observations are not calibrated probabilities.</p>
        </div>
      </section>
    </div>
  );
}

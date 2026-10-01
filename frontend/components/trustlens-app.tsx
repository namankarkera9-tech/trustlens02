"use client";

import { useEffect, useState } from "react";
import { Activity, ArrowRight, Check, ChevronRight, CircleHelp, FileCheck2, Fingerprint, Menu, ShieldCheck, Sparkles, X } from "lucide-react";
import { analyzeMedia } from "@/lib/api";
import type { AnalysisResult } from "@/lib/types";
import { ResultDashboard } from "./result-dashboard";
import { UploadPanel } from "./upload-panel";

const PIPELINE = [
  { name: "Metadata inspection", keywords: ["metadata", "exif"] },
  { name: "Provenance check", keywords: ["provenance", "c2pa"] },
  { name: "Media processing", keywords: ["media", "ffmpeg", "opencv", "frame"] },
  { name: "Gemini observations", keywords: ["gemini", "ai", "multimodal"] },
  { name: "Evidence fusion", keywords: ["fusion", "evidence", "normalize"] },
];

export function TrustLensApp() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendState, setBackendState] = useState<"checking" | "online" | "offline">("checking");
  const [geminiConfigured, setGeminiConfigured] = useState<boolean | null>(null);
  const [processing, setProcessing] = useState({ stage: "", message: "" });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const apiUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
    const controller = new AbortController();
    fetch(`${apiUrl}/api/health`, { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Backend unavailable");
        return response.json();
      })
      .then((health: { gemini_configured?: boolean }) => {
        setBackendState("online");
        setGeminiConfigured(typeof health.gemini_configured === "boolean" ? health.gemini_configured : null);
      })
      .catch(() => setBackendState("offline"));
    return () => controller.abort();
  }, []);

  async function handleAnalyze(file: File) {
    setSelectedFile(file);
    setBusy(true);
    setError(null);
    setResult(null);
    setProcessing({ stage: "uploading", message: "Sending the selected file to the local analysis service." });
    try {
      const analysis = await analyzeMedia(file, (stage, message) => setProcessing({ stage, message: message ?? "" }));
      setResult(analysis);
      setProcessing({ stage: "complete", message: "Analysis complete." });
      window.setTimeout(() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "An unexpected error interrupted the analysis.");
    } finally {
      setBusy(false);
    }
  }

  function resetAnalysis() {
    setResult(null);
    setSelectedFile(null);
    setError(null);
    setProcessing({ stage: "", message: "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const currentStage = processing.stage.toLowerCase().replaceAll("_", " ");
  const activeStep = PIPELINE.findIndex((step) => step.keywords.some((keyword) => currentStage.includes(keyword)));

  return (
    <div className="app-shell">
      <aside className={`app-sidebar${mobileMenuOpen ? " sidebar-open" : ""}`}>
        <a className="brand" href="#home" onClick={() => setMobileMenuOpen(false)} aria-label="TrustLens home">
          <span className="brand-mark"><ShieldCheck size={19} strokeWidth={2} /></span>
          <span className="brand-name">trustlens<span>AI</span></span>
        </a>
        <div className="sidebar-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          <a className={`side-link${result ? "" : " active"}`} href="#analysis" onClick={() => setMobileMenuOpen(false)}><Activity size={17} /><span>New analysis</span><ChevronRight className="nav-chevron" size={14} /></a>
          <a className={`side-link${result ? " active" : ""}`} href={result ? "#results" : "#how-it-works"} onClick={() => setMobileMenuOpen(false)}><FileCheck2 size={17} /><span>Trust report</span>{result && <ChevronRight className="nav-chevron" size={14} />}</a>
        </nav>
        <div className="sidebar-divider" />
        <div className="sidebar-label">THE TRUSTLENS METHOD</div>
        <div className="sidebar-method">
          <span><Fingerprint size={15} /> Multiple evidence sources</span>
          <span><CircleHelp size={15} /> Uncertainty stays visible</span>
          <span><Sparkles size={15} /> AI is not the verdict</span>
        </div>
        <div className="sidebar-bottom">
          <div className="sidebar-status"><span className={`status-indicator ${backendState}`} /><div><strong>{backendState === "online" ? "Backend connected" : backendState === "checking" ? "Checking backend" : "Backend offline"}</strong><span>{backendState === "online" ? (geminiConfigured === true ? "Gemini configured" : geminiConfigured === false ? "Gemini needs configuration" : "Local analysis service") : backendState === "checking" ? "Connecting to localhost:8000" : "Start FastAPI on port 8000"}</span></div></div>
          <p>TrustLens supports human review. It does not certify media as authentic.</p>
        </div>
        <button className="sidebar-close" type="button" aria-label="Close navigation" onClick={() => setMobileMenuOpen(false)}><X size={18} /></button>
      </aside>

      {mobileMenuOpen && <button className="sidebar-scrim" type="button" aria-label="Close navigation overlay" onClick={() => setMobileMenuOpen(false)} />}

      <div className="main-column" id="home">
        <header className="topbar">
          <button className="mobile-menu-button" type="button" aria-label="Open navigation" onClick={() => setMobileMenuOpen(true)}><Menu size={20} /></button>
          <div className="breadcrumb"><span>Workspace</span><ChevronRight size={13} /><strong>{result ? "Analysis report" : "Media analysis"}</strong></div>
          <div className="topbar-right"><span className={`backend-pill ${backendState}`}><span />{backendState === "online" ? "Local service online" : backendState === "checking" ? "Connecting" : "Service unavailable"}</span><span className="avatar">TL</span></div>
        </header>

        <main className="main-content">
          <section className="page-intro" id="analysis">
            <div>
              <div className="eyebrow intro-eyebrow"><span className="eyebrow-dot" /> TRUST, WITH CONTEXT</div>
              <h1>Look closer.<br /><span>Understand the evidence.</span></h1>
              <p className="intro-copy">Inspect suspicious images and short videos through a transparent, multi-source evidence review.</p>
              <div className="intro-features"><span><Check size={14} /> Provenance-aware</span><span><Check size={14} /> Evidence-first</span><span><Check size={14} /> Uncertainty included</span></div>
            </div>
            <div className="intro-illustration" aria-hidden="true">
              <div className="orbit orbit-one" /><div className="orbit orbit-two" />
              <div className="illustration-core"><ShieldCheck size={39} strokeWidth={1.35} /></div>
              <div className="orbit-node node-top"><Fingerprint size={15} /></div>
              <div className="orbit-node node-right"><Sparkles size={15} /></div>
              <div className="orbit-node node-bottom"><FileCheck2 size={15} /></div>
            </div>
          </section>

          {busy ? (
            <section className="processing-card" aria-live="polite" aria-busy="true">
              <div className="processing-heading"><div className="processing-spinner" /><div><div className="eyebrow">ANALYSIS IN PROGRESS</div><h2>Reviewing your media</h2><p>{processing.message || "The backend is processing your file. This may take a moment."}</p></div></div>
              <div className="processing-pipeline">
                {PIPELINE.map((step, index) => <div className={`processing-step${activeStep === index ? " step-active" : ""}`} key={step.name}><span className="processing-step-icon">{activeStep === index ? <span className="step-pulse" /> : index < activeStep ? <Check size={13} /> : <span>{String(index + 1).padStart(2, "0")}</span>}</span><span>{step.name}</span>{activeStep === index && <span className="step-label">IN PROGRESS</span>}</div>)}
              </div>
              <p className="processing-honesty"><CircleHelp size={14} /> Only stages reported by the analysis service are marked as in progress. No verdict is inferred from upload or model confidence alone.</p>
            </section>
          ) : result ? (
            <ResultDashboard result={result} file={selectedFile} onNewAnalysis={resetAnalysis} />
          ) : (
            <>
              <UploadPanel onAnalyze={handleAnalyze} busy={busy} error={error} />
              <section className="method-section" id="how-it-works">
                <div className="method-heading"><div><div className="eyebrow">A MORE CAREFUL APPROACH</div><h2>Evidence before conclusions</h2></div><a href="#analysis">Start an analysis <ArrowRight size={15} /></a></div>
                <div className="method-steps">
                  <article><span className="method-number">01</span><div className="method-icon"><Fingerprint size={19} /></div><h3>Inspect the file</h3><p>Metadata and provenance are checked alongside the media itself.</p></article>
                  <article><span className="method-number">02</span><div className="method-icon"><Sparkles size={19} /></div><h3>Gather observations</h3><p>Computer vision and Gemini contribute observations—not a final verdict.</p></article>
                  <article><span className="method-number">03</span><div className="method-icon"><ShieldCheck size={19} /></div><h3>Review the evidence</h3><p>Independent signals, conflicts, and unknowns stay visible together.</p></article>
                </div>
              </section>
              <div className="bottom-note"><CircleHelp size={15} /><span>Missing metadata or provenance is not proof of manipulation. Always verify important media at its source.</span></div>
            </>
          )}
        </main>
        <footer className="app-footer"><span>TRUSTLENS AI <span className="footer-divider">·</span> EVIDENCE, NOT CERTAINTY</span><span>LOCAL PROTOTYPE</span></footer>
      </div>
    </div>
  );
}

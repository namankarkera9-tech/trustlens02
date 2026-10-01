"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Clock3, Film, Play, ScanSearch } from "lucide-react";
import type { AnalysisResult, TimelineEvent } from "@/lib/types";

function timestamp(seconds: number) {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  return `${Math.floor(safeSeconds / 60).toString().padStart(2, "0")}:${(safeSeconds % 60).toString().padStart(2, "0")}`;
}

function eventColor(event: TimelineEvent) {
  const strength = String(event.strength ?? "").toLowerCase();
  if (strength.includes("strong")) return "marker-strong";
  if (strength.includes("moderate")) return "marker-moderate";
  return "marker-subtle";
}

export function EvidenceTimeline({ result, file }: { result: AnalysisResult; file: File | null }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [duration, setDuration] = useState(0);
  const [selected, setSelected] = useState<TimelineEvent | null>(null);
  const videoUrl = useMemo(() => file && result.mediaKind === "video" ? URL.createObjectURL(file) : null, [file, result.mediaKind]);
  const events = [...result.timeline].sort((a, b) => a.timestamp - b.timestamp);
  const displayDuration = duration || Number(result.mediaInfo.duration ?? result.mediaInfo.duration_seconds ?? 0) || 1;

  useEffect(() => () => {
    if (videoUrl) URL.revokeObjectURL(videoUrl);
  }, [videoUrl]);

  function selectEvent(event: TimelineEvent) {
    setSelected(event);
    if (videoRef.current) {
      videoRef.current.currentTime = event.timestamp;
      void videoRef.current.play().catch(() => undefined);
    }
  }

  if (result.mediaKind !== "video") return null;

  return (
    <section className="dashboard-card timeline-card" id="timeline" aria-labelledby="timeline-title">
      <div className="card-heading">
        <div>
          <div className="eyebrow">TEMPORAL EVIDENCE</div>
          <h2 id="timeline-title">Video trust timeline</h2>
          <p>Jump to moments with recorded evidence. Markers are observations, not proof.</p>
        </div>
        <div className="card-heading-icon"><Clock3 size={18} /></div>
      </div>

      {videoUrl ? (
        <video
          ref={videoRef}
          className="timeline-video"
          src={videoUrl}
          controls
          playsInline
          preload="metadata"
          onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
          aria-label={`Video preview of ${result.filename}`}
        />
      ) : (
        <div className="video-unavailable"><Film size={20} /> The original clip is not available in this session. Timeline evidence is still shown below.</div>
      )}

      <div className="timeline-track-wrap">
        <div className="timeline-scale"><span>00:00</span><span>{timestamp(displayDuration)}</span></div>
        <div className="timeline-track" aria-label="Evidence event timeline">
          <span className="timeline-line" />
          {events.map((event, index) => {
            const left = `${Math.min(98, Math.max(2, (event.timestamp / displayDuration) * 100))}%`;
            return (
              <button
                key={event.id ?? `${event.timestamp}-${index}`}
                type="button"
                className={`timeline-marker ${eventColor(event)}${selected === event ? " is-selected" : ""}`}
                style={{ left }}
                onClick={() => selectEvent(event)}
                aria-label={`${timestamp(event.timestamp)}: ${event.title ?? event.observation}`}
                title={`${timestamp(event.timestamp)} · ${event.title ?? event.observation}`}
              />
            );
          })}
        </div>
      </div>

      {selected && (
        <div className="selected-event">
          <div className="selected-event-time"><Play size={12} fill="currentColor" /> {timestamp(selected.timestamp)}</div>
          <div><strong>{selected.title}</strong><p>{selected.observation}</p></div>
        </div>
      )}

      <div className="event-list-heading"><span>OBSERVATION LOG</span><span>{events.length} {events.length === 1 ? "event" : "events"}</span></div>
      {events.length ? (
        <div className="event-list">
          {events.map((event, index) => (
            <button className={`event-row${selected === event ? " is-active" : ""}`} type="button" key={event.id ?? `${event.timestamp}-${index}`} onClick={() => selectEvent(event)}>
              <span className={`event-dot ${eventColor(event)}`} />
              <span className="event-time">{timestamp(event.timestamp)}</span>
              <span className="event-copy"><strong>{event.title}</strong><span>{event.observation}</span></span>
              <span className="event-source">{event.source}</span>
            </button>
          ))}
        </div>
      ) : (
        <div className="empty-evidence"><ScanSearch size={17} /> No timestamped events were returned for this clip.</div>
      )}
    </section>
  );
}

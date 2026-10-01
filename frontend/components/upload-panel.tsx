"use client";

import { useEffect, useRef, useState } from "react";
import { FileImage, FileVideo2, FolderOpen, LockKeyhole, ShieldCheck, UploadCloud, X } from "lucide-react";

const MAX_BYTES = 100 * 1024 * 1024;
const ACCEPTED = new Set(["jpg", "jpeg", "png", "webp", "gif", "mp4", "mov", "webm", "m4v"]);

function extension(name: string) {
  return name.split(".").pop()?.toLowerCase() ?? "";
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateFile(file: File): string | null {
  if (!ACCEPTED.has(extension(file.name))) return "Choose a JPG, PNG, WEBP, GIF, MP4, MOV, or WEBM file.";
  if (file.size > MAX_BYTES) return "Files must be smaller than 100 MB for this local prototype.";
  if (file.size === 0) return "This file is empty. Choose another media file.";
  const ext = extension(file.name);
  const saysImage = file.type.startsWith("image/");
  const saysVideo = file.type.startsWith("video/");
  if (file.type && !saysImage && !saysVideo) return "The selected file does not appear to be an image or video.";
  if (saysImage && !["jpg", "jpeg", "png", "webp", "gif"].includes(ext)) return "The file extension and media type do not match.";
  if (saysVideo && !["mp4", "mov", "webm", "m4v"].includes(ext)) return "The file extension and media type do not match.";
  return null;
}

export interface UploadPanelProps {
  onAnalyze: (file: File) => void;
  busy: boolean;
  error?: string | null;
}

export function UploadPanel({ onAnalyze, busy, error }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  function chooseFile(candidate?: File) {
    if (!candidate) return;
    const validationError = validateFile(candidate);
    if (validationError) {
      setLocalError(validationError);
      return;
    }
    setLocalError(null);
    setFile(candidate);
    setPreview(URL.createObjectURL(candidate));
  }

  function clearFile() {
    setPreview(null);
    setFile(null);
    setLocalError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const isVideo = Boolean(file?.type.startsWith("video/") || (file && ["mp4", "mov", "webm", "m4v"].includes(extension(file.name))));
  const message = localError || error;

  return (
    <section className="upload-card" aria-labelledby="upload-title">
      <div className="upload-card-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-dot" /> PRIVATE MEDIA REVIEW</div>
          <h2 id="upload-title">Start with a piece of media</h2>
          <p>Drop in an image or short video. TrustLens will show its evidence, not just a verdict.</p>
        </div>
        <div className="upload-lock" aria-label="Processed locally">
          <LockKeyhole size={17} strokeWidth={1.8} />
          <span>Local analysis</span>
        </div>
      </div>

      <div
        className={`drop-zone${dragging ? " is-dragging" : ""}${file ? " has-file" : ""}`}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          chooseFile(event.dataTransfer.files[0]);
        }}
      >
        <input
          ref={inputRef}
          className="visually-hidden"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif,video/mp4,video/quicktime,video/webm,video/x-m4v,.jpg,.jpeg,.png,.webp,.gif,.mp4,.mov,.webm,.m4v"
          onChange={(event) => chooseFile(event.target.files?.[0])}
          aria-label="Select an image or video file"
        />
        {file && preview ? (
          <div className="selected-file">
            <div className="file-preview">
              {isVideo ? (
                <video src={preview} muted playsInline aria-label="Selected video preview" />
              ) : (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={preview} alt="Selected media preview" />
              )}
            </div>
            <div className="selected-file-copy">
              <div className="selected-file-type">{isVideo ? <FileVideo2 size={15} /> : <FileImage size={15} />}{isVideo ? "VIDEO FILE" : "IMAGE FILE"}</div>
              <strong title={file.name}>{file.name}</strong>
              <span>{formatBytes(file.size)} <span className="file-separator">·</span> {file.type || extension(file.name).toUpperCase()}</span>
            </div>
            <button className="icon-button remove-file" type="button" onClick={clearFile} disabled={busy} aria-label="Remove selected file"><X size={17} /></button>
          </div>
        ) : (
          <div className="drop-empty">
            <div className="upload-icon"><UploadCloud size={24} strokeWidth={1.7} /></div>
            <strong>Drag a file here to begin</strong>
            <span>or choose a file from your device</span>
            <button className="button button-secondary browse-button" type="button" onClick={() => inputRef.current?.click()} disabled={busy}>
              <FolderOpen size={16} /> Browse files
            </button>
          </div>
        )}
      </div>

      <div className="upload-footer">
        <div className="accepted-formats">
          <strong>SUPPORTED MEDIA</strong>
          <span>JPG</span><span>PNG</span><span>WEBP</span><span>MP4</span><span>MOV</span><span>WEBM</span>
        </div>
        {file ? (
          <button className="button button-primary analyze-button" type="button" onClick={() => onAnalyze(file)} disabled={busy}>
            <ShieldCheck size={17} /> {busy ? "Analysis running…" : "Analyze evidence"}
          </button>
        ) : (
          <span className="size-note">Maximum file size 100 MB</span>
        )}
      </div>
      {message && <div className="inline-error" role="alert">{message}</div>}
      <p className="privacy-note"><LockKeyhole size={13} /> Media is sent only to your configured local TrustLens backend for analysis.</p>
    </section>
  );
}

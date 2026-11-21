import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { CardStackIcon, CloseIcon, SparkIcon, UploadIcon } from "./Icons";
import { ProgressView } from "./ProgressView";
import type { Job } from "../types";

interface ImportPanelProps {
  sourceText: string;
  onSourceTextChange: (text: string) => void;
  onImportText: (text: string) => void;
  expanded: boolean;
  onToggle: (expanded: boolean) => void;
  hasCards: boolean;
  cardCount: number;
  busy: boolean;
  job: Job<unknown> | null;
}

const PLACEHOLDER = `1 Sol Ring
1 Command Tower (C15) 281
1 Atraxa, Grand Unifier (ONE) 360
4 Forest (MIR) 303`;

export function ImportPanel({
  sourceText,
  onSourceTextChange,
  onImportText,
  expanded,
  onToggle,
  hasCards,
  cardCount,
  busy,
  job,
}: ImportPanelProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  function loadFile(file: File) {
    setFileError(null);
    if (file.size > 2_000_000) {
      setFileError("That file is larger than 2 MB. Use a plain decklist file.");
      return;
    }
    void file
      .text()
      .then((text) => onImportText(text))
      .catch(() => setFileError("That file could not be read."));
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) loadFile(file);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) loadFile(file);
  }

  if (hasCards && !expanded) {
    return (
      <section className="import-bar" aria-label="Decklist source">
        <div className="import-bar-summary">
          <span className="icon-badge">
            <CardStackIcon />
          </span>
          <div>
            <strong>Decklist loaded</strong>
            <span>{cardCount} cards ready to review</span>
          </div>
        </div>
        <button
          className="button button-quiet"
          type="button"
          onClick={() => onToggle(true)}
        >
          Replace list
        </button>
      </section>
    );
  }

  return (
    <section className="panel import-panel" aria-labelledby="import-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Step 1</p>
          <h2 id="import-heading">Bring in your decklist</h2>
        </div>
        {hasCards && (
          <button
            className="icon-button"
            type="button"
            aria-label="Close decklist editor"
            onClick={() => onToggle(false)}
          >
            <CloseIcon />
          </button>
        )}
      </div>

      <p className="section-copy">
        Paste a text or Arena decklist, or upload a <code>.txt</code> file. One
        card per line, with an optional quantity, set, and collector number.
      </p>

      <div
        className={`import-drop ${dragging ? "is-dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <textarea
          value={sourceText}
          onChange={(event) => onSourceTextChange(event.target.value)}
          placeholder={PLACEHOLDER}
          spellCheck={false}
          aria-label="Decklist text"
          disabled={busy}
        />
        <div className="drop-hint">
          <UploadIcon />
          <span>Drop a .txt decklist here</span>
        </div>
      </div>

      <div className="import-actions">
        <div>
          <input
            ref={fileInput}
            type="file"
            accept=".txt,text/plain"
            onChange={handleFile}
            hidden
          />
          <button
            className="button button-secondary"
            type="button"
            onClick={() => fileInput.current?.click()}
            disabled={busy}
          >
            <UploadIcon />
            Upload file
          </button>
          {fileError && <p className="inline-error">{fileError}</p>}
        </div>
        <button
          className="button button-primary"
          type="button"
          onClick={() => onImportText(sourceText)}
          disabled={busy || sourceText.trim().length === 0}
        >
          <SparkIcon />
          {busy ? "Reading list…" : "Load cards"}
        </button>
      </div>

      <ProgressView job={job} busy={busy} label="Reading decklist" />
    </section>
  );
}

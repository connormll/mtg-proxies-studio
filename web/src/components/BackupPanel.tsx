import { useRef, useState, type ChangeEvent } from "react";
import { downloadBackup, parseBackup } from "../backup";
import type { WorkspaceState } from "../workspace";
import {
  ArchiveIcon,
  CheckIcon,
  DownloadIcon,
  UploadIcon,
  WarningIcon,
} from "./Icons";

const MAX_BACKUP_BYTES = 10_000_000;

interface BackupPanelProps {
  state: WorkspaceState;
  onRestore: (state: WorkspaceState, createdAt: string | null) => void;
  disabled?: boolean;
}

function cardTotals(state: WorkspaceState): string {
  const copies = state.cards.reduce((total, card) => total + card.count, 0);
  if (state.cards.length === 0) return "no cards";
  const cardLabel = `${state.cards.length} card${state.cards.length === 1 ? "" : "s"}`;
  const copyLabel = `${copies} cop${copies === 1 ? "y" : "ies"}`;
  return `${cardLabel} (${copyLabel})`;
}

function formatBackupDate(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return ` from ${date.toLocaleString()}`;
}

export function BackupPanel({
  state,
  onRestore,
  disabled = false,
}: BackupPanelProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [reading, setReading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleDownload() {
    setMessage(null);
    setError(null);
    try {
      downloadBackup(state);
      setMessage(`Backup downloaded with ${cardTotals(state)}.`);
    } catch {
      setError("The backup file could not be created.");
    }
  }

  async function handleFile(file: File) {
    setMessage(null);
    setError(null);

    if (file.size > MAX_BACKUP_BYTES) {
      setError("That backup file is larger than 10 MB.");
      return;
    }

    setReading(true);
    try {
      const restored = parseBackup(await file.text());
      const currentCopies = state.cards.reduce(
        (total, card) => total + card.count,
        0,
      );
      if (
        state.cards.length > 0 &&
        !window.confirm(
          `Restore this backup? It will replace the ${currentCopies} card${
            currentCopies === 1 ? "" : "s"
          } currently in the editor.`,
        )
      ) {
        return;
      }

      onRestore(restored.state, restored.createdAt);
      setMessage(
        `Restored ${cardTotals(restored.state)}${formatBackupDate(restored.createdAt)}.`,
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "That backup could not be read.",
      );
    } finally {
      setReading(false);
    }
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void handleFile(file);
    event.target.value = "";
  }

  return (
    <section className="backup-bar" aria-label="Workspace backup">
      <div className="backup-summary">
        <span className="icon-badge">
          <ArchiveIcon />
        </span>
        <div>
          <strong>Workspace backup</strong>
          <span>
            Keep the decklist, chosen printings, and layout settings in a file.
          </span>
        </div>
      </div>

      <div className="backup-controls">
        <input
          ref={fileInput}
          type="file"
          accept=".json,application/json"
          onChange={handleChange}
          hidden
        />
        <button
          className="button button-secondary"
          type="button"
          onClick={handleDownload}
          disabled={disabled || reading}
        >
          <DownloadIcon />
          Download backup
        </button>
        <button
          className="button button-secondary"
          type="button"
          onClick={() => fileInput.current?.click()}
          disabled={disabled || reading}
        >
          <UploadIcon />
          {reading ? "Reading backup…" : "Restore backup"}
        </button>
      </div>

      {error && (
        <p className="backup-status is-error" role="alert">
          <WarningIcon />
          {error}
        </p>
      )}
      {message && (
        <p className="backup-status is-success" aria-live="polite">
          <CheckIcon />
          {message}
        </p>
      )}
    </section>
  );
}

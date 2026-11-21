import {
  STORAGE_VERSION,
  normalizeWorkspaceState,
  type WorkspaceState,
} from "./workspace";

const BACKUP_FORMAT = "mtg-proxies-backup";
const BACKUP_VERSION = 1;

interface BackupEnvelope {
  format: typeof BACKUP_FORMAT;
  version: number;
  created_at: string;
  state: WorkspaceState;
}

export interface RestoredBackup {
  state: WorkspaceState;
  createdAt: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function backupFilename(date = new Date()): string {
  const stamp = date.toISOString().replace(/[:.]/g, "-").replace("Z", "");
  return `mtg-proxies-backup-${stamp}.json`;
}

export function createBackup(state: WorkspaceState): BackupEnvelope {
  return {
    format: BACKUP_FORMAT,
    version: BACKUP_VERSION,
    created_at: new Date().toISOString(),
    state: { ...state, version: STORAGE_VERSION },
  };
}

export function parseBackup(raw: string): RestoredBackup {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw) as unknown;
  } catch {
    throw new Error("That file is not valid JSON.");
  }

  // A wrapped backup carries metadata. A bare workspace state is also
  // accepted so backups made before the backup format existed still restore.
  if (isRecord(parsed) && parsed.format === BACKUP_FORMAT) {
    if (parsed.version !== BACKUP_VERSION) {
      throw new Error(
        "That backup was made by a newer version of MTG Proxy Studio.",
      );
    }
    const state = normalizeWorkspaceState(parsed.state);
    if (state === null) {
      throw new Error("That backup does not contain a valid workspace.");
    }
    return {
      state,
      createdAt: typeof parsed.created_at === "string" ? parsed.created_at : null,
    };
  }

  const state = normalizeWorkspaceState(parsed);
  if (state === null) {
    throw new Error("That file does not contain a workspace backup.");
  }
  return { state, createdAt: null };
}

export function downloadBackup(state: WorkspaceState): void {
  const payload = JSON.stringify(createBackup(state), null, 2);
  const blob = new Blob([payload], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = backupFilename();
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

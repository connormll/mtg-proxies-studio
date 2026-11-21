import type {
  CardEntry,
  CardWarning,
  ImportIssue,
  PrintOptions,
} from "./types";

export const STORAGE_KEY = "mtg-proxies-gui-v1";
export const STORAGE_VERSION = 1;

export interface WorkspaceState {
  version: number;
  sourceText: string;
  cards: CardEntry[];
  issues: ImportIssue[];
  options: PrintOptions;
}

const MODES = new Set(["standard", "makercraft", "handcut", "slider"]);
const PAPER_PRESETS = new Set(["letter", "a4", "custom"]);
const FACES = new Set(["all", "front", "back"]);
const SEVERITIES = new Set(["error", "warning"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function textOrNull(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function booleanValue(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function numberList(value: unknown): number[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is number =>
          typeof item === "number" && Number.isInteger(item),
      )
    : [];
}

export function defaultOptions(): PrintOptions {
  return {
    mode: "standard",
    paper_preset: "letter",
    paper_width: 8.5,
    paper_height: 11,
    scale: 1,
    border_crop: 14,
    gap: 0,
    bleed: 0,
    corner_radius: 2.5,
    no_basic_lands: false,
    no_tokens: false,
    faces: "all",
    background: null,
    cropmarks: true,
    cut_file: true,
    mark_inset: 7,
    mark_arm: 10,
    mark_stroke: 1,
    overcut: 1,
  };
}

function normalizeOptions(value: unknown): PrintOptions {
  const defaults = defaultOptions();
  if (!isRecord(value)) return defaults;

  const mode = text(value.mode, defaults.mode);
  const paperPreset = text(value.paper_preset, defaults.paper_preset);
  const faces = text(value.faces, defaults.faces);
  const background = textOrNull(value.background);

  return {
    mode: (MODES.has(mode) ? mode : defaults.mode) as PrintOptions["mode"],
    paper_preset: (PAPER_PRESETS.has(paperPreset)
      ? paperPreset
      : defaults.paper_preset) as PrintOptions["paper_preset"],
    paper_width: numberValue(value.paper_width, defaults.paper_width),
    paper_height: numberValue(value.paper_height, defaults.paper_height),
    scale: numberValue(value.scale, defaults.scale),
    border_crop: numberValue(value.border_crop, defaults.border_crop),
    gap: numberValue(value.gap, defaults.gap),
    bleed: numberValue(value.bleed, defaults.bleed),
    corner_radius: numberValue(value.corner_radius, defaults.corner_radius),
    no_basic_lands: booleanValue(value.no_basic_lands, defaults.no_basic_lands),
    no_tokens: booleanValue(value.no_tokens, defaults.no_tokens),
    faces: (FACES.has(faces) ? faces : defaults.faces) as PrintOptions["faces"],
    background: /^#[0-9a-f]{6}$/i.test(background ?? "") ? background : null,
    cropmarks: booleanValue(value.cropmarks, defaults.cropmarks),
    cut_file: booleanValue(value.cut_file, defaults.cut_file),
    mark_inset: numberValue(value.mark_inset, defaults.mark_inset),
    mark_arm: numberValue(value.mark_arm, defaults.mark_arm),
    mark_stroke: numberValue(value.mark_stroke, defaults.mark_stroke),
    overcut: numberValue(value.overcut, defaults.overcut),
  };
}

function normalizeWarning(value: unknown): CardWarning | null {
  if (!isRecord(value) || typeof value.message !== "string") return null;
  return {
    code: text(value.code, "printing"),
    message: value.message,
  };
}

function normalizeCard(value: unknown): CardEntry | null {
  if (!isRecord(value)) return null;
  const printingId = text(value.printing_id);
  const name = text(value.name);
  if (!printingId || !name) return null;

  const count = Math.max(
    1,
    Math.min(999, Math.round(numberValue(value.count, 1))),
  );
  const warnings = Array.isArray(value.warnings)
    ? value.warnings
        .map(normalizeWarning)
        .filter((warning): warning is CardWarning => warning !== null)
    : [];

  return {
    key: text(value.key) || `card:${printingId}`,
    printing_id: printingId,
    name,
    set_code: text(value.set_code),
    set_name: text(value.set_name),
    collector_number: text(value.collector_number),
    released_at: textOrNull(value.released_at),
    count,
    image_url: textOrNull(value.image_url),
    image_back_url: textOrNull(value.image_back_url),
    face_names:
      stringList(value.face_names).length > 0
        ? stringList(value.face_names)
        : [name],
    is_basic_land: booleanValue(value.is_basic_land, false),
    is_token: booleanValue(value.is_token, false),
    warnings,
    low_res: booleanValue(value.low_res, false),
    non_english: booleanValue(value.non_english, false),
    source_lines: numberList(value.source_lines),
  };
}

function normalizeIssue(value: unknown): ImportIssue | null {
  if (!isRecord(value) || typeof value.message !== "string") return null;
  // Older saved workspaces treated an unresolved card as a blocking error.
  // Reclassify those issues so restoring them does not lock the generator.
  const missingCard = value.message.startsWith("Unable to find card ");
  const severity = missingCard
    ? "warning"
    : text(value.severity, "warning");
  if (!SEVERITIES.has(severity)) return null;
  const message =
    missingCard && !value.message.includes("Skipped this line.")
      ? `${value.message} Skipped this line.`
      : value.message;
  return {
    line: Math.max(0, Math.round(numberValue(value.line, 0))),
    text: text(value.text),
    message,
    severity: severity as ImportIssue["severity"],
    skipped: missingCard || booleanValue(value.skipped, false),
  };
}

export function normalizeWorkspaceState(value: unknown): WorkspaceState | null {
  if (!isRecord(value) || value.version !== STORAGE_VERSION) return null;
  if (!Array.isArray(value.cards)) return null;

  const cards = value.cards
    .map(normalizeCard)
    .filter((card): card is CardEntry => card !== null);
  if (value.cards.length > 0 && cards.length === 0) return null;

  const issues = Array.isArray(value.issues)
    ? value.issues
        .map(normalizeIssue)
        .filter((issue): issue is ImportIssue => issue !== null)
    : [];

  return {
    version: STORAGE_VERSION,
    sourceText: text(value.sourceText),
    cards,
    issues,
    options: normalizeOptions(value.options),
  };
}

export function loadWorkspaceState(): WorkspaceState | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return normalizeWorkspaceState(JSON.parse(raw) as unknown);
  } catch {
    return null;
  }
}

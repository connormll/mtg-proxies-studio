export type PrintMode = "standard" | "makercraft" | "handcut" | "slider";
export type PrintingScope = "artworks" | "all";
export type Faces = "all" | "front" | "back";
export type PaperPreset = "letter" | "a4" | "custom";
export type Severity = "error" | "warning";
export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface CardWarning {
  code: string;
  message: string;
}

export interface CardEntry {
  key: string;
  printing_id: string;
  name: string;
  set_code: string;
  set_name: string;
  collector_number: string;
  released_at: string | null;
  count: number;
  image_url: string | null;
  image_back_url: string | null;
  face_names: string[];
  is_basic_land: boolean;
  is_token: boolean;
  warnings: CardWarning[];
  low_res: boolean;
  non_english: boolean;
  source_lines: number[];
}

export interface ImportIssue {
  line: number;
  text: string;
  message: string;
  severity: Severity;
  skipped: boolean;
}

export interface ImportResult {
  cards: CardEntry[];
  issues: ImportIssue[];
  total_count: number;
}

export interface PrintingOption {
  id: string;
  name: string;
  set_code: string;
  set_name: string;
  collector_number: string;
  released_at: string | null;
  rarity: string;
  border_color: string;
  language: string;
  high_res: boolean;
  digital: boolean;
  is_recommended: boolean;
  image_url: string | null;
  image_back_url: string | null;
  face_names: string[];
  warnings: CardWarning[];
  low_res: boolean;
  non_english: boolean;
}

export interface PrintingsResult {
  card_name: string;
  recommended_id: string;
  options: PrintingOption[];
  scope: PrintingScope;
}

export interface ReplacementRequest {
  printing_id: string;
  deck: Array<{ printing_id: string; count: number }>;
}

export interface ReplacementSuggestion {
  name: string;
  reason: string;
  card: CardEntry;
  off_color_identity: boolean;
}

export interface ReplacementResult {
  card_name: string;
  model: string;
  deck_color_identity: string;
  suggestions: ReplacementSuggestion[];
}

export interface PrintOptions {
  mode: PrintMode;
  paper_preset: PaperPreset;
  paper_width: number;
  paper_height: number;
  scale: number;
  border_crop: number;
  gap: number;
  bleed: number;
  corner_radius: number;
  no_basic_lands: boolean;
  no_tokens: boolean;
  faces: Faces;
  background: string | null;
  cropmarks: boolean;
  cut_file: boolean;
  mark_inset: number;
  mark_arm: number;
  mark_stroke: number;
  overcut: number;
}

export interface GeneratePayload {
  cards: Array<{ printing_id: string; count: number }>;
  options: {
    mode: PrintMode;
    paper_width: number;
    paper_height: number;
    scale: number;
    border_crop: number;
    gap: number;
    bleed: number;
    corner_radius: number;
    no_basic_lands: boolean;
    no_tokens: boolean;
    faces: Faces;
    background: string | null;
    cropmarks: boolean;
    cut_file: boolean;
    mark_inset: number;
    mark_arm: number;
    mark_stroke: number;
    overcut: number;
  };
}

export interface Job<T = unknown> {
  id: string;
  kind: "import" | "generate" | "suggest";
  status: JobStatus;
  stage: string;
  message: string;
  completed: number;
  total: number;
  error: string | null;
  result: T | null;
}

export interface Artifact {
  id: string;
  filename: string;
  label: string;
  kind: "pdf" | "svg" | "plt";
  media_type: string;
  size: number;
}

export interface GenerationResult {
  artifacts: Artifact[];
  layout: string;
  card_count: number;
  image_count: number;
  cards_per_page: number;
  pages: number;
  filters: string[];
}

export interface OutputState {
  jobId: string;
  result: GenerationResult;
}

export interface CutterDevice {
  label: string;
  bus: number | null;
  address: number | null;
}

export interface CutterDevicesResult {
  devices: CutterDevice[];
  error: string | null;
}

export interface SendToCutterResult {
  ok: boolean;
  message: string;
}

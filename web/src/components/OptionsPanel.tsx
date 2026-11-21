import { ChevronIcon, ScissorsIcon, SparkIcon, SpinnerIcon } from "./Icons";
import { ProgressView } from "./ProgressView";
import type { Job, PrintMode, PrintOptions } from "../types";

interface OptionsPanelProps {
  options: PrintOptions;
  onChange: (patch: Partial<PrintOptions>) => void;
  onModeChange: (mode: PrintMode) => void;
  onGenerate: () => void;
  canGenerate: boolean;
  disabledReason: string | null;
  busy: boolean;
  locked?: boolean;
  job: Job<unknown> | null;
}

const PAPER_PRESETS = {
  letter: { width: 8.5, height: 11 },
  a4: { width: 8.2677165354, height: 11.6929133858 },
} as const;

const MODES: Array<{ mode: PrintMode; title: string; description: string }> = [
  {
    mode: "standard",
    title: "Standard",
    description: "Regular print sheet with white crop marks.",
  },
  {
    mode: "makercraft",
    title: "MakerCraft",
    description: "Camera marks and a reusable Skycut template.",
  },
  {
    mode: "handcut",
    title: "Hand cut",
    description: "Full-page guides for a trimmer or craft knife.",
  },
  {
    mode: "slider",
    title: "Slider trimmer",
    description: "Bleed layout with full grid cut lines.",
  },
];

interface NumberFieldProps {
  id: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  hint?: string;
  disabled?: boolean;
  integer?: boolean;
  onChange: (value: number) => void;
}

function NumberField({
  id,
  label,
  value,
  min,
  max,
  step,
  unit,
  hint,
  disabled,
  integer,
  onChange,
}: NumberFieldProps) {
  return (
    <label className={`field ${disabled ? "is-disabled" : ""}`} htmlFor={id}>
      <span className="field-label">{label}</span>
      <span className="number-wrap">
        <input
          id={id}
          type="number"
          value={value}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          onChange={(event) => {
            const next = Number(event.target.value);
            if (Number.isFinite(next)) {
              onChange(integer ? Math.round(next) : next);
            }
          }}
        />
        {unit && <span>{unit}</span>}
      </span>
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

interface RangeFieldProps {
  id: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (value: number) => void;
}

function RangeField({
  id,
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: RangeFieldProps) {
  return (
    <div className="range-field">
      <label htmlFor={id}>{label}</label>
      <div className="range-controls">
        <input
          id={id}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        <span className="number-wrap compact">
          <input
            type="number"
            aria-label={`${label} in ${unit}`}
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isFinite(next)) onChange(next);
            }}
          />
          <span>{unit}</span>
        </span>
      </div>
    </div>
  );
}

export function OptionsPanel({
  options,
  onChange,
  onModeChange,
  onGenerate,
  canGenerate,
  disabledReason,
  busy,
  locked = false,
  job,
}: OptionsPanelProps) {
  const guidesDisabled =
    options.mode === "handcut" || options.mode === "slider";

  function setPaperPreset(preset: PrintOptions["paper_preset"]) {
    if (preset === "custom") {
      onChange({ paper_preset: preset });
      return;
    }
    const paper = PAPER_PRESETS[preset];
    onChange({
      paper_preset: preset,
      paper_width: paper.width,
      paper_height: paper.height,
    });
  }

  return (
    <aside className="options-panel panel" aria-labelledby="options-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Step 3</p>
          <h2 id="options-heading">Print setup</h2>
        </div>
      </div>

      <fieldset className="settings-lock" disabled={locked}>
        <fieldset className="option-group">
          <legend>Output mode</legend>
          <div className="mode-grid">
            {MODES.map((mode) => (
              <button
                key={mode.mode}
                type="button"
                className={`mode-button ${options.mode === mode.mode ? "is-active" : ""}`}
                aria-pressed={options.mode === mode.mode}
                onClick={() => onModeChange(mode.mode)}
              >
                <strong>{mode.title}</strong>
                <span>{mode.description}</span>
              </button>
            ))}
          </div>
        </fieldset>

        <div className="option-group">
          <label className="field">
            <span className="field-label">Paper</span>
            <select
              value={options.paper_preset}
              onChange={(event) =>
                setPaperPreset(
                  event.target.value as PrintOptions["paper_preset"],
                )
              }
            >
              <option value="letter">US Letter · 8.5 × 11 in</option>
              <option value="a4">A4 · 210 × 297 mm</option>
              <option value="custom">Custom size</option>
            </select>
          </label>

          {options.paper_preset === "custom" && (
            <div className="field-pair">
              <NumberField
                id="paper-width"
                label="Width"
                value={options.paper_width}
                min={3}
                max={20}
                step={0.1}
                unit="in"
                onChange={(paper_width) => onChange({ paper_width })}
              />
              <NumberField
                id="paper-height"
                label="Height"
                value={options.paper_height}
                min={3}
                max={20}
                step={0.1}
                unit="in"
                onChange={(paper_height) => onChange({ paper_height })}
              />
            </div>
          )}

          <RangeField
            id="gap"
            label="Gap between cards"
            value={options.gap}
            min={0}
            max={3}
            step={0.5}
            unit="mm"
            onChange={(gap) => onChange({ gap })}
          />
          <RangeField
            id="bleed"
            label="Mirrored bleed"
            value={options.bleed}
            min={0}
            max={10}
            step={0.5}
            unit="mm"
            onChange={(bleed) => onChange({ bleed })}
          />
          <RangeField
            id="corner-radius"
            label="Corner radius"
            value={options.corner_radius}
            min={0}
            max={10}
            step={0.5}
            unit="mm"
            onChange={(corner_radius) => onChange({ corner_radius })}
          />
        </div>

        <div className="option-group">
          <label className="field">
            <span className="field-label">Card faces</span>
            <select
              value={options.faces}
              onChange={(event) =>
                onChange({ faces: event.target.value as PrintOptions["faces"] })
              }
            >
              <option value="all">Front and back</option>
              <option value="front">Fronts only</option>
              <option value="back">Backs only</option>
            </select>
          </label>

          <label className="check-row">
            <input
              type="checkbox"
              checked={options.background !== null}
              onChange={(event) =>
                onChange({
                  background: event.target.checked ? "#ffffff" : null,
                })
              }
            />
            <span>
              <strong>Background color</strong>
              <small>Off uses white behind rounded corners.</small>
            </span>
          </label>
          {options.background !== null && (
            <div className="color-row">
              <input
                type="color"
                value={options.background}
                aria-label="Background color"
                onChange={(event) =>
                  onChange({ background: event.target.value })
                }
              />
              <code>{options.background}</code>
            </div>
          )}

          <label className={`check-row ${guidesDisabled ? "is-disabled" : ""}`}>
            <input
              type="checkbox"
              checked={options.cropmarks && !guidesDisabled}
              disabled={guidesDisabled}
              onChange={(event) =>
                onChange({ cropmarks: event.target.checked })
              }
            />
            <span>
              <strong>White crop marks</strong>
              <small>Ignored by the hand-cut and slider layouts.</small>
            </span>
          </label>

          <label className="check-row">
            <input
              type="checkbox"
              checked={options.cut_file}
              onChange={(event) => onChange({ cut_file: event.target.checked })}
            />
            <span>
              <strong>Also write SVG cut file</strong>
              <small>
                {options.mode === "makercraft"
                  ? "The MakerCraft PLT template is always generated."
                  : "One SVG per printed page, with card outlines."}
              </small>
            </span>
          </label>
        </div>

        <details className="advanced-options">
          <summary>
            <span>Advanced layout</span>
            <ChevronIcon />
          </summary>
          <div className="advanced-content">
            <div className="field-pair">
              <NumberField
                id="scale"
                label="Card scale"
                value={options.scale}
                min={0.1}
                max={3}
                step={0.05}
                unit="×"
                onChange={(scale) => onChange({ scale })}
              />
              <NumberField
                id="border-crop"
                label="Border crop"
                value={options.border_crop}
                min={0}
                max={300}
                step={1}
                unit="px"
                integer
                onChange={(border_crop) => onChange({ border_crop })}
              />
            </div>

            <p className="advanced-label">MakerCraft registration</p>
            <div className="field-pair">
              <NumberField
                id="mark-inset"
                label="Mark inset"
                value={options.mark_inset}
                min={0.5}
                max={60}
                step={0.5}
                unit="mm"
                hint="Raised automatically when needed."
                onChange={(mark_inset) => onChange({ mark_inset })}
              />
              <NumberField
                id="mark-arm"
                label="Arm length"
                value={options.mark_arm}
                min={0.5}
                max={50}
                step={0.5}
                unit="mm"
                onChange={(mark_arm) => onChange({ mark_arm })}
              />
            </div>
            <div className="field-pair">
              <NumberField
                id="mark-stroke"
                label="Mark stroke"
                value={options.mark_stroke}
                min={0.1}
                max={10}
                step={0.1}
                unit="mm"
                onChange={(mark_stroke) => onChange({ mark_stroke })}
              />
              <NumberField
                id="overcut"
                label="Overcut"
                value={options.overcut}
                min={0}
                max={10}
                step={0.5}
                unit="mm"
                onChange={(overcut) => onChange({ overcut })}
              />
            </div>
          </div>
        </details>
      </fieldset>

      <div className="generate-area">
        <button
          className="button button-generate"
          type="button"
          onClick={onGenerate}
          disabled={!canGenerate || busy}
        >
          {busy ? (
            <SpinnerIcon />
          ) : options.cut_file || options.mode === "makercraft" ? (
            <ScissorsIcon />
          ) : (
            <SparkIcon />
          )}
          {busy ? "Generating…" : "Generate print files"}
        </button>
        {disabledReason && !busy && (
          <p className="generate-note">{disabledReason}</p>
        )}
        <ProgressView job={job} busy={busy} label="Generating print files" />
      </div>
    </aside>
  );
}

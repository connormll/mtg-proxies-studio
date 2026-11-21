import { useCallback, useEffect, useMemo, useState } from "react";
import {
  completedGeneration,
  completedImport,
  errorMessage,
  pendingJob,
  startGeneration,
  startImport,
  waitForJob,
} from "./api";
import { BackupPanel } from "./components/BackupPanel";
import { CardGrid } from "./components/CardGrid";
import {
  CardStackIcon,
  CloseIcon,
  InfoIcon,
  LogoMark,
  WarningIcon,
} from "./components/Icons";
import { ImportPanel } from "./components/ImportPanel";
import { IssuesPanel } from "./components/IssuesPanel";
import { OptionsPanel } from "./components/OptionsPanel";
import { OutputPanel } from "./components/OutputPanel";
import { PrintingDialog } from "./components/PrintingDialog";
import { ReplacementDialog } from "./components/ReplacementDialog";
import type {
  CardEntry,
  GeneratePayload,
  GenerationResult,
  ImportIssue,
  ImportResult,
  Job,
  OutputState,
  PrintMode,
  PrintOptions,
  PrintingOption,
  ReplacementSuggestion,
} from "./types";
import {
  STORAGE_KEY,
  STORAGE_VERSION,
  defaultOptions,
  loadWorkspaceState,
  type WorkspaceState,
} from "./workspace";

const MODE_DEFAULTS: Record<
  PrintMode,
  { bleed: number; corner_radius: number; cut_file: boolean }
> = {
  standard: { bleed: 0, corner_radius: 2.5, cut_file: true },
  makercraft: { bleed: 0, corner_radius: 2.5, cut_file: false },
  handcut: { bleed: 0, corner_radius: 0, cut_file: false },
  slider: { bleed: 2, corner_radius: 0, cut_file: false },
};

function includedTotal(cards: CardEntry[], options: PrintOptions): number {
  return cards
    .filter(
      (card) =>
        !(options.no_basic_lands && card.is_basic_land) &&
        !(options.no_tokens && card.is_token),
    )
    .reduce((total, card) => total + card.count, 0);
}

function generatePayload(
  cards: CardEntry[],
  options: PrintOptions,
): GeneratePayload {
  return {
    cards: cards.map((card) => ({
      printing_id: card.printing_id,
      count: card.count,
    })),
    options: {
      mode: options.mode,
      paper_width: options.paper_width,
      paper_height: options.paper_height,
      scale: options.scale,
      border_crop: options.border_crop,
      gap: options.gap,
      bleed: options.bleed,
      corner_radius: options.corner_radius,
      no_basic_lands: options.no_basic_lands,
      no_tokens: options.no_tokens,
      faces: options.faces,
      background: options.background,
      cropmarks: options.cropmarks,
      cut_file: options.cut_file,
      mark_inset: options.mark_inset,
      mark_arm: options.mark_arm,
      mark_stroke: options.mark_stroke,
      overcut: options.overcut,
    },
  };
}

export default function App() {
  const initial = useMemo(loadWorkspaceState, []);
  const [sourceText, setSourceText] = useState(initial?.sourceText ?? "");
  const [cards, setCards] = useState<CardEntry[]>(initial?.cards ?? []);
  const [issues, setIssues] = useState<ImportIssue[]>(initial?.issues ?? []);
  const [options, setOptions] = useState<PrintOptions>(
    initial?.options ?? defaultOptions(),
  );
  const [showImport, setShowImport] = useState(
    (initial?.cards.length ?? 0) === 0,
  );
  const [error, setError] = useState<string | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [importJob, setImportJob] = useState<Job<ImportResult> | null>(null);
  const [generateBusy, setGenerateBusy] = useState(false);
  const [generateJob, setGenerateJob] = useState<Job<GenerationResult> | null>(
    null,
  );
  const [output, setOutput] = useState<OutputState | null>(null);
  const [stale, setStale] = useState(false);
  const [pickerKey, setPickerKey] = useState<string | null>(null);
  const [replacementKey, setReplacementKey] = useState<string | null>(null);

  const pickerCard = useMemo(
    () => cards.find((card) => card.key === pickerKey) ?? null,
    [cards, pickerKey],
  );
  const replacementCard = useMemo(
    () => cards.find((card) => card.key === replacementKey) ?? null,
    [cards, replacementKey],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const state: WorkspaceState = {
          version: STORAGE_VERSION,
          sourceText,
          cards,
          issues,
          options,
        };
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      } catch {
        // Persistence is a convenience; a blocked quota should not interrupt the editor.
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [sourceText, cards, issues, options]);

  const invalidateOutputs = useCallback(() => {
    if (output !== null) {
      setOutput(null);
      setStale(true);
    }
  }, [output]);

  function handleOptionsChange(patch: Partial<PrintOptions>) {
    invalidateOutputs();
    setOptions((previous) => ({ ...previous, ...patch }));
  }

  function handleModeChange(mode: PrintMode) {
    invalidateOutputs();
    setOptions((previous) => {
      const previousDefaults = MODE_DEFAULTS[previous.mode];
      const nextDefaults = MODE_DEFAULTS[mode];
      const next = { ...previous, mode };
      if (previous.bleed === previousDefaults.bleed)
        next.bleed = nextDefaults.bleed;
      if (previous.corner_radius === previousDefaults.corner_radius) {
        next.corner_radius = nextDefaults.corner_radius;
      }
      if (previous.cut_file === previousDefaults.cut_file) {
        next.cut_file = nextDefaults.cut_file;
      }
      return next;
    });
  }

  function handleQuantity(key: string, count: number) {
    invalidateOutputs();
    setCards((previous) =>
      previous.map((card) => (card.key === key ? { ...card, count } : card)),
    );
  }

  function handleRemove(key: string) {
    invalidateOutputs();
    setCards((previous) => previous.filter((card) => card.key !== key));
    if (cards.length <= 1) setShowImport(true);
  }

  function handleFiltersChange(
    patch: Pick<PrintOptions, "no_basic_lands" | "no_tokens">,
  ) {
    invalidateOutputs();
    setOptions((previous) => ({
      ...previous,
      no_basic_lands: patch.no_basic_lands,
      no_tokens: patch.no_tokens,
    }));
  }

  async function handleImportText(text: string) {
    if (importBusy || generateBusy) return;
    if (text.trim().length === 0) {
      setError("Paste a decklist or upload a .txt file first.");
      return;
    }
    if (
      cards.length > 0 &&
      !window.confirm(
        "Replace the cards currently in the editor with this decklist?",
      )
    ) {
      return;
    }

    setError(null);
    setSourceText(text);
    setImportBusy(true);
    setImportJob(pendingJob<ImportResult>("import"));
    let finalJob: Job<ImportResult> | null = null;
    try {
      const { job_id } = await startImport(text);
      finalJob = await waitForJob<ImportResult>(job_id, setImportJob);
      const result = completedImport(finalJob);
      setCards(result.cards);
      setIssues(result.issues);
      setOutput(null);
      setStale(false);
      setShowImport(result.issues.some((issue) => issue.severity === "error"));
      window.setTimeout(
        () =>
          document
            .getElementById("cards")
            ?.scrollIntoView({ behavior: "smooth", block: "start" }),
        100,
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setImportBusy(false);
      setImportJob(finalJob?.status === "failed" ? finalJob : null);
    }
  }

  async function handleGenerate() {
    if (importBusy || generateBusy) return;
    setError(null);
    setOutput(null);
    setStale(false);
    setGenerateBusy(true);
    setGenerateJob(pendingJob<GenerationResult>("generate"));
    let finalJob: Job<GenerationResult> | null = null;
    try {
      const { job_id } = await startGeneration(generatePayload(cards, options));
      finalJob = await waitForJob<GenerationResult>(job_id, setGenerateJob);
      const result = completedGeneration(finalJob);
      setOutput({ jobId: job_id, result });
      setStale(false);
      setGenerateJob(null);
      window.setTimeout(
        () =>
          document
            .getElementById("outputs")
            ?.scrollIntoView({ behavior: "smooth", block: "start" }),
        100,
      );
    } catch (reason) {
      setError(errorMessage(reason));
      setGenerateJob(finalJob?.status === "failed" ? finalJob : null);
    } finally {
      setGenerateBusy(false);
    }
  }

  function handlePrintingSelect(option: PrintingOption) {
    if (!pickerCard) return;
    invalidateOutputs();
    setCards((previous) =>
      previous.map((card) =>
        card.key === pickerCard.key
          ? {
              ...card,
              printing_id: option.id,
              name: option.name,
              set_code: option.set_code,
              set_name: option.set_name,
              collector_number: option.collector_number,
              released_at: option.released_at,
              image_url: option.image_url,
              image_back_url: option.image_back_url,
              face_names: option.face_names,
              warnings: option.warnings,
              low_res: option.low_res,
              non_english: option.non_english,
            }
          : card,
      ),
    );
    setPickerKey(null);
  }

  function handleReplace(suggestion: ReplacementSuggestion) {
    if (!replacementCard) return;
    const original = replacementCard;
    invalidateOutputs();
    setCards((previous) => {
      const remaining = previous.filter((card) => card.key !== original.key);
      const existing = remaining.find(
        (card) => card.key === suggestion.card.key,
      );
      if (existing) {
        return remaining.map((card) =>
          card.key === existing.key
            ? {
                ...card,
                count: Math.min(999, card.count + original.count),
                source_lines: Array.from(
                  new Set([...card.source_lines, ...original.source_lines]),
                ).sort((a, b) => a - b),
              }
            : card,
        );
      }

      const replacement: CardEntry = {
        ...suggestion.card,
        count: original.count,
        source_lines: original.source_lines,
      };
      const index = previous.findIndex((card) => card.key === original.key);
      if (index < 0) return [...remaining, replacement];
      const next = [...previous];
      next.splice(index, 1, replacement);
      return next;
    });
    setReplacementKey(null);
  }

  function handleRestore(restored: WorkspaceState) {
    setSourceText(restored.sourceText);
    setCards(restored.cards);
    setIssues(restored.issues);
    setOptions(restored.options);
    setOutput(null);
    setStale(false);
    setShowImport(restored.cards.length === 0);
    setPickerKey(null);
    setReplacementKey(null);
    setImportJob(null);
    setGenerateJob(null);
    setError(null);
  }

  function handlePrint(url: string) {
    const frame = document.createElement("iframe");
    frame.title = "Print preview";
    frame.style.position = "fixed";
    frame.style.left = "-10000px";
    frame.style.top = "0";
    frame.style.width = "800px";
    frame.style.height = "1000px";
    frame.src = url;
    frame.onload = () => {
      window.setTimeout(() => {
        try {
          frame.contentWindow?.focus();
          frame.contentWindow?.print();
        } catch {
          window.open(url, "_blank", "noopener,noreferrer");
        }
      }, 350);
    };
    document.body.appendChild(frame);
    window.setTimeout(() => frame.remove(), 120_000);
  }

  const included = includedTotal(cards, options);
  const canGenerateIncluded = included > 0;
  const disabledReason = importBusy
    ? "Wait for the decklist import to finish."
    : cards.length === 0
      ? "Load a decklist to generate print files."
      : !canGenerateIncluded
        ? "All cards are currently excluded. Turn off a filter or add cards."
        : null;
  const canGenerate = disabledReason === null;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <LogoMark />
          <div>
            <p className="eyebrow">MTG Proxies</p>
            <h1>Print Studio</h1>
          </div>
        </div>
        <div className="topbar-meta">
          <span
            className="local-chip"
            title="Generated files and artwork stay on this machine."
          >
            <span className="local-dot" />
            Local files
          </span>
          <span>High-resolution Scryfall art</span>
        </div>
      </header>

      <main>
        {error && (
          <div className="alert alert-error" role="alert">
            <WarningIcon />
            <p>{error}</p>
            <button
              className="icon-button"
              type="button"
              aria-label="Dismiss error"
              onClick={() => setError(null)}
            >
              <CloseIcon />
            </button>
          </div>
        )}

        <ImportPanel
          sourceText={sourceText}
          onSourceTextChange={setSourceText}
          onImportText={(text) => void handleImportText(text)}
          expanded={showImport}
          onToggle={setShowImport}
          hasCards={cards.length > 0}
          cardCount={cards.reduce((total, card) => total + card.count, 0)}
          busy={importBusy || generateBusy}
          job={importJob}
        />

        <IssuesPanel issues={issues} />

        <BackupPanel
          state={{ version: STORAGE_VERSION, sourceText, cards, issues, options }}
          onRestore={handleRestore}
          disabled={importBusy || generateBusy}
        />

        {stale && (
          <div className="alert alert-info">
            <InfoIcon />
            <p>
              Your cards or layout settings changed. Generate new print files
              before printing or cutting.
            </p>
          </div>
        )}

        <div className="workspace">
          <CardGrid
            cards={cards}
            options={options}
            onQuantity={handleQuantity}
            onRemove={handleRemove}
            onChoosePrinting={(card) => setPickerKey(card.key)}
            onReplace={(card) => setReplacementKey(card.key)}
            onFiltersChange={handleFiltersChange}
            locked={importBusy || generateBusy}
          />
          <OptionsPanel
            options={options}
            onChange={handleOptionsChange}
            onModeChange={handleModeChange}
            onGenerate={() => void handleGenerate()}
            canGenerate={canGenerate}
            disabledReason={disabledReason}
            busy={generateBusy}
            locked={importBusy || generateBusy}
            job={generateJob}
          />
        </div>

        {output && (
          <OutputPanel
            output={output}
            mode={options.mode}
            onPrint={handlePrint}
          />
        )}

        {!output && cards.length > 0 && !stale && (
          <section className="generate-placeholder">
            <CardStackIcon />
            <div>
              <strong>Nothing generated yet</strong>
              <p>Set your layout options, then create the PDF and cut files.</p>
            </div>
          </section>
        )}
      </main>

      <footer className="footer">
        <span>MTG Proxy Studio</span>
        <span>Print at 100% / Actual size · Images from Scryfall</span>
      </footer>

      {pickerCard && (
        <PrintingDialog
          card={pickerCard}
          onClose={() => setPickerKey(null)}
          onSelect={handlePrintingSelect}
        />
      )}

      {replacementCard && (
        <ReplacementDialog
          card={replacementCard}
          deck={cards}
          onClose={() => setReplacementKey(null)}
          onReplace={handleReplace}
        />
      )}
    </div>
  );
}

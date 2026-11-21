import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  errorMessage,
  pendingJob,
  startReplacementSuggestions,
  waitForJob,
} from "../api";
import type {
  CardEntry,
  Job,
  ReplacementResult,
  ReplacementSuggestion,
} from "../types";
import { CloseIcon, SparkIcon, WarningIcon } from "./Icons";
import { ProgressView } from "./ProgressView";

interface ReplacementDialogProps {
  card: CardEntry;
  deck: CardEntry[];
  onClose: () => void;
  onReplace: (suggestion: ReplacementSuggestion) => void;
}

function SuggestionImage({ card }: { card: CardEntry }) {
  if (!card.image_url) {
    return (
      <span className="replacement-image replacement-image-empty">
        {card.name}
      </span>
    );
  }
  return (
    <span
      className={`replacement-image ${card.image_back_url ? "has-back" : ""}`}
    >
      <img
        src={card.image_url}
        alt={card.face_names[0] ?? card.name}
        loading="lazy"
      />
      {card.image_back_url && (
        <img
          src={card.image_back_url}
          alt={card.face_names[1] ?? "Back face"}
          loading="lazy"
          className="replacement-back"
        />
      )}
    </span>
  );
}

export function ReplacementDialog({
  card,
  deck,
  onClose,
  onReplace,
}: ReplacementDialogProps) {
  const [job, setJob] = useState<Job<ReplacementResult> | null>(null);
  const [result, setResult] = useState<ReplacementResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const dialogRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const load = useCallback(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    setResult(null);
    setJob(pendingJob<ReplacementResult>("suggest"));

    void (async () => {
      let finalJob: Job<ReplacementResult> | null = null;
      try {
        const { job_id } = await startReplacementSuggestions({
          printing_id: card.printing_id,
          deck: deck.map((entry) => ({
            printing_id: entry.printing_id,
            count: entry.count,
          })),
        });
        finalJob = await waitForJob<ReplacementResult>(
          job_id,
          setJob,
          controller.signal,
        );
        if (finalJob.status === "failed") {
          throw new Error(
            finalJob.error ?? "Kimi could not suggest a replacement.",
          );
        }
        if (!finalJob.result) {
          throw new Error("Kimi finished without returning suggestions.");
        }
        if (!controller.signal.aborted) setResult(finalJob.result);
      } catch (reason) {
        if (controller.signal.aborted) return;
        setError(errorMessage(reason));
        setJob(finalJob?.status === "failed" ? finalJob : null);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
  }, [card.printing_id, deck]);

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
  }, [load]);

  useEffect(() => {
    const previous =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialogRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;

      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (document.activeElement === dialogRef.current) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previous?.focus();
    };
  }, []);

  return createPortal(
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="printing-dialog replacement-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="replacement-title"
        aria-busy={loading}
        tabIndex={-1}
        ref={dialogRef}
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">Kimi suggests</p>
            <h2 id="replacement-title">Replace {card.name}</h2>
            <p>
              Finds cards that fill the same role in your deck, with the closest
              effect and mana value.
            </p>
          </div>
          <button
            className="icon-button"
            type="button"
            onClick={onClose}
            aria-label="Close replacement suggestions"
          >
            <CloseIcon />
          </button>
        </header>

        <div className="replacement-target">
          <span className="replacement-target-art">
            {card.image_url ? (
              <img src={card.image_url} alt="" />
            ) : (
              <span>{card.name}</span>
            )}
          </span>
          <div className="replacement-target-copy">
            <strong>{card.name}</strong>
            <span>
              {card.set_code} · {card.collector_number} · {card.count}{" "}
              {card.count === 1 ? "copy" : "copies"}
            </span>
            <p>
              One suggestion replaces every copy in the editor. Nothing is
              changed until you pick a card.
            </p>
          </div>
          <SparkIcon />
        </div>

        <div className="dialog-body">
          {loading && (
            <div className="replacement-loading" aria-live="polite">
              <div>
                <strong>Kimi is reading the card and your deck</strong>
                <span>
                  It is comparing rules text, role, timing, and mana value.
                </span>
              </div>
              <ProgressView job={job} busy={loading} label="Asking Kimi" />
            </div>
          )}

          {!loading && error && (
            <div className="replacement-error">
              <p className="form-error">{error}</p>
              <button
                className="button button-secondary"
                type="button"
                onClick={load}
              >
                Try again
              </button>
            </div>
          )}

          {!loading && !error && result && result.suggestions.length === 0 && (
            <div className="replacement-error">
              <p className="empty-copy">
                Kimi did not return a card that exists in Scryfall. Try again
                for a fresh set of suggestions.
              </p>
              <button
                className="button button-secondary"
                type="button"
                onClick={load}
              >
                Ask again
              </button>
            </div>
          )}

          {!loading && !error && result && result.suggestions.length > 0 && (
            <>
              <div className="replacement-intro">
                <div>
                  <strong>Same effect, different card</strong>
                  <span>
                    Ranked by how closely each card matches the original.
                    {result.deck_color_identity
                      ? ` Deck colors: ${result.deck_color_identity}.`
                      : ""}
                  </span>
                </div>
                <button
                  className="button button-quiet"
                  type="button"
                  onClick={load}
                >
                  Ask again
                </button>
              </div>
              <div className="replacement-grid">
                {result.suggestions.map((suggestion) => (
                  <button
                    key={suggestion.card.key}
                    type="button"
                    className="replacement-option"
                    onClick={() => onReplace(suggestion)}
                    aria-label={`Replace ${card.name} with ${suggestion.name}`}
                  >
                    <SuggestionImage card={suggestion.card} />
                    <span className="replacement-meta">
                      <strong>{suggestion.card.name}</strong>
                      <span>
                        {suggestion.card.set_code} ·{" "}
                        {suggestion.card.collector_number}
                      </span>
                      <span className="replacement-reason">
                        {suggestion.reason}
                      </span>
                      {suggestion.off_color_identity && (
                        <span className="replacement-warning">
                          <WarningIcon />
                          Outside the deck&apos;s color identity
                        </span>
                      )}
                      <span className="replacement-use">Use this card</span>
                    </span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <footer className="dialog-footer replacement-footer">
          <p>
            Kimi suggestions send this card and your decklist card names to
            OpenCode Go. Artwork and files stay on this machine.
          </p>
          {result && <span>Suggested by {result.model} via OpenCode Go</span>}
        </footer>
      </div>
    </div>,
    document.body,
  );
}

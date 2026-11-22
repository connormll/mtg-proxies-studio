import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { createPortal } from "react-dom";
import {
  clearReplacementKey,
  errorMessage,
  getReplacementSettings,
  pendingJob,
  saveReplacementKey,
  startReplacementSuggestions,
  waitForJob,
} from "../api";
import type {
  CardEntry,
  Job,
  ReplacementResult,
  ReplacementSettings,
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
  const [settings, setSettings] = useState<ReplacementSettings | null>(null);
  const [showKeyForm, setShowKeyForm] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [keyError, setKeyError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState(false);
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
        void getReplacementSettings()
          .then((next) => {
            if (controller.signal.aborted) return;
            setSettings(next);
            if (!next.configured) setShowKeyForm(true);
          })
          .catch(() => {
            // Keep the original error if the settings cannot be read.
          });
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
  }, [card.printing_id, deck]);

  const checkSettings = useCallback(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    setResult(null);
    setJob(null);

    void (async () => {
      try {
        const next = await getReplacementSettings();
        if (controller.signal.aborted) return;
        setSettings(next);
        if (next.configured) {
          setShowKeyForm(false);
          load();
        } else {
          setShowKeyForm(true);
          setLoading(false);
        }
      } catch (reason) {
        if (controller.signal.aborted) return;
        setLoading(false);
        setError(errorMessage(reason));
      }
    })();
  }, [load]);

  useEffect(() => {
    checkSettings();
    return () => abortRef.current?.abort();
  }, [checkSettings]);

  async function handleSaveKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = apiKey.trim();
    if (!value) {
      setKeyError("Paste an OpenCode Go API key first.");
      return;
    }

    setSavingKey(true);
    setKeyError(null);
    try {
      const next = await saveReplacementKey(value);
      setSettings(next);
      setApiKey("");
      setShowKeyForm(false);
      checkSettings();
    } catch (reason) {
      setKeyError(errorMessage(reason));
    } finally {
      setSavingKey(false);
    }
  }

  async function handleClearKey() {
    if (
      !window.confirm(
        "Remove the saved OpenCode Go key from this computer? You can paste a new key at any time.",
      )
    ) {
      return;
    }

    setSavingKey(true);
    setKeyError(null);
    try {
      await clearReplacementKey();
      setApiKey("");
      setShowKeyForm(false);
      checkSettings();
    } catch (reason) {
      setKeyError(errorMessage(reason));
    } finally {
      setSavingKey(false);
    }
  }

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

          {!loading && showKeyForm && (
            <form
              className="replacement-key"
              onSubmit={(event) => void handleSaveKey(event)}
            >
              <div>
                <strong>Connect OpenCode Go</strong>
                <p>
                  Kimi replacement suggestions need an OpenCode Go key. Paste
                  one here once and this computer will remember it for later
                  launches.
                </p>
              </div>
              <label className="field" htmlFor="opencode-api-key">
                <span className="field-label">OpenCode Go API key</span>
                <input
                  id="opencode-api-key"
                  type="password"
                  value={apiKey}
                  placeholder="oc_sk_..."
                  autoComplete="off"
                  spellCheck={false}
                  disabled={savingKey}
                  onChange={(event) => setApiKey(event.target.value)}
                />
                <span className="field-hint">
                  Saved in your user settings folder with owner-only
                  permissions. It is never stored in the browser or in
                  workspace backups.
                </span>
              </label>
              {keyError && (
                <p className="form-error" role="alert">
                  {keyError}
                </p>
              )}
              <div className="replacement-key-actions">
                <button
                  className="button button-primary"
                  type="submit"
                  disabled={savingKey || !apiKey.trim()}
                >
                  {savingKey ? "Saving…" : "Save key"}
                </button>
                <a
                  className="button button-quiet"
                  href="https://opencode.ai/console"
                  target="_blank"
                  rel="noreferrer"
                >
                  Get a key
                </a>
                {settings?.source === "saved" && (
                  <button
                    className="button button-quiet"
                    type="button"
                    disabled={savingKey}
                    onClick={() => void handleClearKey()}
                  >
                    Forget saved key
                  </button>
                )}
                {settings?.configured && (
                  <button
                    className="button button-quiet"
                    type="button"
                    disabled={savingKey}
                    onClick={() => {
                      setKeyError(null);
                      setShowKeyForm(false);
                    }}
                  >
                    Cancel
                  </button>
                )}
              </div>
            </form>
          )}

          {!loading && !showKeyForm && error && (
            <div className="replacement-error">
              <p className="form-error">{error}</p>
              <button
                className="button button-secondary"
                type="button"
                onClick={() => {
                  if (settings?.configured) load();
                  else checkSettings();
                }}
              >
                Try again
              </button>
            </div>
          )}

          {!loading &&
            !showKeyForm &&
            !error &&
            result &&
            result.suggestions.length === 0 && (
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

          {!loading &&
            !showKeyForm &&
            !error &&
            result &&
            result.suggestions.length > 0 && (
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
          <div className="replacement-footer-meta">
            {result && (
              <span>Suggested by {result.model} via OpenCode Go</span>
            )}
            {settings?.source === "environment" && (
              <span>Key from OPENCODE_API_KEY</span>
            )}
            {settings?.source === "saved" && !showKeyForm && (
              <button
                className="button button-quiet"
                type="button"
                onClick={() => {
                  setKeyError(null);
                  setShowKeyForm(true);
                }}
              >
                Manage key
              </button>
            )}
          </div>
        </footer>
      </div>
    </div>,
    document.body,
  );
}

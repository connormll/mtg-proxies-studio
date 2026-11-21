import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { getPrintings } from "../api";
import type {
  CardEntry,
  PrintingOption,
  PrintingScope,
  PrintingsResult,
} from "../types";
import { CardPreview, type CardPreviewAnchor } from "./CardPreview";
import { CheckIcon, CloseIcon, SpinnerIcon, WarningIcon } from "./Icons";

interface PreviewState {
  option: PrintingOption;
  anchor: CardPreviewAnchor;
}

interface PrintingDialogProps {
  card: CardEntry;
  onClose: () => void;
  onSelect: (option: PrintingOption) => void;
}

function PrintingImage({ option }: { option: PrintingOption }) {
  if (!option.image_url) {
    return (
      <span className="printing-image printing-image-empty">{option.name}</span>
    );
  }
  return (
    <span
      className={`printing-faces ${option.image_back_url ? "has-back" : ""}`}
    >
      <img
        src={option.image_url}
        alt={option.face_names[0] ?? option.name}
        loading="lazy"
      />
      {option.image_back_url && (
        <img
          src={option.image_back_url}
          alt={option.face_names[1] ?? "Back face"}
          loading="lazy"
          className="printing-back"
        />
      )}
    </span>
  );
}

export function PrintingDialog({
  card,
  onClose,
  onSelect,
}: PrintingDialogProps) {
  const [scope, setScope] = useState<PrintingScope>("artworks");
  const [result, setResult] = useState<PrintingsResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewState | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getPrintings(card.printing_id, scope)
      .then((response) => {
        if (!cancelled) setResult(response);
      })
      .catch((reason: unknown) => {
        if (!cancelled)
          setError(
            reason instanceof Error
              ? reason.message
              : "Printings could not be loaded.",
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [card.printing_id, scope]);

  useEffect(() => {
    if (!preview) return;
    function dismiss() {
      setPreview(null);
    }
    window.addEventListener("scroll", dismiss, true);
    window.addEventListener("resize", dismiss);
    return () => {
      window.removeEventListener("scroll", dismiss, true);
      window.removeEventListener("resize", dismiss);
    };
  }, [preview]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose]);

  function choose(option: PrintingOption) {
    onSelect(option);
    onClose();
  }

  function showPreview(option: PrintingOption, element: HTMLElement) {
    if (!option.image_url) {
      setPreview(null);
      return;
    }
    const rect = element.getBoundingClientRect();
    setPreview({
      option,
      anchor: {
        top: rect.top,
        bottom: rect.bottom,
        left: rect.left,
        right: rect.right,
      },
    });
  }

  return createPortal(
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="printing-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="printing-title"
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">Printing picker</p>
            <h2 id="printing-title">{card.name}</h2>
            <p>
              One choice applies to all {card.count}{" "}
              {card.count === 1 ? "copy" : "copies"}. Hover over a printing to
              see it larger.
            </p>
          </div>
          <button
            className="icon-button"
            type="button"
            onClick={onClose}
            aria-label="Close printing picker"
          >
            <CloseIcon />
          </button>
        </header>

        <div className="dialog-toolbar">
          <div className="segmented" role="tablist" aria-label="Printing view">
            <button
              type="button"
              role="tab"
              aria-selected={scope === "artworks"}
              className={scope === "artworks" ? "is-active" : ""}
              onClick={() => setScope("artworks")}
            >
              Unique artworks
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={scope === "all"}
              className={scope === "all" ? "is-active" : ""}
              onClick={() => setScope("all")}
            >
              All printings
            </button>
          </div>
          <span className="dialog-count">
            {result
              ? `${result.options.length} option${result.options.length === 1 ? "" : "s"}`
              : ""}
          </span>
        </div>

        <div className="dialog-body">
          {loading && (
            <div className="printing-loading">
              <SpinnerIcon />
              <span>Finding printings…</span>
            </div>
          )}

          {error && <p className="form-error">{error}</p>}

          {!loading && !error && result && result.options.length === 0 && (
            <p className="empty-copy">
              No alternative printings were found for this card.
            </p>
          )}

          {!loading && result && (
            <div className="printing-grid">
              {result.options.map((option) => {
                const selected = option.id === card.printing_id;
                return (
                  <button
                    key={option.id}
                    type="button"
                    className={`printing-option ${selected ? "is-selected" : ""}`}
                    onClick={() => choose(option)}
                    onMouseEnter={(event) =>
                      showPreview(option, event.currentTarget)
                    }
                    onMouseLeave={() => setPreview(null)}
                    onFocus={(event) => {
                      if (
                        !event.currentTarget.contains(
                          event.relatedTarget as Node | null,
                        )
                      ) {
                        showPreview(option, event.currentTarget);
                      }
                    }}
                    onBlur={(event) => {
                      if (
                        !event.currentTarget.contains(
                          event.relatedTarget as Node | null,
                        )
                      ) {
                        setPreview(null);
                      }
                    }}
                    aria-pressed={selected}
                  >
                    <span className="printing-choice-mark">
                      {selected ? (
                        <CheckIcon />
                      ) : option.is_recommended ? (
                        "Recommended"
                      ) : null}
                    </span>
                    <PrintingImage option={option} />
                    <span className="printing-meta">
                      <strong>
                        {option.set_code} · {option.collector_number}
                      </strong>
                      <span>
                        {option.set_name}
                        {option.released_at
                          ? ` · ${option.released_at.slice(0, 4)}`
                          : ""}
                      </span>
                      <span className="printing-subline">
                        {option.rarity}
                        {option.image_back_url ? " · double-faced" : ""}
                      </span>
                      {(option.low_res || option.non_english) && (
                        <span className="printing-warning">
                          <WarningIcon />
                          {[
                            option.low_res ? "Low-resolution" : "",
                            option.non_english ? "Non-English" : "",
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <footer className="dialog-footer">
          <p>
            Recommended printings use high-resolution English scans with a
            standard black border when available.
          </p>
        </footer>
      </div>

      {preview && preview.option.image_url && (
        <CardPreview
          anchor={preview.anchor}
          imageUrl={preview.option.image_url}
          imageBackUrl={preview.option.image_back_url}
          elevated
        />
      )}
    </div>,
    document.body,
  );
}

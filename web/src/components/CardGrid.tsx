import { useEffect, useState } from "react";
import { CardPreview, type CardPreviewAnchor } from "./CardPreview";
import {
  CardStackIcon,
  MinusIcon,
  PlusIcon,
  SparkIcon,
  TrashIcon,
  WarningIcon,
} from "./Icons";
import type { CardEntry, PrintOptions } from "../types";

interface PreviewState {
  card: CardEntry;
  anchor: CardPreviewAnchor;
}

interface CardGridProps {
  cards: CardEntry[];
  options: PrintOptions;
  onQuantity: (key: string, count: number) => void;
  onRemove: (key: string) => void;
  onChoosePrinting: (card: CardEntry) => void;
  onReplace: (card: CardEntry) => void;
  onFiltersChange: (
    patch: Pick<PrintOptions, "no_basic_lands" | "no_tokens">,
  ) => void;
  locked?: boolean;
}

function clampCount(value: number): number {
  if (!Number.isFinite(value)) return 1;
  return Math.max(1, Math.min(999, Math.round(value)));
}

export function CardGrid({
  cards,
  options,
  onQuantity,
  onRemove,
  onChoosePrinting,
  onReplace,
  onFiltersChange,
  locked = false,
}: CardGridProps) {
  const [preview, setPreview] = useState<PreviewState | null>(null);

  useEffect(() => {
    if (!preview) return;
    function dismiss() {
      setPreview(null);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") dismiss();
    }
    window.addEventListener("scroll", dismiss, true);
    window.addEventListener("resize", dismiss);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("scroll", dismiss, true);
      window.removeEventListener("resize", dismiss);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [preview]);

  function showPreview(card: CardEntry, element: HTMLElement) {
    if (!card.image_url) {
      setPreview(null);
      return;
    }
    const rect = element.getBoundingClientRect();
    setPreview({
      card,
      anchor: {
        top: rect.top,
        bottom: rect.bottom,
        left: rect.left,
        right: rect.right,
      },
    });
  }

  const included = cards.filter(
    (card) =>
      !(options.no_basic_lands && card.is_basic_land) &&
      !(options.no_tokens && card.is_token),
  );
  const selectedCount = included.reduce((total, card) => total + card.count, 0);

  return (
    <section
      className="cards-section"
      aria-labelledby="cards-heading"
      id="cards"
    >
      <div className="cards-toolbar">
        <div>
          <p className="eyebrow">Step 2</p>
          <h2 id="cards-heading">Choose your printings</h2>
          <p className="section-copy">
            Hover over a card to inspect it up close. Click any card to change
            its artwork — your choice applies to every copy. Use Replace to swap
            the card itself.
          </p>
        </div>
        <div className="card-totals">
          <strong>{selectedCount}</strong>
          <span>cards in output</span>
        </div>
      </div>

      <div className="filter-row" aria-label="Card filters">
        <label className="filter-chip">
          <input
            type="checkbox"
            checked={options.no_basic_lands}
            disabled={locked}
            onChange={(event) =>
              onFiltersChange({
                no_basic_lands: event.target.checked,
                no_tokens: options.no_tokens,
              })
            }
          />
          <span>Exclude basic lands</span>
        </label>
        <label className="filter-chip">
          <input
            type="checkbox"
            checked={options.no_tokens}
            disabled={locked}
            onChange={(event) =>
              onFiltersChange({
                no_basic_lands: options.no_basic_lands,
                no_tokens: event.target.checked,
              })
            }
          />
          <span>Exclude tokens</span>
        </label>
        <span className="filter-note">
          Filters hide cards from the output without deleting them.
        </span>
      </div>

      {cards.length === 0 ? (
        <div className="empty-state">
          <CardStackIcon />
          <strong>Your cards will appear here</strong>
          <span>Load a decklist above to start choosing printings.</span>
        </div>
      ) : (
        <div className="card-grid">
          {cards.map((card) => {
            const excluded =
              (options.no_basic_lands && card.is_basic_land) ||
              (options.no_tokens && card.is_token);
            const warningTitle = card.warnings
              .map((warning) => warning.message)
              .join("\n");
            return (
              <article
                key={card.key}
                className={`card-tile ${excluded ? "is-excluded" : ""}`}
                onMouseEnter={(event) => showPreview(card, event.currentTarget)}
                onMouseLeave={() => setPreview(null)}
                onFocus={(event) => {
                  if (
                    !event.currentTarget.contains(
                      event.relatedTarget as Node | null,
                    )
                  ) {
                    showPreview(card, event.currentTarget);
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
                onClick={() => setPreview(null)}
              >
                <button
                  className="card-art-button"
                  type="button"
                  onClick={() => onChoosePrinting(card)}
                  aria-label={`Choose a printing for ${card.name}`}
                  disabled={locked}
                >
                  {card.image_url ? (
                    <img
                      src={card.image_url}
                      alt={card.name}
                      loading="lazy"
                      className="card-art"
                    />
                  ) : (
                    <span className="card-art card-art-placeholder">
                      {card.name}
                    </span>
                  )}
                  {card.face_names.length > 1 && (
                    <span className="card-flag">2 faces</span>
                  )}
                  {excluded && (
                    <span className="excluded-banner">
                      {card.is_basic_land
                        ? "Basic land excluded"
                        : "Token excluded"}
                    </span>
                  )}
                </button>

                <div className="card-tile-body">
                  <button
                    className="card-name"
                    type="button"
                    onClick={() => onChoosePrinting(card)}
                    title={card.name}
                    disabled={locked}
                  >
                    {card.name}
                  </button>
                  <p className="card-printing">
                    {card.set_code} · {card.collector_number}
                    {card.released_at && (
                      <span> · {card.released_at.slice(0, 4)}</span>
                    )}
                  </p>

                  {(card.low_res ||
                    card.non_english ||
                    card.warnings.length > 0) && (
                    <div className="card-warnings">
                      {card.low_res && (
                        <span className="warning-chip">Low-res</span>
                      )}
                      {card.non_english && (
                        <span className="warning-chip">Non-English</span>
                      )}
                      {card.warnings.length > 0 && (
                        <span
                          title={warningTitle}
                          className="warning-icon"
                          aria-label={warningTitle}
                        >
                          <WarningIcon />
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <div className="card-controls">
                  <div
                    className="quantity"
                    aria-label={`Quantity for ${card.name}`}
                  >
                    <button
                      type="button"
                      aria-label="Decrease quantity"
                      disabled={locked || card.count <= 1}
                      onClick={() =>
                        onQuantity(card.key, clampCount(card.count - 1))
                      }
                    >
                      <MinusIcon />
                    </button>
                    <input
                      type="number"
                      min={1}
                      max={999}
                      value={card.count}
                      aria-label={`Copies of ${card.name}`}
                      disabled={locked}
                      onChange={(event) =>
                        onQuantity(
                          card.key,
                          clampCount(Number(event.target.value)),
                        )
                      }
                    />
                    <button
                      type="button"
                      aria-label="Increase quantity"
                      disabled={locked || card.count >= 999}
                      onClick={() =>
                        onQuantity(card.key, clampCount(card.count + 1))
                      }
                    >
                      <PlusIcon />
                    </button>
                  </div>
                  <button
                    className="remove-card"
                    type="button"
                    aria-label={`Remove ${card.name}`}
                    title="Remove card"
                    onClick={() => onRemove(card.key)}
                    disabled={locked}
                  >
                    <TrashIcon />
                  </button>
                </div>

                <button
                  className="replace-card"
                  type="button"
                  title={`Ask Kimi for a card with the same effect as ${card.name}`}
                  onClick={() => onReplace(card)}
                  disabled={locked}
                >
                  <SparkIcon />
                  Replace
                </button>
              </article>
            );
          })}
        </div>
      )}

      {preview && preview.card.image_url && (
        <CardPreview
          anchor={preview.anchor}
          imageUrl={preview.card.image_url}
          imageBackUrl={preview.card.image_back_url}
        />
      )}
    </section>
  );
}

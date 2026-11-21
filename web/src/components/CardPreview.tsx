import { useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export interface CardPreviewAnchor {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

interface CardPreviewProps {
  anchor: CardPreviewAnchor;
  imageUrl: string;
  imageBackUrl: string | null;
  elevated?: boolean;
}

const VIEWPORT_MARGIN = 16;
const ANCHOR_GAP = 14;

export function CardPreview({
  anchor,
  imageUrl,
  imageBackUrl,
  elevated = false,
}: CardPreviewProps) {
  const frameRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{
    left: number;
    top: number;
  } | null>(null);

  useLayoutEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const { width, height } = frame.getBoundingClientRect();
    const viewWidth = window.innerWidth;
    const viewHeight = window.innerHeight;

    let left: number;
    if (anchor.right + ANCHOR_GAP + width <= viewWidth - VIEWPORT_MARGIN) {
      left = anchor.right + ANCHOR_GAP;
    } else if (anchor.left - ANCHOR_GAP - width >= VIEWPORT_MARGIN) {
      left = anchor.left - ANCHOR_GAP - width;
    } else {
      left = (viewWidth - width) / 2;
    }
    left = Math.max(
      VIEWPORT_MARGIN,
      Math.min(left, viewWidth - width - VIEWPORT_MARGIN),
    );

    const centeredTop = anchor.top + (anchor.bottom - anchor.top - height) / 2;
    const top = Math.max(
      VIEWPORT_MARGIN,
      Math.min(centeredTop, viewHeight - height - VIEWPORT_MARGIN),
    );

    setPosition({ left, top });
  }, [anchor, imageBackUrl]);

  return createPortal(
    <div
      ref={frameRef}
      className={`card-preview ${imageBackUrl ? "has-back" : ""} ${elevated ? "is-elevated" : ""}`}
      style={position ?? { visibility: "hidden" }}
      aria-hidden="true"
    >
      <img
        className="card-preview-face"
        src={imageUrl}
        alt=""
        draggable={false}
      />
      {imageBackUrl && (
        <img
          className="card-preview-face"
          src={imageBackUrl}
          alt=""
          draggable={false}
        />
      )}
    </div>,
    document.body,
  );
}

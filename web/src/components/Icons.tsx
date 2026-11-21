import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function base(props: IconProps) {
  return {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    ...props,
  };
}

export function LogoMark(props: IconProps) {
  return (
    <svg viewBox="0 0 40 40" aria-hidden="true" {...props}>
      <rect width="40" height="40" rx="11" fill="currentColor" />
      <rect x="12" y="7" width="16" height="24" rx="2.5" fill="#f5f1e6" />
      <rect
        x="9"
        y="10"
        width="16"
        height="24"
        rx="2.5"
        fill="#f5f1e6"
        opacity="0.55"
      />
      <rect x="11.5" y="8.5" width="16" height="24" rx="2.5" fill="#f5f1e6" />
      <path
        d="M15.5 14h8M15.5 18h8M15.5 22h5"
        stroke="#0f6b5c"
        strokeWidth="1.7"
      />
    </svg>
  );
}

export function CardStackIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="7" y="3" width="12" height="17" rx="2" />
      <path d="M5 6v13a2 2 0 0 0 2 2h9" />
    </svg>
  );
}

export function UploadIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5" />
      <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
    </svg>
  );
}

export function SparkIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3l1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3Z" />
      <path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" />
    </svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function MinusIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M5 12h14" />
    </svg>
  );
}

export function TrashIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 7h16M9 7V5h6v2M6.5 7l.8 13h9.4l.8-13" />
      <path d="M10 11v5M14 11v5" />
    </svg>
  );
}

export function PrintIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M7 9V4h10v5" />
      <rect x="4" y="9" width="16" height="8" rx="2" />
      <path d="M7 14h10v6H7z" />
      <path d="M17 12h.01" />
    </svg>
  );
}

export function ArchiveIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 7h16v3H4z" />
      <path d="M6 10v9h12v-9" />
      <path d="M9.5 14h5" />
    </svg>
  );
}

export function DownloadIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 4v12m0 0l-4.5-4.5M12 16l4.5-4.5" />
      <path d="M4 19h16" />
    </svg>
  );
}

export function ScissorsIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="6" cy="7" r="2.5" />
      <circle cx="6" cy="17" r="2.5" />
      <path d="M8.2 8.2L20 19M8.2 15.8L20 5" />
    </svg>
  );
}

export function WarningIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 4L3.5 19h17L12 4Z" />
      <path d="M12 9v5M12 17h.01" />
    </svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4.5 12.5l5 5L20 7" />
    </svg>
  );
}

export function UsbIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3v13" />
      <path d="M8 6l4-3 4 3M8 9l4-3 4 3" />
      <rect x="9" y="16" width="6" height="5" rx="1.5" />
    </svg>
  );
}

export function RefreshIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M20 11a8 8 0 1 0-2.3 5.7" />
      <path d="M20 4v7h-7" />
    </svg>
  );
}

export function ChevronIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M7 10l5 5 5-5" />
    </svg>
  );
}

export function InfoIcon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7h.01" />
    </svg>
  );
}

export function SpinnerIcon(props: IconProps) {
  return (
    <svg {...base(props)} className={`spin ${props.className ?? ""}`}>
      <path d="M12 3a9 9 0 1 1-6.4 2.6" />
    </svg>
  );
}

import { useEffect, useState } from "react";
import { fileUrl, getCutterDevices, sendToCutter } from "../api";
import type {
  CutterDevice,
  OutputState,
  PrintMode,
  SendToCutterResult,
} from "../types";
import {
  CheckIcon,
  DownloadIcon,
  InfoIcon,
  PrintIcon,
  RefreshIcon,
  ScissorsIcon,
  SpinnerIcon,
  UsbIcon,
  WarningIcon,
} from "./Icons";

interface OutputPanelProps {
  output: OutputState;
  mode: PrintMode;
  onPrint: (url: string) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function OutputPanel({ output, mode, onPrint }: OutputPanelProps) {
  const { jobId, result } = output;
  const pdf = result.artifacts.find((artifact) => artifact.kind === "pdf");
  const svgs = result.artifacts.filter((artifact) => artifact.kind === "svg");
  const plt = result.artifacts.find((artifact) => artifact.kind === "plt");

  return (
    <section
      className="output-section"
      aria-labelledby="output-heading"
      id="outputs"
    >
      <div className="output-heading">
        <div>
          <p className="eyebrow">Step 4</p>
          <h2 id="output-heading">Your print files are ready</h2>
          <p className="section-copy">{result.layout}</p>
        </div>
        <div className="output-facts">
          <span>
            <strong>{result.card_count}</strong> cards
          </span>
          <span>
            <strong>{result.pages}</strong> page{result.pages === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      {result.filters.length > 0 && (
        <ul className="filter-summary">
          {result.filters.map((filter) => (
            <li key={filter}>
              <CheckIcon />
              {filter}
            </li>
          ))}
        </ul>
      )}

      <div className="file-layout">
        {pdf && (
          <div className="file-primary">
            <div className="file-icon">
              <ScissorsIcon />
            </div>
            <div>
              <strong>{pdf.filename}</strong>
              <span>{formatBytes(pdf.size)} · print at 100% / Actual size</span>
            </div>
            <div className="file-actions">
              <button
                className="button button-primary"
                type="button"
                onClick={() => onPrint(fileUrl(jobId, pdf.id))}
              >
                <PrintIcon />
                Print PDF
              </button>
              <a
                className="button button-secondary"
                href={fileUrl(jobId, pdf.id, true)}
              >
                <DownloadIcon />
                Download
              </a>
            </div>
          </div>
        )}

        {(svgs.length > 0 || plt) && (
          <div className="cut-files">
            <h3>Cut files</h3>
            {svgs.map((artifact) => (
              <a
                className="cut-file-row"
                key={artifact.id}
                href={fileUrl(jobId, artifact.id, true)}
              >
                <ScissorsIcon />
                <span>
                  <strong>{artifact.label}</strong>
                  <small>
                    {artifact.filename} · {formatBytes(artifact.size)}
                  </small>
                </span>
                <DownloadIcon />
              </a>
            ))}
            {plt && (
              <a className="cut-file-row" href={fileUrl(jobId, plt.id, true)}>
                <UsbIcon />
                <span>
                  <strong>{plt.label}</strong>
                  <small>
                    {plt.filename} · {formatBytes(plt.size)}
                  </small>
                </span>
                <DownloadIcon />
              </a>
            )}
          </div>
        )}
      </div>

      <div className="print-note">
        <InfoIcon />
        <p>
          In the Brave print dialog, choose the same paper size and set scale to{" "}
          <strong>100% / Actual size</strong>. Disable “Fit to page” or any
          shrink-to-fit option.
          <a
            href={pdf ? fileUrl(jobId, pdf.id) : undefined}
            target="_blank"
            rel="noreferrer"
          >
            Open the PDF in a new tab
          </a>
        </p>
      </div>

      {mode === "makercraft" && plt && <CutterPanel jobId={jobId} />}
    </section>
  );
}

function CutterPanel({ jobId }: { jobId: string }) {
  const [devices, setDevices] = useState<CutterDevice[]>([]);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string>("");
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<SendToCutterResult | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  function refreshDevices() {
    setLoading(true);
    setDiscoveryError(null);
    getCutterDevices()
      .then((result) => {
        setDevices(result.devices);
        setDiscoveryError(result.error);
        if (result.devices.length === 1) {
          setSelected(result.devices[0].label);
        }
      })
      .catch((error: unknown) => {
        setDevices([]);
        setDiscoveryError(
          error instanceof Error
            ? error.message
            : "The cutter could not be checked.",
        );
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    setSendResult(null);
    setSendError(null);
    setSelected("");
    refreshDevices();
    // Discovery should run again only when a different generation is displayed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  async function handleSend() {
    const device = devices.length === 1 ? devices[0].label : selected;
    if (!device) return;
    const confirmed = window.confirm(
      `Send one MakerCraft sheet to “${device}”?\n\nMake sure the printed sheet is loaded and aligned. The template is reused for every page, so send it once per sheet.`,
    );
    if (!confirmed) return;

    setSending(true);
    setSendError(null);
    setSendResult(null);
    try {
      const result = await sendToCutter(jobId, device);
      setSendResult(result);
    } catch (error) {
      setSendError(
        error instanceof Error
          ? error.message
          : "The cut job could not be sent.",
      );
    } finally {
      setSending(false);
    }
  }

  const canSend =
    !sending &&
    devices.length > 0 &&
    (devices.length === 1 || selected.length > 0);

  return (
    <section className="cutter-panel" aria-labelledby="cutter-heading">
      <div className="cutter-heading">
        <span className="icon-badge">
          <UsbIcon />
        </span>
        <div>
          <h3 id="cutter-heading">Send to cutter</h3>
          <p>
            MakerCraft / Skycut C10 over USB. Uses the force and speed set on
            the cutter panel.
          </p>
        </div>
        <button
          className="icon-button"
          type="button"
          onClick={refreshDevices}
          title="Check for the cutter again"
          aria-label="Check for the cutter again"
          disabled={loading || sending}
        >
          <RefreshIcon />
        </button>
      </div>

      {loading && (
        <div className="cutter-status">
          <SpinnerIcon />
          Checking the USB connection…
        </div>
      )}

      {!loading && discoveryError && (
        <div className="cutter-status is-error">
          <WarningIcon />
          {discoveryError}
        </div>
      )}

      {!loading && !discoveryError && devices.length === 0 && (
        <div className="cutter-status">
          <WarningIcon />
          No compatible cutter found. Connect it by USB and check again.
        </div>
      )}

      {!loading && devices.length > 0 && (
        <div className="cutter-controls">
          {devices.length > 1 ? (
            <label className="field">
              <span className="field-label">Cutter</span>
              <select
                value={selected}
                onChange={(event) => setSelected(event.target.value)}
              >
                <option value="">Choose a device…</option>
                {devices.map((device) => (
                  <option key={device.label} value={device.label}>
                    {device.label}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p className="device-label">
              <CheckIcon />
              {devices[0].label}
            </p>
          )}
          <button
            className="button button-secondary"
            type="button"
            onClick={handleSend}
            disabled={!canSend}
          >
            {sending ? <SpinnerIcon /> : <ScissorsIcon />}
            {sending ? "Sending…" : "Send one sheet"}
          </button>
        </div>
      )}

      {sendResult && (
        <p className="cutter-success">
          <CheckIcon />
          {sendResult.message}
        </p>
      )}
      {sendError && (
        <p className="cutter-error">
          <WarningIcon />
          {sendError}
        </p>
      )}
      <p className="cutter-footnote">
        The same template cuts every page. Print one sheet, send it once, then
        repeat. Keep hands clear of the carriage.
      </p>
    </section>
  );
}

import type {
  CutterDevicesResult,
  GeneratePayload,
  GenerationResult,
  ImportResult,
  Job,
  PrintingsResult,
  PrintingScope,
  ReplacementRequest,
  ReplacementSettings,
  SendToCutterResult,
} from "./types";

class ApiError extends Error {}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String(item.msg);
        }
        return String(item);
      })
      .join(" ");
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String(detail.message);
  }
  return "The request could not be completed.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = response.statusText || "Request failed";
    try {
      const body = (await response.json()) as { detail?: unknown };
      message = formatDetail(body.detail ?? message);
    } catch {
      // Keep the HTTP status message.
    }
    throw new ApiError(message);
  }

  return (await response.json()) as T;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export function startImport(text: string): Promise<{ job_id: string }> {
  return post("/api/import", { text });
}

export function startGeneration(
  payload: GeneratePayload,
): Promise<{ job_id: string }> {
  return post("/api/generate", payload);
}

export function getJob<T>(jobId: string): Promise<Job<T>> {
  return request(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function getPrintings(
  printingId: string,
  scope: PrintingScope,
): Promise<PrintingsResult> {
  return post("/api/printings", { printing_id: printingId, scope });
}

export function startReplacementSuggestions(
  payload: ReplacementRequest,
): Promise<{ job_id: string }> {
  return post("/api/replace/suggestions", payload);
}

export function getReplacementSettings(): Promise<ReplacementSettings> {
  return request("/api/replace/settings");
}

export function saveReplacementKey(
  apiKey: string,
): Promise<ReplacementSettings> {
  return request("/api/replace/settings", {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey }),
  });
}

export function clearReplacementKey(): Promise<ReplacementSettings> {
  return request("/api/replace/settings", { method: "DELETE" });
}

export function getCutterDevices(): Promise<CutterDevicesResult> {
  return request("/api/cutter/devices");
}

export function sendToCutter(
  jobId: string,
  device: string | null,
): Promise<SendToCutterResult> {
  return post("/api/cutter/send", { job_id: jobId, device });
}

export function fileUrl(
  jobId: string,
  artifactId: string,
  download = false,
): string {
  const suffix = download ? "?download=true" : "";
  return `/api/jobs/${encodeURIComponent(jobId)}/files/${encodeURIComponent(artifactId)}${suffix}`;
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "Something went wrong.";
}

function delay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    let timer = 0;
    function abort() {
      window.clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    }
    timer = window.setTimeout(() => {
      signal?.removeEventListener("abort", abort);
      resolve();
    }, milliseconds);
    signal?.addEventListener("abort", abort, { once: true });
  });
}

export async function waitForJob<T>(
  jobId: string,
  onUpdate: (job: Job<T>) => void,
  signal?: AbortSignal,
): Promise<Job<T>> {
  for (;;) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    const job = await getJob<T>(jobId);
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    onUpdate(job);
    if (job.status === "succeeded" || job.status === "failed") {
      return job;
    }
    await delay(700, signal);
  }
}

export function pendingJob<T>(kind: "import" | "generate" | "suggest"): Job<T> {
  return {
    id: "",
    kind,
    status: "queued",
    stage: "Queued",
    message: "Waiting for a worker…",
    completed: 0,
    total: 0,
    error: null,
    result: null,
  };
}

export function completedImport(job: Job<ImportResult>): ImportResult {
  if (job.status === "failed") {
    throw new ApiError(job.error ?? "The decklist could not be read.");
  }
  if (!job.result) {
    throw new ApiError("The import finished without a result.");
  }
  return job.result;
}

export function completedGeneration(
  job: Job<GenerationResult>,
): GenerationResult {
  if (job.status === "failed") {
    throw new ApiError(job.error ?? "The print files could not be generated.");
  }
  if (!job.result) {
    throw new ApiError("Generation finished without any files.");
  }
  return job.result;
}

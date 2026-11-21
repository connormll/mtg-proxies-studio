import { SpinnerIcon } from "./Icons";
import type { Job } from "../types";

interface ProgressViewProps {
  job: Job<unknown> | null;
  busy: boolean;
  label?: string;
}

export function ProgressView({
  job,
  busy,
  label = "Working",
}: ProgressViewProps) {
  if (!busy && !job) return null;

  const total = job?.total ?? 0;
  const completed = job?.completed ?? 0;
  const determinate = total > 0;
  const percentage = determinate
    ? Math.min(100, Math.round((completed / total) * 100))
    : 0;
  const stage =
    job?.status === "failed" ? "Something went wrong" : (job?.stage ?? label);
  const message = job?.message ?? "Starting a background job…";

  return (
    <div
      className={`job-progress ${job?.status === "failed" ? "is-error" : ""}`}
      aria-live="polite"
    >
      <div className="job-progress-heading">
        <SpinnerIcon className={job?.status === "failed" ? "icon-error" : ""} />
        <div>
          <strong>{stage}</strong>
          {message && <span>{message}</span>}
        </div>
        {determinate && <span className="job-percent">{percentage}%</span>}
      </div>
      <div
        className={`progress-track ${determinate ? "" : "is-indeterminate"}`}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={determinate ? 100 : undefined}
        aria-valuenow={determinate ? percentage : undefined}
      >
        <div
          className="progress-fill"
          style={determinate ? { width: `${percentage}%` } : undefined}
        />
      </div>
    </div>
  );
}

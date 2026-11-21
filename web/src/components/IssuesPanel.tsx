import { WarningIcon } from "./Icons";
import type { ImportIssue } from "../types";

interface IssuesPanelProps {
  issues: ImportIssue[];
}

function isSkipped(issue: ImportIssue): boolean {
  // `skipped` is always set by current imports. The message check keeps older
  // API responses from showing a missing card as a blocking error.
  return issue.skipped || issue.message.startsWith("Unable to find card ");
}

export function IssuesPanel({ issues }: IssuesPanelProps) {
  if (issues.length === 0) return null;
  const skipped = issues.filter(isSkipped).length;
  const errors = issues.filter(
    (issue) => issue.severity === "error" && !isSkipped(issue),
  ).length;
  const warnings = issues.length - errors - skipped;
  const notes = [
    warnings > 0
      ? `${warnings} warning${warnings === 1 ? "" : "s"}`
      : "",
    skipped > 0 ? `${skipped} skipped` : "",
  ].filter(Boolean);

  return (
    <section
      className={`issues-panel ${errors > 0 ? "has-errors" : ""}`}
      aria-live="polite"
    >
      <div className="issues-heading">
        <WarningIcon />
        <strong>
          {errors > 0
            ? `${errors} line${errors === 1 ? "" : "s"} need attention`
            : skipped > 0
              ? `${skipped} line${skipped === 1 ? "" : "s"} skipped`
              : "Decklist notes"}
        </strong>
        {notes.length > 0 && <span>{notes.join(" · ")}</span>}
      </div>
      <ul className="issues-list">
        {issues.map((issue, index) => (
          <li
            key={`${issue.line}-${index}-${issue.message}`}
            className={issue.severity}
          >
            <span className="issue-line">
              {issue.line > 0 ? `Line ${issue.line}` : "Decklist"}
            </span>
            <div>
              <p>{issue.message}</p>
              {issue.text && <code>{issue.text}</code>}
            </div>
          </li>
        ))}
      </ul>
      {skipped > 0 && (
        <p className="issues-footnote">
          Skipped lines are left out of the print files. Everything else can
          still be generated.
        </p>
      )}
      {errors > 0 && (
        <p className="issues-footnote">
          Fix the affected lines in the decklist editor and load the list again.
        </p>
      )}
    </section>
  );
}

"""Decklist import for the local web interface."""

from __future__ import annotations

import re

import mtg_proxies.scryfall as scryfall
from mtg_proxies.decklists import validate_card_name, validate_print
from mtg_proxies.gui.cards import card_summary
from mtg_proxies.gui.models import CardSummary, ImportIssue, ImportResult
from mtg_proxies.gui.progress import ProgressReporter

_CARD_LINE_RE = re.compile(r"([0-9]+)x?\s+(.+?)(?:\s+\((\S*)\)\s+(\S+))?\s*$")


def _issue(line_number: int, text: str, message: str, severity: str, *, skipped: bool = False) -> ImportIssue:
    """Build one line-level import diagnostic."""
    return ImportIssue(
        line=line_number,
        text=text,
        message=message,
        severity="error" if severity == "ERROR" else "warning",
        skipped=skipped,
    )


def import_decklist(text: str, report: ProgressReporter) -> ImportResult:
    """Parse decklist text into unique cards and line-level diagnostics.

    The parser accepts the same text and Arena formats as the CLI. Cards that
    resolve are returned even when other lines contain errors, so the editor
    can show both the usable list and the lines that need attention.
    """
    report("Loading Scryfall data", 0, 0, "The local card database is being prepared.")
    scryfall.get_cards()

    lines = text.splitlines()
    card_line_numbers = [index for index, line in enumerate(lines, start=1) if _CARD_LINE_RE.search(line)]
    total = len(card_line_numbers)
    report("Reading decklist", 0, total, "")

    merged: dict[str, CardSummary] = {}
    issues: list[ImportIssue] = []
    completed = 0

    for line_number, line in enumerate(lines, start=1):
        match = _CARD_LINE_RE.search(line)
        if match is None:
            continue

        count = int(match.group(1))
        raw_name = match.group(2)
        set_id = match.group(3)
        collector_number = match.group(4)

        card_name, name_warnings = validate_card_name(raw_name)
        if card_name is None:
            # One unresolved card should not block the cards that did resolve.
            # The line is skipped and reported as a warning, so the rest of the
            # deck can still be generated.
            issues.extend(
                _issue(line_number, line, f"{warning.message} Skipped this line.", "WARNING", skipped=True)
                for warning in name_warnings
            )
            if not name_warnings:
                issues.append(
                    _issue(
                        line_number,
                        line,
                        f"Unable to find card {raw_name!r}. Skipped this line.",
                        "WARNING",
                        skipped=True,
                    )
                )
            completed += 1
            report("Reading decklist", completed, total, line.strip())
            continue
        issues.extend(_issue(line_number, line, str(warning.message), warning.level) for warning in name_warnings)

        card, print_warnings = validate_print(card_name, set_id, collector_number)
        issues.extend(_issue(line_number, line, str(warning.message), warning.level) for warning in print_warnings)

        summary = card_summary(card, count=count, source_lines=[line_number])
        if summary.key in merged:
            previous = merged[summary.key]
            merged[summary.key] = previous.model_copy(
                update={
                    "count": previous.count + summary.count,
                    "source_lines": sorted({*previous.source_lines, *summary.source_lines}),
                }
            )
        else:
            merged[summary.key] = summary

        completed += 1
        report("Reading decklist", completed, total, line.strip())

    cards = list(merged.values())
    if not cards:
        message = (
            "None of the card lines could be resolved. Check the flagged lines and try again."
            if card_line_numbers
            else "No card lines were found. Use one card per line, for example '1 Sol Ring'."
        )
        issues.append(ImportIssue(line=0, text="", message=message, severity="error"))

    report("Import complete", total, total, f"Found {sum(card.count for card in cards)} cards.")
    return ImportResult(cards=cards, issues=issues, total_count=sum(card.count for card in cards))

"""Progress reporting shared by background GUI jobs."""

from collections.abc import Callable

type ProgressReporter = Callable[[str, int, int, str], None]
"""Report a stage, completed units, total units, and an optional detail."""


def noop_progress(stage: str, completed: int, total: int, detail: str) -> None:
    """Ignore a progress update."""

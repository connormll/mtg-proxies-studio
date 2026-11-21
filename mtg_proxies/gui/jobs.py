"""In-memory background jobs for imports and print generation."""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from mtg_proxies.gui.models import JobKind, JobSnapshot, JobStatus
from mtg_proxies.gui.progress import ProgressReporter

logger = logging.getLogger(__name__)

type JobTarget = Callable[[Path, ProgressReporter], dict[str, Any]]

_JOB_MAX_AGE_SECONDS = 24 * 60 * 60


@dataclass(slots=True)
class _Job:
    """Mutable state of one background job."""

    id: str
    kind: JobKind
    status: JobStatus = "queued"
    stage: str = "Queued"
    message: str = ""
    completed: int = 0
    total: int = 0
    error: str | None = None
    result: dict[str, Any] | None = None
    directory: Path = field(default_factory=Path)


class JobManager:
    """Run short-lived local jobs and expose their progress in memory."""

    def __init__(self, root: Path | None = None, *, max_workers: int = 2) -> None:
        """Create a job manager, optionally rooted at an explicit output directory."""
        self.root = root or Path(tempfile.gettempdir()) / "mtg-proxies-gui"
        self.root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, _Job] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="mtg-gui")
        self._clean_old_jobs()

    def _clean_old_jobs(self) -> None:
        """Remove output folders left behind by old launches."""
        cutoff = time.time() - _JOB_MAX_AGE_SECONDS
        for path in self.root.iterdir():
            try:
                if path.is_dir() and path.stat().st_mtime < cutoff:
                    shutil.rmtree(path, ignore_errors=True)
            except OSError:
                logger.warning("Could not inspect GUI output folder %s", path, exc_info=True)

    def submit(self, kind: JobKind, target: JobTarget) -> str:
        """Queue a job and return its identifier."""
        job_id = uuid.uuid4().hex
        directory = self.root / job_id
        directory.mkdir(parents=True, exist_ok=True)
        job = _Job(id=job_id, kind=kind, directory=directory)
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run, job_id, target)
        return job_id

    def _update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        stage: str | None = None,
        message: str | None = None,
        completed: int | None = None,
        total: int | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if status is not None:
                job.status = status
            if stage is not None:
                job.stage = stage
            if message is not None:
                job.message = message
            if completed is not None:
                job.completed = completed
            if total is not None:
                job.total = total

    def _report(self, job_id: str) -> ProgressReporter:
        def report(stage: str, completed: int, total: int, detail: str) -> None:
            self._update(
                job_id,
                status="running",
                stage=stage,
                completed=completed,
                total=total,
                message=detail,
            )

        return report

    def _run(self, job_id: str, target: JobTarget) -> None:
        self._update(job_id, status="running", stage="Starting", message="")
        with self._lock:
            job = self._jobs[job_id]
        try:
            result = target(job.directory, self._report(job_id))
        except Exception as exc:
            logger.exception("GUI job %s failed", job_id)
            message = str(exc) or exc.__class__.__name__
            with self._lock:
                job.status = "failed"
                job.error = message
                job.stage = "Failed"
                job.message = message
            return

        with self._lock:
            job.status = "succeeded"
            job.stage = "Complete"
            job.message = ""
            job.result = result

    def snapshot(self, job_id: str) -> JobSnapshot | None:
        """Return a consistent copy of a job's current state."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return JobSnapshot(
                id=job.id,
                kind=job.kind,
                status=job.status,
                stage=job.stage,
                message=job.message,
                completed=job.completed,
                total=job.total,
                error=job.error,
                result=job.result,
            )

    def directory(self, job_id: str) -> Path | None:
        """Return the output directory of a job."""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.directory if job is not None else None

    def shutdown(self) -> None:
        """Stop accepting work and release worker threads."""
        self._executor.shutdown(wait=False, cancel_futures=True)

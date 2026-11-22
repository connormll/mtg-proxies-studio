"""FastAPI application for the local mtg-proxies web interface."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from mtg_proxies.gui.generation import generate_files
from mtg_proxies.gui.importer import import_decklist
from mtg_proxies.gui.jobs import JobManager
from mtg_proxies.gui.models import (
    CutterDevice,
    CutterDevicesResult,
    GenerateRequest,
    GenerationResult,
    ImportRequest,
    JobCreated,
    JobSnapshot,
    PrintingRequest,
    PrintingsResult,
    ReplacementRequest,
    ReplacementSettings,
    ReplacementSettingsUpdate,
    SendToCutterRequest,
    SendToCutterResult,
)
from mtg_proxies.gui.printings import list_printings
from mtg_proxies.gui.progress import ProgressReporter
from mtg_proxies.gui.replacements import (
    clear_opencode_api_key,
    model_name,
    opencode_api_key,
    opencode_api_key_source,
    save_opencode_api_key,
    suggest_replacements,
)
from mtg_proxies.makercraft import device_label, find_devices, send_plt

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"
_INDEX_FILE = _STATIC_DIR / "index.html"


def _missing_frontend_page() -> str:
    """Return a helpful page shown when the compiled frontend is absent."""
    return """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>mtg-proxies GUI</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 44rem; margin: 4rem auto; line-height: 1.6;">
  <h1>The GUI frontend has not been built</h1>
  <p>Run the production build once, then reload this page:</p>
  <pre style="padding: 1rem; background: #f3f3ee;"><code>cd web
npm install
npm run build</code></pre>
  <p>For frontend development, run <code>npm run dev</code> in <code>web/</code> and open the Vite URL.</p>
</body>
</html>"""


def _replacement_settings() -> ReplacementSettings:
    """Describe the configured OpenCode Go key without exposing it."""
    configured = opencode_api_key() is not None
    return ReplacementSettings(
        configured=configured,
        source=opencode_api_key_source() if configured else None,
        model=model_name(),
    )


def _generation_result(request: Request, job_id: str) -> GenerationResult:
    """Return a completed generation result or raise an HTTP error."""
    job = request.app.state.jobs.snapshot(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "succeeded" or job.result is None:
        raise HTTPException(status_code=409, detail="The job has not produced files yet.")
    if job.kind != "generate":
        raise HTTPException(status_code=400, detail="That job did not generate print files.")
    return GenerationResult.model_validate(job.result)


def create_app(job_manager: JobManager | None = None) -> FastAPI:
    """Create the local web application."""
    manager = job_manager or JobManager()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        try:
            yield
        finally:
            manager.shutdown()

    app = FastAPI(
        title="mtg-proxies GUI",
        description="Local print preparation for MTG proxies.",
        lifespan=lifespan,
    )
    app.state.jobs = manager

    @app.post("/api/import", response_model=JobCreated, status_code=202)
    def start_import(request: ImportRequest) -> JobCreated:
        """Queue a decklist import and return its job id."""
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="The decklist is empty.")

        def target(_output_dir: Path, report: ProgressReporter) -> dict[str, Any]:
            return import_decklist(text, report).model_dump(mode="json")

        return JobCreated(job_id=manager.submit("import", target))

    @app.post("/api/generate", response_model=JobCreated, status_code=202)
    def start_generation(request: GenerateRequest) -> JobCreated:
        """Queue a print generation job and return its job id."""
        if not request.cards:
            raise HTTPException(status_code=422, detail="Select at least one card before generating.")

        def target(output_dir: Path, report: ProgressReporter) -> dict[str, Any]:
            return generate_files(request, output_dir, report).model_dump(mode="json")

        return JobCreated(job_id=manager.submit("generate", target))

    @app.post("/api/replace/suggestions", response_model=JobCreated, status_code=202)
    def start_replacement_suggestions(body: ReplacementRequest) -> JobCreated:
        """Queue a Kimi replacement search for one card."""
        if opencode_api_key() is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Kimi replacement suggestions need an OpenCode Go API key. Set "
                    "OPENCODE_API_KEY before starting the GUI, then try again."
                ),
            )

        def target(_output_dir: Path, report: ProgressReporter) -> dict[str, Any]:
            return suggest_replacements(body, report).model_dump(mode="json")

        return JobCreated(job_id=manager.submit("suggest", target))

    @app.get("/api/replace/settings", response_model=ReplacementSettings)
    def get_replacement_settings() -> ReplacementSettings:
        """Report whether an OpenCode Go key is available."""
        return _replacement_settings()

    @app.put("/api/replace/settings", response_model=ReplacementSettings)
    def update_replacement_settings(body: ReplacementSettingsUpdate) -> ReplacementSettings:
        """Save an OpenCode Go key so later launches remember it."""
        try:
            save_opencode_api_key(body.api_key)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail="The OpenCode Go API key could not be saved on this computer.",
            ) from exc
        return _replacement_settings()

    @app.delete("/api/replace/settings", response_model=ReplacementSettings)
    def delete_replacement_settings() -> ReplacementSettings:
        """Forget the locally saved OpenCode Go key."""
        try:
            clear_opencode_api_key()
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail="The saved OpenCode Go API key could not be removed.",
            ) from exc
        return _replacement_settings()

    @app.get("/api/jobs/{job_id}", response_model=JobSnapshot)
    def get_job(job_id: str) -> JobSnapshot:
        """Return progress and results for a background job."""
        snapshot = manager.snapshot(job_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return snapshot

    @app.get("/api/jobs/{job_id}/files/{artifact_id}")
    def get_file(
        request: Request,
        job_id: str,
        artifact_id: str,
        download: Annotated[bool, Query()] = False,
    ) -> FileResponse:
        """Serve one generated file inline or as a download."""
        result = _generation_result(request, job_id)
        artifact = next((item for item in result.artifacts if item.id == artifact_id), None)
        if artifact is None:
            raise HTTPException(status_code=404, detail="File not found.")

        directory = manager.directory(job_id)
        if directory is None:
            raise HTTPException(status_code=404, detail="Job output has expired.")
        path = (directory / artifact.filename).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file():
            raise HTTPException(status_code=404, detail="File not found.")

        inline = artifact.kind == "pdf" and not download
        return FileResponse(
            path,
            media_type=artifact.media_type,
            filename=artifact.filename,
            content_disposition_type="inline" if inline else "attachment",
        )

    @app.post("/api/printings", response_model=PrintingsResult)
    def get_printings(request: PrintingRequest) -> PrintingsResult:
        """List alternative artworks or every printing for one card."""
        try:
            return list_printings(request.printing_id, request.scope)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/cutter/devices", response_model=CutterDevicesResult)
    def cutter_devices() -> CutterDevicesResult:
        """Discover connected MakerCraft/Skycut devices."""
        try:
            devices = find_devices()
        except Exception as exc:
            return CutterDevicesResult(devices=[], error=str(exc))

        return CutterDevicesResult(
            devices=[
                CutterDevice(label=device_label(device), bus=device.bus, address=device.address) for device in devices
            ],
            error=None,
        )

    @app.post("/api/cutter/send", response_model=SendToCutterResult)
    def cutter_send(request: Request, body: SendToCutterRequest) -> SendToCutterResult:
        """Send the generated MakerCraft template to one connected cutter."""
        result = _generation_result(request, body.job_id)
        artifact = next((item for item in result.artifacts if item.kind == "plt"), None)
        if artifact is None:
            raise HTTPException(status_code=400, detail="This job did not produce a MakerCraft template.")
        directory = manager.directory(body.job_id)
        if directory is None:
            raise HTTPException(status_code=404, detail="Job output has expired.")
        path = (directory / artifact.filename).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file():
            raise HTTPException(status_code=404, detail="MakerCraft template not found.")

        try:
            send_plt(path, yes=True, device=body.device)
        except (RuntimeError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return SendToCutterResult(ok=True, message=f"Sent {artifact.filename} to the cutter (one sheet).")

    if _STATIC_DIR.is_dir():
        assets = _STATIC_DIR / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> Response:
        """Serve the compiled single-page frontend."""
        if _INDEX_FILE.is_file():
            return FileResponse(_INDEX_FILE, media_type="text/html")
        return HTMLResponse(_missing_frontend_page())

    return app


app = create_app()

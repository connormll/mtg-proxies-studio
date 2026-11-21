"""Request and response models for the local web interface."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "running", "succeeded", "failed"]
JobKind = Literal["import", "generate", "suggest"]
PrintMode = Literal["standard", "makercraft", "handcut", "slider"]
PrintingScope = Literal["artworks", "all"]
WarningSeverity = Literal["error", "warning"]


class CardWarning(BaseModel):
    """A printing-quality warning attached to a card."""

    code: str
    message: str


class CardSummary(BaseModel):
    """A card in the GUI editor, collapsed to one entry per unique card."""

    key: str
    printing_id: str
    name: str
    set_code: str
    set_name: str
    collector_number: str
    released_at: str | None
    count: int
    image_url: str | None
    image_back_url: str | None
    face_names: list[str]
    is_basic_land: bool
    is_token: bool
    warnings: list[CardWarning]
    low_res: bool
    non_english: bool
    source_lines: list[int]


class ImportIssue(BaseModel):
    """A diagnostic produced while reading a decklist."""

    line: int
    text: str
    message: str
    severity: WarningSeverity
    skipped: bool = False


class ImportResult(BaseModel):
    """Parsed cards and line-level diagnostics from one decklist."""

    cards: list[CardSummary]
    issues: list[ImportIssue]
    total_count: int


class ImportRequest(BaseModel):
    """Decklist text pasted or read from an uploaded file."""

    text: str = Field(min_length=1, max_length=2_000_000)


class PrintingRequest(BaseModel):
    """Which printings to list for a card."""

    printing_id: str = Field(min_length=1)
    scope: PrintingScope = "artworks"


class PrintingOption(BaseModel):
    """One selectable Scryfall printing."""

    id: str
    name: str
    set_code: str
    set_name: str
    collector_number: str
    released_at: str | None
    rarity: str
    border_color: str
    language: str
    high_res: bool
    digital: bool
    is_recommended: bool
    image_url: str | None
    image_back_url: str | None
    face_names: list[str]
    warnings: list[CardWarning]
    low_res: bool
    non_english: bool


class PrintingsResult(BaseModel):
    """Available printings for the currently selected card."""

    card_name: str
    recommended_id: str
    options: list[PrintingOption]
    scope: PrintingScope


class SelectedCard(BaseModel):
    """A selected printing and how many copies to print."""

    printing_id: str = Field(min_length=1)
    count: int = Field(ge=1, le=999)


class ReplacementRequest(BaseModel):
    """A card to replace and the deck context around it."""

    printing_id: str = Field(min_length=1)
    deck: list[SelectedCard] = Field(default_factory=list, max_length=1000)


class ReplacementSuggestion(BaseModel):
    """One card Kimi proposes as a functional replacement."""

    name: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)
    card: CardSummary
    off_color_identity: bool = False


class ReplacementResult(BaseModel):
    """Kimi's replacement suggestions for one card."""

    card_name: str
    model: str
    deck_color_identity: str
    suggestions: list[ReplacementSuggestion]


class GenerateOptions(BaseModel):
    """PDF and cut-file layout options."""

    mode: PrintMode = "standard"
    paper_width: float = Field(ge=3.0, le=20.0)
    paper_height: float = Field(ge=3.0, le=20.0)
    scale: float = Field(default=1.0, ge=0.1, le=3.0)
    border_crop: int = Field(default=14, ge=0, le=300)
    gap: float = Field(default=0.0, ge=0.0, le=3.0)
    bleed: float | None = Field(default=None, ge=0.0, le=10.0)
    corner_radius: float | None = Field(default=None, ge=0.0, le=10.0)
    no_basic_lands: bool = False
    no_tokens: bool = False
    faces: Literal["all", "front", "back"] = "all"
    background: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    cropmarks: bool = True
    cut_file: bool = False
    mark_inset: float = Field(default=7.0, ge=0.5, le=60.0)
    mark_arm: float = Field(default=10.0, ge=0.5, le=50.0)
    mark_stroke: float = Field(default=1.0, ge=0.1, le=10.0)
    overcut: float = Field(default=1.0, ge=0.0, le=10.0)


class GenerateRequest(BaseModel):
    """A complete request to render one set of print files."""

    cards: list[SelectedCard] = Field(min_length=1, max_length=1000)
    options: GenerateOptions


class JobCreated(BaseModel):
    """Identifier of a newly queued background job."""

    job_id: str


class Artifact(BaseModel):
    """One generated file offered for download."""

    id: str
    filename: str
    label: str
    kind: Literal["pdf", "svg", "plt"]
    media_type: str
    size: int


class GenerationResult(BaseModel):
    """Files and layout details produced by a generation job."""

    artifacts: list[Artifact]
    layout: str
    card_count: int
    image_count: int
    cards_per_page: int
    pages: int
    filters: list[str]


class JobSnapshot(BaseModel):
    """Observable state of a background job."""

    id: str
    kind: JobKind
    status: JobStatus
    stage: str
    message: str
    completed: int
    total: int
    error: str | None
    result: dict[str, Any] | None


class CutterDevice(BaseModel):
    """A connected MakerCraft/Skycut device."""

    label: str
    bus: int | None
    address: int | None


class CutterDevicesResult(BaseModel):
    """Cutter discovery response, including a user-facing error if discovery failed."""

    devices: list[CutterDevice]
    error: str | None


class SendToCutterRequest(BaseModel):
    """Send a generated MakerCraft template to a connected cutter."""

    job_id: str = Field(min_length=1)
    device: str | None = None


class SendToCutterResult(BaseModel):
    """Result of a cutter transfer."""

    ok: bool
    message: str

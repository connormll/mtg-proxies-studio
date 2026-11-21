"""PDF and cut-file generation for the local web interface."""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Literal

import matplotlib.colors
import numpy as np

import mtg_proxies.scryfall as scryfall
from mtg_proxies.decklists import Decklist
from mtg_proxies.gui.models import Artifact, GenerateRequest, GenerationResult, SelectedCard
from mtg_proxies.gui.progress import ProgressReporter
from mtg_proxies.makercraft import write_plt_file
from mtg_proxies.print_cards import (
    _layout,
    handcut_layout,
    makercraft_layout,
    print_cards_fpdf,
    slider_layout,
    write_cut_files,
)
from mtg_proxies.scans import fetch_scans_scryfall


class _ProgressImages(Sequence[str]):
    """Sequence wrapper that reports plotting progress without changing the renderer."""

    def __init__(self, images: Sequence[str], report: ProgressReporter) -> None:
        self._images = images
        self._report = report

    def __len__(self) -> int:
        return len(self._images)

    def __getitem__(self, index: int | slice) -> str | Sequence[str]:
        return self._images[index]

    def __iter__(self) -> Iterator[str]:
        total = len(self._images)
        for index, image in enumerate(self._images, start=1):
            yield image
            self._report("Building PDF", index, total, "Placing card artwork on the page.")


def _decklist_from_request(cards: Sequence[SelectedCard]) -> tuple[Decklist, int]:
    """Rebuild a decklist from selected printing ids.

    Printings that disappeared from the local Scryfall database are skipped so
    one stale card cannot prevent the rest of the deck from being printed.
    """
    catalog = scryfall.card_by_id()
    counts: dict[str, int] = {}
    for selection in cards:
        counts[selection.printing_id] = counts.get(selection.printing_id, 0) + selection.count

    decklist = Decklist()
    skipped = 0
    for printing_id, count in counts.items():
        card = catalog.get(printing_id)
        if card is None:
            skipped += count
            continue
        decklist.append_card(count, card)
    return decklist, skipped


def _apply_filters(decklist: Decklist, request: GenerateRequest) -> tuple[Decklist, list[str]]:
    """Apply non-destructive basic-land and token exclusions."""
    filters: list[str] = []
    if request.options.no_basic_lands:
        before = decklist.total_count
        decklist = decklist.without_basic_lands()
        excluded = before - decklist.total_count
        if excluded:
            filters.append(f"Excluded {excluded} basic land{'s' if excluded != 1 else ''}.")
    if request.options.no_tokens:
        before = decklist.total_count
        decklist = decklist.without_tokens()
        excluded = before - decklist.total_count
        if excluded:
            filters.append(f"Excluded {excluded} token{'s' if excluded != 1 else ''}.")
    return decklist, filters


def _layout_details(
    request: GenerateRequest,
) -> tuple[str, int, np.ndarray | None, float, float, float, float]:
    """Return layout text, cards/page, grid limit, bleed, corner radius, gap, and mark inset."""
    options = request.options
    papersize = np.array([options.paper_width, options.paper_height]) * 25.4
    cardsize = np.array([2.5, 3.5]) * 25.4 * options.scale
    bleed = 2.0 if options.bleed is None and options.mode == "slider" else (options.bleed or 0.0)
    corner_radius = options.corner_radius
    if corner_radius is None:
        corner_radius = 0.0 if options.mode in {"handcut", "slider"} else 2.5

    max_cards: np.ndarray | None = None
    mark_inset = options.mark_inset
    layout_gap = options.gap

    if options.mode == "makercraft":
        max_cards, mark_inset = makercraft_layout(
            papersize,
            cardsize,
            options.border_crop,
            options.gap,
            mark_inset=options.mark_inset,
            mark_arm=options.mark_arm,
            mark_stroke=options.mark_stroke,
        )
        n_cards, _, _ = _layout(
            papersize,
            cardsize,
            options.border_crop,
            options.gap,
            max_cards=max_cards,
        )
        text = f"{int(np.prod(max_cards))} cards/page ({max_cards[0]}x{max_cards[1]}), {mark_inset:g} mm mark inset"
    elif options.mode == "handcut":
        n_cards, trim_size, _ = handcut_layout(papersize, cardsize, options.border_crop, options.gap)
        text = (
            f"{int(np.prod(n_cards))} cards/page ({n_cards[0]}x{n_cards[1]}), "
            f"{trim_size[0]:.1f} x {trim_size[1]:.1f} mm finished cards"
        )
    elif options.mode == "slider":
        n_cards, _, margin, layout_gap = slider_layout(
            papersize,
            cardsize,
            options.border_crop,
            bleed=bleed,
            gap=options.gap,
        )
        text = (
            f"{int(np.prod(n_cards))} cards/page ({n_cards[0]}x{n_cards[1]}), "
            f"{bleed:g} mm bleed, {layout_gap:g} mm gutters"
        )
        finger_margin = min(float(margin[0]), float(margin[1]))
        text += f", {finger_margin:.1f} mm minimum page margin"
    else:
        n_cards, _, _ = _layout(papersize, cardsize, options.border_crop, layout_gap)
        text = f"{int(np.prod(n_cards))} cards/page ({n_cards[0]}x{n_cards[1]})"

    cards_per_page = int(np.prod(n_cards))
    if cards_per_page <= 0:
        raise ValueError("The paper size is too small for a single card.")
    return text, cards_per_page, max_cards, bleed, corner_radius, layout_gap, mark_inset


def _artifact(
    job_dir: Path,
    artifact_id: str,
    label: str,
    kind: Literal["pdf", "svg", "plt"],
    media_type: str,
) -> Artifact:
    """Describe a generated file in the job output directory."""
    path = job_dir / Path(artifact_id).name
    if not path.is_file():
        raise FileNotFoundError(f"Generated file is missing: {path.name}")
    return Artifact(
        id=artifact_id,
        filename=path.name,
        label=label,
        kind=kind,
        media_type=media_type,
        size=path.stat().st_size,
    )


def generate_files(request: GenerateRequest, job_dir: Path, report: ProgressReporter) -> GenerationResult:
    """Render the selected cards and all requested companion cut files."""
    job_dir.mkdir(parents=True, exist_ok=True)
    options = request.options

    report("Preparing cards", 0, 0, "")
    decklist, skipped = _decklist_from_request(request.cards)
    decklist, filters = _apply_filters(decklist, request)
    if skipped:
        copies = "copy" if skipped == 1 else "copies"
        filters.insert(0, f"Skipped {skipped} {copies} no longer available in the card database.")
    if decklist.total_count == 0:
        if skipped:
            raise ValueError("None of the selected printings are available in the local Scryfall database.")
        raise ValueError("No cards are left to print after applying the exclusion filters.")

    layout_text, cards_per_page, max_cards, bleed, corner_radius, layout_gap, mark_inset = _layout_details(request)

    papersize = np.array([options.paper_width, options.paper_height]) * 25.4
    cardsize = np.array([2.5, 3.5]) * 25.4 * options.scale

    report("Fetching card scans", 0, 0, "Downloading high-resolution art from Scryfall.")
    images = fetch_scans_scryfall(
        decklist,
        faces=options.faces,
        progress=lambda completed, total, name: report("Fetching card scans", completed, total, name),
    )
    if not images:
        raise ValueError("No card faces were selected for printing.")

    background_color = None
    if options.background is not None:
        rgb = np.array(matplotlib.colors.to_rgb(options.background)) * 255
        background_color = tuple(round(channel) for channel in rgb)

    pdf_path = job_dir / "proxies.pdf"
    report("Building PDF", 0, len(images), "")
    print_cards_fpdf(
        _ProgressImages(images, report),
        pdf_path,
        papersize=papersize,
        cardsize=cardsize,
        border_crop=options.border_crop,
        background_color=background_color,
        cropmarks=options.cropmarks and options.mode not in {"handcut", "slider"},
        gap=options.gap,
        bleed=bleed,
        corner_radius=corner_radius,
        registration_marks=options.mode == "makercraft",
        mark_inset=mark_inset,
        mark_arm=options.mark_arm,
        mark_stroke=options.mark_stroke,
        max_cards=max_cards,
        handcut=options.mode == "handcut",
        slider=options.mode == "slider",
    )

    artifacts = [_artifact(job_dir, "proxies.pdf", "Print sheet PDF", "pdf", "application/pdf")]

    if options.mode == "makercraft":
        report("Writing MakerCraft template", 0, 1, "")
        plt_path = write_plt_file(
            job_dir / "makercraft.plt",
            papersize=papersize,
            cardsize=cardsize,
            border_crop=options.border_crop,
            gap=options.gap,
            corner_radius=corner_radius,
            mark_inset=mark_inset,
            overcut=options.overcut,
            max_cards=max_cards,
        )
        artifacts.append(
            _artifact(job_dir, plt_path.name, "MakerCraft cut template", "plt", "application/octet-stream")
        )

    if options.cut_file:
        report("Writing cut files", 0, 0, "")
        cut_files = write_cut_files(
            len(images),
            job_dir / "proxies_cut.svg",
            papersize=papersize,
            cardsize=cardsize,
            border_crop=options.border_crop,
            gap=layout_gap,
            corner_radius=corner_radius,
            max_cards=max_cards,
        )
        multi_page = len(cut_files) > 1
        for index, path in enumerate(cut_files, start=1):
            label = f"SVG cut file - page {index}" if multi_page else "SVG cut file"
            artifacts.append(_artifact(job_dir, path.name, label, "svg", "image/svg+xml"))

    pages = math.ceil(len(images) / cards_per_page)
    report("Complete", 1, 1, "")
    return GenerationResult(
        artifacts=artifacts,
        layout=layout_text,
        card_count=decklist.total_count,
        image_count=len(images),
        cards_per_page=cards_per_page,
        pages=pages,
        filters=filters,
    )

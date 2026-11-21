from __future__ import annotations

import itertools
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.colors as colors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from tqdm import tqdm

from mtg_proxies.plotting import SplitPages

if TYPE_CHECKING:
    from fpdf import FPDF

image_size = np.array([745, 1040])
MAX_GAP = 3.0
MAX_BLEED = 10.0
MAX_CORNER_RADIUS = 10.0
DEFAULT_MARK_INSET = 7.0
DEFAULT_MARK_ARM = 10.0
DEFAULT_MARK_STROKE = 1.0
C10_MAX_CONTOUR_WIDTH = 220.0
C10_MAX_MARK_BOX_LENGTH = 260.0
MAKERCRAFT_MARK_CLEARANCE = 0.5
HANDCUT_MARK_STROKE = 0.15
SLIDER_DEFAULT_BLEED = 2.0
SLIDER_GUIDE_STROKE = 0.15


def _trim_size(cardsize: np.ndarray, border_crop: int) -> np.ndarray:
    """Return the size of a card after the border crop is trimmed away."""
    return cardsize * (image_size - 2 * border_crop) / image_size


def _layout(
    papersize: np.ndarray,
    cardsize: np.ndarray,
    border_crop: int,
    gap: float,
    max_cards: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute the card grid, trimmed card size, and trim-grid margin.

    The gap must use the same units as papersize and cardsize. If ``max_cards``
    is given, the grid is limited to that many columns and rows.
    """
    if gap < 0:
        raise ValueError(f"Gap must not be negative: {gap}")
    trim_size = _trim_size(cardsize, border_crop)
    if np.any(trim_size <= 0):
        raise ValueError(f"Border crop too large for card size: {border_crop}")

    # Largest grid that fits, including the gap between adjacent cards.
    n_cards = np.floor((papersize + gap) / (trim_size + gap)).astype(int)
    if max_cards is not None:
        n_cards = np.minimum(n_cards, np.asarray(max_cards, dtype=int))
    if np.any(n_cards == 0):
        raise ValueError(f"Paper size too small: {papersize}")

    occupied = n_cards * trim_size + (n_cards - 1) * gap
    margin = (papersize - occupied) / 2
    return n_cards, trim_size, margin


def makercraft_layout(
    papersize: np.ndarray,
    cardsize: np.ndarray,
    border_crop: int,
    gap: float,
    mark_inset: float = DEFAULT_MARK_INSET,
    mark_arm: float = DEFAULT_MARK_ARM,
    mark_stroke: float = DEFAULT_MARK_STROKE,
) -> tuple[np.ndarray, float]:
    """Choose a card grid and mark inset that fit the MakerCraft C10.

    The C10 can contour-cut about 220 mm across the carriage. We also keep the
    mark box within about 260 mm in the feed direction, the size of the proven
    8 x 10 layout. Start with the largest grid that fits the paper, then reduce
    rows/columns until the marks have clear paper outside the grid.

    Returns:
        The maximum ``(columns, rows)`` grid and the adjusted mark inset in mm.
    """
    width, height = (float(value) for value in papersize)
    inset = max(
        float(mark_inset),
        (width - C10_MAX_CONTOUR_WIDTH) / 2,
        (height - C10_MAX_MARK_BOX_LENGTH) / 2,
        0.0,
    )
    # Round up to the next 0.5 mm so the mark box stays inside the limit.
    inset = float(np.ceil(inset * 2) / 2)

    n_cards, trim_size, _ = _layout(papersize, cardsize, border_crop, gap)
    max_cols, max_rows = (int(value) for value in n_cards)

    # Keep the cut grid inside the C10's contour-cutting width.
    while max_cols > 1 and max_cols * trim_size[0] + (max_cols - 1) * gap > C10_MAX_CONTOUR_WIDTH:
        max_cols -= 1

    # The top and bottom marks need a clear strip of paper outside the grid.
    required = inset + float(mark_arm) + float(mark_stroke) / 2 + MAKERCRAFT_MARK_CLEARANCE
    while max_rows > 1:
        occupied = np.array([max_cols, max_rows]) * trim_size + (np.array([max_cols, max_rows]) - 1) * gap
        margins = (papersize - occupied) / 2
        if margins[1] >= required:
            break
        max_rows -= 1

    occupied = np.array([max_cols, max_rows]) * trim_size + (np.array([max_cols, max_rows]) - 1) * gap
    margins = (papersize - occupied) / 2
    if margins[1] < required:
        raise ValueError(
            f"Paper is too small for MakerCraft registration marks: {papersize[0]:.1f} x {papersize[1]:.1f} mm"
        )
    return np.array([max_cols, max_rows], dtype=int), inset


def handcut_layout(
    papersize: np.ndarray,
    cardsize: np.ndarray,
    border_crop: int,
    gap: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the card grid, finished card size, and margin for hand cutting.

    Hand cutting uses the largest grid that fits the paper. With the default
    ``gap=0`` the cards are edge to edge, so one straight cut separates each
    pair of neighbours and a single cut line serves both cards.

    Args:
        papersize: Size of the paper in mm.
        cardsize: Size of a card in mm.
        border_crop: How many pixels to crop from the border of each card.
        gap: Gap between cards in mm.

    Returns:
        The ``(columns, rows)`` grid, the finished card size, and the top-left
        margin of the grid, all in mm.
    """
    return _layout(papersize, cardsize, border_crop, gap)


def slider_layout(
    papersize: np.ndarray,
    cardsize: np.ndarray,
    border_crop: int,
    bleed: float = SLIDER_DEFAULT_BLEED,
    gap: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Return the maximised grid for a manual sliding-blade paper trimmer.

    Each card is printed with mirrored bleed. Neighbouring cards need at least
    twice the bleed between their trim boxes, otherwise the bleed images would
    overlap the neighbouring card face. The returned gutter is therefore the
    larger of ``gap`` and ``2 * bleed``.

    Args:
        papersize: Size of the paper in mm.
        cardsize: Size of a card in mm.
        border_crop: How many pixels to crop from the border of each card.
        bleed: Mirrored bleed around each card in mm.
        gap: Minimum gap between finished card edges in mm.

    Returns:
        The ``(columns, rows)`` grid, the finished card size, the top-left
        margin of the grid, and the gutter between cards, all in mm.
    """
    if bleed < 0:
        raise ValueError(f"Bleed must not be negative: {bleed}")
    gutter = max(float(gap), 2 * float(bleed))
    n_cards, trim_size, margin = _layout(papersize, cardsize, border_crop, gutter)
    return n_cards, trim_size, margin, gutter


def _trim_origin(
    margin: np.ndarray,
    trim_size: np.ndarray,
    gap: float,
    x: int,
    y: int,
) -> np.ndarray:
    """Return the top-left corner of a card's trim box in mm."""
    return margin + np.array([x, y]) * (trim_size + gap)


def _bleed_pixels(cardsize: np.ndarray, bleed: float) -> np.ndarray:
    """Convert a bleed to source-image pixels for each axis.

    The bleed must use the same units as cardsize.
    """
    return np.round(bleed / cardsize * image_size).astype(int)


def _rounded_rect_path(origin: np.ndarray, size: np.ndarray, radius: float) -> str:
    """Return an SVG path for a rounded rectangle, in millimetres."""
    x, y = origin
    width, height = size
    radius = min(max(float(radius), 0.0), width / 2, height / 2)
    if radius <= 0:
        return f"M {x:.3f} {y:.3f} H {x + width:.3f} V {y + height:.3f} H {x:.3f} Z"

    return (
        f"M {x + radius:.3f} {y:.3f} "
        f"H {x + width - radius:.3f} "
        f"A {radius:.3f} {radius:.3f} 0 0 1 {x + width:.3f} {y + radius:.3f} "
        f"V {y + height - radius:.3f} "
        f"A {radius:.3f} {radius:.3f} 0 0 1 {x + width - radius:.3f} {y + height:.3f} "
        f"H {x + radius:.3f} "
        f"A {radius:.3f} {radius:.3f} 0 0 1 {x:.3f} {y + height - radius:.3f} "
        f"V {y + radius:.3f} "
        f"A {radius:.3f} {radius:.3f} 0 0 1 {x + radius:.3f} {y:.3f} Z"
    )


def _cut_svg(page: int, pages: int, papersize: np.ndarray, paths: list[str]) -> str:
    """Return the contents of one SVG cut-file page."""
    width, height = papersize
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{width:.3f}mm" height="{height:.3f}mm" '
            f'viewBox="0 0 {width:.3f} {height:.3f}">'
        ),
        f"  <title>MTG Proxies cut file - page {page} of {pages}</title>",
        "  <desc>Cut lines for printed cards. Units are millimetres.</desc>",
        '  <g id="cut-lines">',
    ]
    for card_number, path in enumerate(paths, start=1):
        lines.append(
            f'    <path id="card-{card_number}" d="{path}" fill="none" stroke="#ff0000" '
            f'stroke-width="0.1" stroke-linecap="round" stroke-linejoin="round" />'
        )
    lines.extend(["  </g>", "</svg>", ""])
    return "\n".join(lines)


def _registration_mark_segments(
    papersize: np.ndarray,
    inset: float = DEFAULT_MARK_INSET,
    arm: float = DEFAULT_MARK_ARM,
) -> list[list[tuple[float, float]]]:
    """Return the L-shaped registration marks and orientation dash, in mm."""
    width, height = (float(value) for value in papersize)
    min_x = min_y = float(inset)
    max_x = width - float(inset)
    max_y = height - float(inset)
    return [
        [(min_x, min_y + arm), (min_x, min_y), (min_x + arm, min_y)],
        [(max_x - arm, min_y), (max_x, min_y), (max_x, min_y + arm)],
        [(max_x, max_y - arm), (max_x, max_y), (max_x - arm, max_y)],
        [(min_x + arm, max_y), (min_x, max_y), (min_x, max_y - arm)],
        # Separate 5 mm orientation dash, 5 mm left of the bottom-right mark.
        [(max_x - arm - 10.0, max_y), (max_x - arm - 5.0, max_y)],
    ]


def _draw_registration_marks(
    pdf: FPDF,
    papersize: np.ndarray,
    inset: float = DEFAULT_MARK_INSET,
    arm: float = DEFAULT_MARK_ARM,
    stroke: float = DEFAULT_MARK_STROKE,
) -> None:
    """Draw Skycut/MakerCraft registration marks on the current PDF page."""
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(stroke)
    for segment in _registration_mark_segments(papersize, inset, arm):
        for (x1, y1), (x2, y2) in itertools.pairwise(segment):
            pdf.line(x1, y1, x2, y2)


def _cut_guide_segments(
    papersize: np.ndarray,
    margin: np.ndarray,
    trim_size: np.ndarray,
    gap: float,
    count: int,
    n_cards: np.ndarray,
) -> list[list[tuple[float, float]]]:
    """Return handcut cut lines for the cards on one page, in mm.

    Each line runs from one paper edge to the other and sits exactly on a
    finished card edge. Cutting along it separates the cards and removes the
    line itself.
    """
    if count <= 0:
        return []

    columns = int(n_cards[0])
    used_columns = min(columns, count)
    used_rows = (count + columns - 1) // columns

    xs = [float(margin[0] + column * (trim_size[0] + gap)) for column in range(used_columns)]
    xs.append(xs[-1] + float(trim_size[0]))
    ys = [float(margin[1] + row * (trim_size[1] + gap)) for row in range(used_rows)]
    ys.append(ys[-1] + float(trim_size[1]))

    width, height = (float(value) for value in papersize)
    segments: list[list[tuple[float, float]]] = [[(x, 0.0), (x, height)] for x in xs]
    segments.extend([[(0.0, y), (width, y)] for y in ys])
    return segments


def _draw_cut_guides(
    pdf: FPDF,
    papersize: np.ndarray,
    margin: np.ndarray,
    trim_size: np.ndarray,
    gap: float,
    count: int,
    n_cards: np.ndarray,
    stroke: float = HANDCUT_MARK_STROKE,
) -> None:
    """Draw handcut cut lines on the current PDF page."""
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(stroke)
    for (x1, y1), (x2, y2) in _cut_guide_segments(papersize, margin, trim_size, gap, count, n_cards):
        pdf.line(x1, y1, x2, y2)


def _slider_guide_segments(
    papersize: np.ndarray,
    margin: np.ndarray,
    trim_size: np.ndarray,
    gutter: float,
    count: int,
    n_cards: np.ndarray,
) -> list[list[tuple[float, float]]]:
    """Return full-page cut guides for a sliding-blade paper trimmer, in mm.

    Every finished card edge gets a straight line running from one paper edge
    to the other, so the lines cross at every card corner. The lines sit on the
    card edges and run through the bleed and gutters, never across a card face.
    Because they span the whole sheet, the cross-cut guides remain on each
    strip after the first set of cuts.
    """
    if count <= 0:
        return []

    columns = int(n_cards[0])
    used_columns = min(columns, count)
    used_rows = (count + columns - 1) // columns

    xs = []
    for column in range(used_columns):
        left = float(margin[0] + column * (trim_size[0] + gutter))
        xs.extend((left, left + float(trim_size[0])))
    ys = []
    for row in range(used_rows):
        top = float(margin[1] + row * (trim_size[1] + gutter))
        ys.extend((top, top + float(trim_size[1])))

    width, height = (float(value) for value in papersize)
    segments: list[list[tuple[float, float]]] = [[(x, 0.0), (x, height)] for x in xs]
    segments.extend([[(0.0, y), (width, y)] for y in ys])
    return segments


def _draw_slider_guides(
    pdf: FPDF,
    papersize: np.ndarray,
    margin: np.ndarray,
    trim_size: np.ndarray,
    gutter: float,
    count: int,
    n_cards: np.ndarray,
    stroke: float = SLIDER_GUIDE_STROKE,
) -> None:
    """Draw full-page sliding-trimmer guides along every card edge."""
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(stroke)
    for (x1, y1), (x2, y2) in _slider_guide_segments(papersize, margin, trim_size, gutter, count, n_cards):
        pdf.line(x1, y1, x2, y2)


def write_cut_files(
    num_cards: int,
    filepath: str | Path,
    papersize: np.ndarray = np.array([210.0, 297.0]),
    cardsize: np.ndarray = np.array([2.5 * 25.4, 3.5 * 25.4]),
    border_crop: int = 14,
    gap: float = 0.0,
    corner_radius: float = 2.5,
    max_cards: np.ndarray | None = None,
) -> list[Path]:
    """Write SVG cut files for cutting machines, one file per printed page.

    Args:
        num_cards: Number of cards that were printed.
        filepath: Base path for the SVG file(s). A missing ``.svg`` suffix is added.
        papersize: Size of the paper in mm.
        cardsize: Size of a card in mm.
        border_crop: How many pixels to crop from the border of each card.
        gap: Gap between cards in mm.
        corner_radius: Corner radius of the cards in mm. Set to 0 for square corners.
        max_cards: Optional maximum ``(columns, rows)`` grid.

    Returns:
        The paths of the written SVG files.
    """
    if gap < 0:
        raise ValueError(f"Gap must not be negative: {gap}")
    if not 0 <= corner_radius <= MAX_CORNER_RADIUS:
        raise ValueError(f"Corner radius must be between 0 and {MAX_CORNER_RADIUS:g} mm: {corner_radius}")

    N, trim_size, margin = _layout(papersize, cardsize, border_crop, gap, max_cards=max_cards)
    cards_per_sheet = int(np.prod(N))
    pages = (num_cards + cards_per_sheet - 1) // cards_per_sheet
    if pages == 0:
        return []

    filepath = Path(filepath)
    if filepath.suffix.lower() != ".svg":
        filepath = filepath.with_name(filepath.name + ".svg")
    filepath.parent.mkdir(parents=True, exist_ok=True)

    output_paths = (
        [filepath]
        if pages == 1
        else [filepath.with_name(f"{filepath.stem}_{page}{filepath.suffix}") for page in range(1, pages + 1)]
    )

    for page, output_path in enumerate(output_paths):
        page_start = page * cards_per_sheet
        cards_on_page = min(cards_per_sheet, num_cards - page_start)
        paths = []
        for card in range(cards_on_page):
            x = card % N[0]
            y = card // N[0]
            origin = _trim_origin(margin, trim_size, gap, x, y)
            paths.append(_rounded_rect_path(origin, trim_size, corner_radius))
        output_path.write_text(_cut_svg(page + 1, pages, papersize, paths), encoding="utf-8")

    return output_paths


def _pad_image(image: np.ndarray, bleed_px: np.ndarray) -> np.ndarray:
    """Add mirrored-edge bleed to an image."""
    if not np.any(bleed_px):
        return image

    pad_width = [(bleed_px[1], bleed_px[1]), (bleed_px[0], bleed_px[0])]
    if image.ndim == 3:
        pad_width.append((0, 0))
    return np.pad(image, pad_width, mode="reflect")


def _rounded_alpha(shape: tuple[int, int], radius_px: np.ndarray) -> np.ndarray:
    """Create an anti-aliased rounded-rectangle alpha mask."""
    height, width = shape
    alpha = np.ones((height, width), dtype=np.float32)
    rx = min(max(int(radius_px[0]), 0), width // 2)
    ry = min(max(int(radius_px[1]), 0), height // 2)
    if rx == 0 or ry == 0:
        return alpha

    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    yy += 0.5
    xx += 0.5
    smooth = max(min(rx, ry), 1)
    corners = (
        ((xx < rx) & (yy < ry), rx, ry),
        ((xx >= width - rx) & (yy < ry), width - rx, ry),
        ((xx < rx) & (yy >= height - ry), rx, height - ry),
        ((xx >= width - rx) & (yy >= height - ry), width - rx, height - ry),
    )
    for region, cx, cy in corners:
        distance = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
        alpha[region] = np.clip((1 - distance[region]) * smooth + 0.5, 0, 1)
    return alpha


def _radius_pixels(
    cardsize: np.ndarray,
    image_shape: tuple[int, ...],
    corner_radius: float,
    bleed: float,
) -> np.ndarray:
    """Convert a corner radius (plus bleed) to image pixels."""
    if corner_radius <= 0:
        return np.zeros(2, dtype=int)
    physical_size = cardsize * [image_shape[1], image_shape[0]] / image_size
    return np.round((corner_radius + bleed) / physical_size * [image_shape[1], image_shape[0]]).astype(int)


def _composite_rounded(
    image: np.ndarray,
    radius_px: np.ndarray,
    background_rgb: np.ndarray,
) -> np.ndarray:
    """Composite an image over the background and optionally round its corners."""
    if image.ndim == 2:
        rgb = np.repeat(image[..., np.newaxis], 3, axis=2)
        alpha = np.ones(image.shape, dtype=np.float32)
    elif image.shape[2] == 4:
        rgb = image[..., :3]
        alpha = image[..., 3]
    else:
        rgb = image[..., :3]
        alpha = np.ones(image.shape[:2], dtype=np.float32)

    rgb = np.asarray(rgb, dtype=np.float32)
    alpha = np.asarray(alpha, dtype=np.float32)
    if np.any(radius_px):
        alpha = alpha * _rounded_alpha(image.shape[:2], radius_px)
    alpha = alpha[..., np.newaxis]
    return np.clip(rgb * alpha + background_rgb * (1 - alpha), 0, 1)


def _crop_image(
    image: np.ndarray,
    left: int,
    top: int,
    right: int,
    bottom: int,
    bleed_px: np.ndarray,
) -> np.ndarray:
    """Crop an image and add bleed to all sides."""
    cropped = image[top : image.shape[0] - bottom, left : image.shape[1] - right]
    return _pad_image(cropped, bleed_px)


def _prepare_cached_image(
    image: str | Path,
    suffix: str,
    left: int,
    top: int,
    right: int,
    bottom: int,
    bleed_px: np.ndarray,
    cardsize: np.ndarray,
    corner_radius: float,
    bleed: float,
    background_rgb: np.ndarray,
) -> str:
    """Return a cached image path, creating the cropped/bleed variant if needed."""
    path = Path(image)
    cached_image = path.parent / (path.stem + suffix + path.suffix)
    if not cached_image.is_file():
        cropped = _crop_image(plt.imread(image), left, top, right, bottom, bleed_px)
        radius_px = _radius_pixels(cardsize, cropped.shape, corner_radius, bleed)
        cropped = _composite_rounded(cropped, radius_px, background_rgb)
        plt.imsave(cached_image, cropped)
    return str(cached_image)


def print_cards_matplotlib(
    images: Sequence[str | Path],
    filepath: str | Path,
    papersize: np.ndarray = np.array([8.27, 11.69]),
    cardsize: np.ndarray = np.array([2.5, 3.5]),
    border_crop: int = 14,
    interpolation: str | None = "lanczos",
    dpi: int = 600,
    background_color: str | None = None,
    gap: float = 0.0,
    bleed: float = 0.0,
    corner_radius: float = 2.5,
) -> None:
    """Print a list of cards to a pdf file.

    Args:
        images: List of image files
        filepath: Name of the pdf file
        papersize: Size of the paper in inches. Defaults to A4.
        cardsize: Size of a card in inches.
        border_crop: How many pixel to crop from the border of each card.
        interpolation: Interpolation method for resizing images.
        dpi: Dots per inch for the output PDF.
        background_color: Background color of the PDF as name or hex code.
        gap: Gap between cards in mm.
        bleed: Mirrored-edge bleed around each card in mm.
        corner_radius: Corner radius of printed cards in mm. Set to 0 to disable.
    """
    if not 0 <= gap <= MAX_GAP:
        raise ValueError(f"Gap must be between 0 and {MAX_GAP:g} mm: {gap}")
    if not 0 <= bleed <= MAX_BLEED:
        raise ValueError(f"Bleed must be between 0 and {MAX_BLEED:g} mm: {bleed}")
    if not 0 <= corner_radius <= MAX_CORNER_RADIUS:
        raise ValueError(f"Corner radius must be between 0 and {MAX_CORNER_RADIUS:g} mm: {corner_radius}")
    gap /= 25.4
    bleed /= 25.4
    corner_radius /= 25.4
    background_rgb = np.array(colors.to_rgb(background_color)) if background_color is not None else np.ones(3)

    # Cards per figure
    N, trim_size, margin = _layout(papersize, cardsize, border_crop, gap)
    bleed_px = _bleed_pixels(cardsize, bleed)
    border_overhang = cardsize * border_crop / image_size
    use_trimmed = gap > 0 or bleed > 0 or corner_radius > 0

    # Ensure directory exists
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Choose pdf of image saver
    saver = PdfPages if filepath.suffix == ".pdf" else SplitPages

    with saver(filepath) as saver, tqdm(total=len(images), desc="Plotting cards") as pbar:
        idx = 0
        while idx < len(images):  # Loop over pages
            fig = plt.figure(figsize=papersize)
            ax = fig.add_axes((0, 0, 1, 1))  # ax covers the whole figure
            #  Background
            if background_color is not None:
                plt.gca().add_patch(Rectangle((0, 0), 1, 1, color=background_color, zorder=-1000))

            for y in range(N[1]):
                for x in range(N[0]):
                    if idx < len(images):
                        image = plt.imread(images[idx])
                        idx += 1

                        origin = _trim_origin(margin, trim_size, gap, x, y)
                        if use_trimmed:
                            image = _crop_image(
                                image,
                                border_crop,
                                border_crop,
                                border_crop,
                                border_crop,
                                bleed_px,
                            )
                            lower = origin - bleed
                        else:
                            # Crop left and top if not on border of sheet
                            left = border_crop if x > 0 else 0
                            top = border_crop if y > 0 else 0
                            image = image[top:, left:]
                            lower = origin - np.where([left == 0, top == 0], border_overhang, 0)

                        radius_px = _radius_pixels(cardsize, image.shape, corner_radius, bleed)
                        image = _composite_rounded(image, radius_px, background_rgb)
                        size = cardsize * [image.shape[1], image.shape[0]] / image_size
                        upper = lower + size
                        extent = (
                            lower[0] / papersize[0],
                            upper[0] / papersize[0],
                            1 - upper[1] / papersize[1],
                            1 - lower[1] / papersize[1],
                        )  # flip y-axis

                        plt.imshow(
                            image,
                            extent=extent,
                            aspect=papersize[1] / papersize[0],
                            interpolation=interpolation,
                        )
                        pbar.update(1)

            plt.xlim(0, 1)
            plt.ylim(0, 1)

            # Hide all axis ticks and labels
            ax.axis("off")

            saver.savefig(dpi=dpi)
            plt.close()


def print_cards_fpdf(
    images: Sequence[str | Path],
    filepath: str | Path,
    papersize: np.ndarray = np.array([210, 297]),
    cardsize: np.ndarray = np.array([2.5 * 25.4, 3.5 * 25.4]),
    border_crop: int = 14,
    background_color: tuple[int, int, int] | None = None,
    cropmarks: bool = True,
    gap: float = 0.0,
    bleed: float = 0.0,
    corner_radius: float = 2.5,
    registration_marks: bool = False,
    mark_inset: float = DEFAULT_MARK_INSET,
    mark_arm: float = DEFAULT_MARK_ARM,
    mark_stroke: float = DEFAULT_MARK_STROKE,
    max_cards: np.ndarray | None = None,
    handcut: bool = False,
    slider: bool = False,
) -> None:
    """Print a list of cards to a pdf file.

    Args:
        images: List of image files
        filepath: Name of the pdf file
        papersize: Size of the paper in mm. Defaults to A4.
        cardsize: Size of a card in mm.
        border_crop: How many pixel to crop from the border of each card.
        background_color: Background color of the PDF as an RGB tuple.
        cropmarks: Whether to add crop marks to the PDF.
        gap: Gap between cards in mm.
        bleed: Mirrored-edge bleed around each card in mm.
        corner_radius: Corner radius of printed cards in mm. Set to 0 to disable.
        registration_marks: Add Skycut/MakerCraft camera registration marks.
        mark_inset: Distance of the marks from the page edge in mm.
        mark_arm: Arm length of each L-shaped mark in mm.
        mark_stroke: Line width of each registration mark in mm.
        max_cards: Optional maximum ``(columns, rows)`` grid.
        handcut: Add full-page cut lines along the card edges for manual trimming.
        slider: Optimise the layout for a sliding-blade paper trimmer. Widen the
            gutters to at least twice the bleed and print full-page cut lines
            along every card edge.
    """
    from fpdf import FPDF

    if not 0 <= gap <= MAX_GAP:
        raise ValueError(f"Gap must be between 0 and {MAX_GAP:g} mm: {gap}")
    if not 0 <= bleed <= MAX_BLEED:
        raise ValueError(f"Bleed must be between 0 and {MAX_BLEED:g} mm: {bleed}")
    if not 0 <= corner_radius <= MAX_CORNER_RADIUS:
        raise ValueError(f"Corner radius must be between 0 and {MAX_CORNER_RADIUS:g} mm: {corner_radius}")
    if registration_marks:
        if not 0 < mark_inset < min(papersize) / 2:
            raise ValueError(f"Registration mark inset is outside the page: {mark_inset} mm")
        if mark_arm <= 0:
            raise ValueError(f"Registration mark arm must be positive: {mark_arm} mm")
        if mark_stroke <= 0:
            raise ValueError(f"Registration mark stroke must be positive: {mark_stroke} mm")
        if 2 * (mark_inset + mark_arm + 10.0) > min(papersize):
            raise ValueError(f"Registration marks do not fit on this paper size: {papersize}")

    # Bleed must not run over a neighbouring card. Sliding-trimmer layouts get
    # one gutter per pair of adjacent cards, sized for both cards' bleed.
    layout_gap = max(gap, 2 * bleed) if slider else gap

    # Cards per sheet
    N, trim_size, margin = _layout(papersize, cardsize, border_crop, layout_gap, max_cards=max_cards)
    cards_per_sheet = int(np.prod(N))
    bleed_px = _bleed_pixels(cardsize, bleed)
    border_overhang = cardsize * border_crop / image_size
    use_trimmed = layout_gap > 0 or bleed > 0 or corner_radius > 0
    background_rgb = np.ones(3) if background_color is None else np.array(background_color, dtype=np.float32) / 255
    background_hex = "".join(f"{round(channel * 255):02x}" for channel in background_rgb)

    # Ensure directory exists
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Initialize PDF
    pdf = FPDF(orientation="P", unit="mm", format=(float(papersize[0]), float(papersize[1])))

    page_card_count = 0
    for i, image in enumerate(tqdm(images, desc="Plotting cards")):
        if i % cards_per_sheet == 0:  # Startign a new sheet
            if i > 0:
                if registration_marks:
                    _draw_registration_marks(pdf, papersize, mark_inset, mark_arm, mark_stroke)
                if handcut:
                    _draw_cut_guides(pdf, papersize, margin, trim_size, layout_gap, page_card_count, N)
                if slider:
                    _draw_slider_guides(pdf, papersize, margin, trim_size, layout_gap, page_card_count, N)
            pdf.add_page()
            page_card_count = min(cards_per_sheet, len(images) - i)
            if background_color is not None:
                pdf.set_fill_color(*background_color)
                pdf.rect(0, 0, papersize[0], papersize[1], "F")

        x = (i % cards_per_sheet) % N[0]
        y = (i % cards_per_sheet) // N[0]
        origin = _trim_origin(margin, trim_size, layout_gap, x, y)

        if use_trimmed:
            bleed_suffix = f"_b{bleed_px[0]}x{bleed_px[1]}" if np.any(bleed_px) else ""
            cache_suffix = (
                f"_trim{border_crop}{bleed_suffix}_cr{corner_radius:g}"
                f"_cs{cardsize[0]:.3f}x{cardsize[1]:.3f}_{background_hex}"
            )
            cropped_image = _prepare_cached_image(
                image,
                cache_suffix,
                border_crop,
                border_crop,
                border_crop,
                border_crop,
                bleed_px,
                cardsize,
                corner_radius,
                bleed,
                background_rgb,
            )
            lower = origin - bleed
            size = cardsize * (image_size - 2 * border_crop + 2 * bleed_px) / image_size
        else:
            # Crop left and top if not on border of sheet
            left = border_crop if x > 0 else 0
            top = border_crop if y > 0 else 0
            cropped_image = _prepare_cached_image(
                image,
                f"_{left}_{top}_flat{background_hex}",
                left,
                top,
                0,
                0,
                bleed_px,
                cardsize,
                0.0,
                0.0,
                background_rgb,
            )
            lower = origin - np.where([left == 0, top == 0], border_overhang, 0)
            size = cardsize * (image_size - [left, top]) / image_size

        # Plot image
        pdf.image(cropped_image, x=lower[0], y=lower[1], w=size[0], h=size[1])

        if cropmarks and not handcut and not slider and ((i + 1) % cards_per_sheet == 0 or i + 1 == len(images)):
            # If this was the last card on a page, add crop marks
            pdf.set_line_width(0.05)
            pdf.set_draw_color(255, 255, 255)
            x_marks = sorted({
                round(margin[0] + x * (trim_size[0] + layout_gap) + offset, 6)
                for x in range(N[0])
                for offset in (0, trim_size[0])
            })
            y_marks = sorted({
                round(margin[1] + y * (trim_size[1] + layout_gap) + offset, 6)
                for y in range(N[1])
                for offset in (0, trim_size[1])
            })
            for x_mark in x_marks:
                for y_mark in y_marks:
                    pdf.line(x_mark - 0.5, y_mark, x_mark + 0.5, y_mark)
                    pdf.line(x_mark, y_mark - 0.5, x_mark, y_mark + 0.5)

    if len(images) > 0:
        if registration_marks:
            _draw_registration_marks(pdf, papersize, mark_inset, mark_arm, mark_stroke)
        if handcut:
            _draw_cut_guides(pdf, papersize, margin, trim_size, layout_gap, page_card_count, N)
        if slider:
            _draw_slider_guides(pdf, papersize, margin, trim_size, layout_gap, page_card_count, N)

    tqdm.write(f"Writing to {filepath}")
    pdf.output(filepath)

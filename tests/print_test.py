from __future__ import annotations

from pathlib import Path

import pytest
from matplotlib.pylab import TYPE_CHECKING

if TYPE_CHECKING:
    from mtg_proxies.decklists import Decklist


@pytest.fixture(scope="module")
def example_images(example_decklist: Decklist) -> list[str]:
    from mtg_proxies import fetch_scans_scryfall

    example_images = fetch_scans_scryfall(example_decklist)
    assert len(example_images) == 7
    return example_images


@pytest.fixture(scope="module")
def synthetic_images(tmp_path_factory: pytest.TempPathFactory) -> list[str]:
    import numpy as np
    from matplotlib import pyplot as plt

    folder = tmp_path_factory.mktemp("synthetic_images")
    path = folder / "card.png"
    plt.imsave(path, np.full((1040, 745, 3), 0.5, dtype=np.float32))
    return [str(path)] * 4


def test_print_cards_fpdf(example_images: list[str], tmp_path: Path) -> None:
    from mtg_proxies import print_cards_fpdf

    out_file = tmp_path / "decklist.pdf"
    print_cards_fpdf(example_images, out_file)

    assert out_file.is_file()


def test_print_cards_matplotlib_pdf(example_images: list[str], tmp_path: Path) -> None:
    from mtg_proxies import print_cards_matplotlib

    out_file = tmp_path / "decklist.pdf"
    print_cards_matplotlib(example_images, out_file)

    assert out_file.is_file()


def test_print_cards_matplotlib_png(example_images: list[str], tmp_path: Path) -> None:
    from mtg_proxies import print_cards_matplotlib

    out_file = tmp_path / "decklist.png"
    print_cards_matplotlib(example_images, out_file)

    assert (tmp_path / "decklist_000.png").is_file()


def test_print_cards_fpdf_gap_and_bleed(synthetic_images: list[str], tmp_path: Path) -> None:
    from mtg_proxies import print_cards_fpdf

    out_file = tmp_path / "gap_bleed.pdf"
    print_cards_fpdf(synthetic_images, out_file, gap=3, bleed=2)

    assert out_file.is_file()


def test_print_cards_fpdf_slider(synthetic_images: list[str], tmp_path: Path) -> None:
    import numpy as np

    from mtg_proxies import print_cards_fpdf

    out_file = tmp_path / "slider.pdf"
    print_cards_fpdf(
        synthetic_images,
        out_file,
        papersize=np.array([8.5 * 25.4, 11 * 25.4]),
        bleed=2,
        corner_radius=0,
        slider=True,
    )

    assert out_file.is_file()


def test_print_cards_fpdf_makercraft_marks(synthetic_images: list[str], tmp_path: Path) -> None:
    import numpy as np

    from mtg_proxies import print_cards_fpdf

    out_file = tmp_path / "makercraft.pdf"
    print_cards_fpdf(
        synthetic_images,
        out_file,
        papersize=np.array([100.0, 100.0]),
        registration_marks=True,
        mark_inset=7,
        mark_arm=10,
    )

    assert out_file.is_file()


def test_print_cards_matplotlib_gap_and_bleed(synthetic_images: list[str], tmp_path: Path) -> None:
    from mtg_proxies import print_cards_matplotlib

    out_file = tmp_path / "gap_bleed.pdf"
    print_cards_matplotlib(synthetic_images, out_file, gap=3, bleed=2)

    assert out_file.is_file()


def test_composite_rounded_corners() -> None:
    import numpy as np

    from mtg_proxies.print_cards import _composite_rounded

    image = np.zeros((100, 150, 4), dtype=np.float32)
    image[..., :3] = [1, 0, 0]
    image[..., 3] = 1
    result = _composite_rounded(image, np.array([15, 10]), np.ones(3))

    assert np.allclose(result[0, 0], [1, 1, 1])  # Rounded corner shows the background
    assert np.allclose(result[0, 75], [1, 0, 0])  # Straight edge is kept
    assert np.allclose(result[50, 75], [1, 0, 0])  # Center is kept
    assert result.min() >= 0
    assert result.max() <= 1


def test_write_cut_files_rounded(tmp_path: Path) -> None:
    import xml.etree.ElementTree as ET

    import numpy as np

    from mtg_proxies import write_cut_files

    cut_files = write_cut_files(
        2,
        tmp_path / "cut",
        papersize=np.array([100.0, 100.0]),
        cardsize=np.array([50.0, 70.0]),
        border_crop=0,
        gap=0,
        corner_radius=2.5,
    )

    assert cut_files == [tmp_path / "cut.svg"]
    root = ET.parse(cut_files[0]).getroot()
    assert root.attrib["width"] == "100.000mm"
    assert root.attrib["height"] == "100.000mm"
    paths = root.findall(".//{http://www.w3.org/2000/svg}path")
    assert len(paths) == 2
    assert paths[0].attrib["d"].startswith("M 2.500 15.000")
    assert "A 2.500 2.500" in paths[0].attrib["d"]


def test_effective_border_crop_keeps_rounded_cards_full_size() -> None:
    from mtg_proxies.print_cards import effective_border_crop

    # A physical corner rounder does not change the card outline, so rounded
    # cards print at full size instead of shrinking into a sleeve proxy.
    assert effective_border_crop(14, 2.5) == 0
    assert effective_border_crop(14, 0.0) == 14
    assert effective_border_crop(0, 2.5) == 0


def test_write_cut_files_rounded_ignores_border_crop(tmp_path: Path) -> None:
    import xml.etree.ElementTree as ET

    import numpy as np

    from mtg_proxies import write_cut_files

    cut_files = write_cut_files(
        1,
        tmp_path / "cut.svg",
        papersize=np.array([100.0, 100.0]),
        cardsize=np.array([50.0, 70.0]),
        border_crop=14,
        gap=0,
        corner_radius=2.5,
    )

    path = ET.parse(cut_files[0]).getroot().findall(".//{http://www.w3.org/2000/svg}path")[0]
    # Full 50 mm width: the straight edge ends 2.5 mm short of the 50 mm edge,
    # not at the ~48.1 mm width left by the default border crop.
    assert "H 47.500" in path.attrib["d"]


def test_write_cut_files_max_cards(tmp_path: Path) -> None:
    import numpy as np

    from mtg_proxies import write_cut_files

    paths = write_cut_files(
        7,
        tmp_path / "cut.svg",
        papersize=np.array([8.5 * 25.4, 11 * 25.4]),
        cardsize=np.array([2.5 * 25.4, 3.5 * 25.4]),
        border_crop=14,
        gap=1.5,
        max_cards=np.array([3, 2]),
    )

    assert len(paths) == 2
    assert paths[0].read_text(encoding="utf-8").count('<path id="card-') == 6
    assert paths[1].read_text(encoding="utf-8").count('<path id="card-') == 1


def test_write_cut_files_multiple_pages(tmp_path: Path) -> None:
    import xml.etree.ElementTree as ET

    import numpy as np

    from mtg_proxies import write_cut_files

    cut_files = write_cut_files(
        3,
        tmp_path / "cut.svg",
        papersize=np.array([100.0, 100.0]),
        cardsize=np.array([50.0, 70.0]),
        border_crop=0,
        gap=0,
        corner_radius=0,
    )

    assert cut_files == [tmp_path / "cut_1.svg", tmp_path / "cut_2.svg"]
    page_1 = ET.parse(cut_files[0]).getroot().findall(".//{http://www.w3.org/2000/svg}path")
    page_2 = ET.parse(cut_files[1]).getroot().findall(".//{http://www.w3.org/2000/svg}path")
    assert len(page_1) == 2
    assert len(page_2) == 1
    assert "A " not in page_1[0].attrib["d"]


def test_handcut_layout_letter() -> None:
    import numpy as np

    from mtg_proxies import handcut_layout

    n_cards, trim_size, margin = handcut_layout(
        papersize=np.array([8.5 * 25.4, 11 * 25.4]),
        cardsize=np.array([2.5 * 25.4, 3.5 * 25.4]),
        border_crop=14,
        gap=0,
    )

    assert n_cards.tolist() == [3, 3]
    assert trim_size.tolist() == pytest.approx([61.11342282, 86.50653846])
    assert margin.tolist() == pytest.approx([16.27986577, 9.94019231])


def test_slider_layout_letter_nine_cards_with_bleed() -> None:
    import numpy as np

    from mtg_proxies import slider_layout

    n_cards, trim_size, margin, gutter = slider_layout(
        papersize=np.array([8.5 * 25.4, 11 * 25.4]),
        cardsize=np.array([2.5 * 25.4, 3.5 * 25.4]),
        border_crop=14,
        bleed=2.0,
    )

    assert n_cards.tolist() == [3, 3]
    assert trim_size.tolist() == pytest.approx([61.11342282, 86.50653846])
    assert gutter == pytest.approx(4.0)
    assert margin.tolist() == pytest.approx([12.27986577, 5.94019231])


def test_slider_layout_full_size_nine_cards_with_2mm_bleed() -> None:
    import numpy as np

    from mtg_proxies import slider_layout

    n_cards, _, margin, gutter = slider_layout(
        papersize=np.array([8.5 * 25.4, 11 * 25.4]),
        cardsize=np.array([2.5 * 25.4, 3.5 * 25.4]),
        border_crop=0,
        bleed=2.0,
    )

    assert n_cards.tolist() == [3, 3]
    assert gutter == pytest.approx(4.0)
    assert margin.tolist() == pytest.approx([8.7, 2.35])


def test_slider_guides_cross_every_card_corner() -> None:
    import numpy as np

    from mtg_proxies.print_cards import _slider_guide_segments

    papersize = np.array([100.0, 100.0])
    margin = np.array([10.0, 20.0])
    trim_size = np.array([20.0, 30.0])
    segments = _slider_guide_segments(
        papersize=papersize,
        margin=margin,
        trim_size=trim_size,
        gutter=4.0,
        count=4,
        n_cards=np.array([2, 2]),
    )

    # Each card edge is a full-page line, so the lines cross at every corner.
    assert [(10.0, 0.0), (10.0, 100.0)] in segments
    assert [(0.0, 20.0), (100.0, 20.0)] in segments
    assert len(segments) == 8
    # The only card surface a line may touch is the edge itself.
    for (x1, y1), (x2, y2) in segments:
        for step in range(11):
            x = x1 + (x2 - x1) * step / 10
            y = y1 + (y2 - y1) * step / 10
            for column in range(2):
                for row in range(2):
                    left = margin[0] + column * (trim_size[0] + 4.0)
                    top = margin[1] + row * (trim_size[1] + 4.0)
                    inside = left + 1e-6 < x < left + trim_size[0] - 1e-6
                    inside &= top + 1e-6 < y < top + trim_size[1] - 1e-6
                    assert not inside


def test_slider_guides_only_cover_used_cards() -> None:
    import numpy as np

    from mtg_proxies.print_cards import _slider_guide_segments

    segments = _slider_guide_segments(
        papersize=np.array([100.0, 100.0]),
        margin=np.array([10.0, 20.0]),
        trim_size=np.array([20.0, 30.0]),
        gutter=4.0,
        count=1,
        n_cards=np.array([2, 2]),
    )

    xs = {segment[0][0] for segment in segments if segment[0][0] == segment[1][0]}
    ys = {segment[0][1] for segment in segments if segment[0][1] == segment[1][1]}
    assert xs == {10.0, 30.0}
    assert ys == {20.0, 50.0}


def test_draw_slider_guides_draws_full_page_lines() -> None:
    import numpy as np

    from mtg_proxies.print_cards import _draw_slider_guides

    class FakePdf:
        def __init__(self) -> None:
            self.lines: list[tuple[float, float, float, float]] = []

        def set_draw_color(self, *args: int) -> None:
            pass

        def set_line_width(self, width: float) -> None:
            pass

        def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
            self.lines.append((x1, y1, x2, y2))

    pdf = FakePdf()
    _draw_slider_guides(
        pdf,
        papersize=np.array([100.0, 100.0]),
        margin=np.array([10.0, 20.0]),
        trim_size=np.array([20.0, 30.0]),
        gutter=4.0,
        count=4,
        n_cards=np.array([2, 2]),
    )

    assert (10.0, 0.0, 10.0, 100.0) in pdf.lines
    assert (0.0, 20.0, 100.0, 20.0) in pdf.lines


def test_cut_guide_segments_stay_in_margins() -> None:
    import numpy as np

    from mtg_proxies.print_cards import _cut_guide_segments

    segments = _cut_guide_segments(
        papersize=np.array([100.0, 100.0]),
        margin=np.array([10.0, 20.0]),
        trim_size=np.array([20.0, 30.0]),
        gap=0.0,
        count=4,
        n_cards=np.array([2, 2]),
    )

    # Three vertical and three horizontal card edges, each a full-page line.
    assert len(segments) == 6
    assert [(10.0, 0.0), (10.0, 100.0)] in segments
    assert [(0.0, 20.0), (100.0, 20.0)] in segments


def test_cut_guide_segments_only_cover_used_cards() -> None:
    import numpy as np

    from mtg_proxies.print_cards import _cut_guide_segments

    segments = _cut_guide_segments(
        papersize=np.array([100.0, 100.0]),
        margin=np.array([10.0, 20.0]),
        trim_size=np.array([20.0, 30.0]),
        gap=0.0,
        count=1,
        n_cards=np.array([2, 2]),
    )

    # One card has only its two outer edges, not the empty second slot.
    xs = {segment[0][0] for segment in segments if segment[0][0] == segment[1][0]}
    ys = {segment[0][1] for segment in segments if segment[0][1] == segment[1][1]}
    assert xs == {10.0, 30.0}
    assert ys == {20.0, 50.0}

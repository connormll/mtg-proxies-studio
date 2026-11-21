from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


def test_write_plt_file_layout(tmp_path: Path) -> None:
    from mtg_proxies.makercraft import write_plt_file

    plt_file = write_plt_file(
        tmp_path / "cut",
        papersize=np.array([100.0, 100.0]),
        cardsize=np.array([50.0, 70.0]),
        border_crop=0,
        gap=0,
        corner_radius=2.5,
        mark_inset=7,
        overcut=1,
    )

    assert plt_file == tmp_path / "cut.plt"
    text = plt_file.read_text(encoding="utf-8")
    assert "IN;\n" in text
    assert "TB25,3440,3440;" in text
    assert "CT1;" in text
    assert text.count("\nU") == 3  # Two full-sheet slots plus the final U0,0
    assert "U3120,3620;" in text
    assert "D3120,3580;" in text  # 1 mm overcut along the top edge
    assert text.endswith("U0,0;\n@;\n@;\n")


def test_makercraft_layout_letter() -> None:
    from mtg_proxies.print_cards import makercraft_layout

    max_cards, inset = makercraft_layout(
        papersize=np.array([8.5 * 25.4, 11 * 25.4]),
        cardsize=np.array([2.5 * 25.4, 3.5 * 25.4]),
        border_crop=14,
        gap=1.5,
    )

    assert max_cards.tolist() == [3, 2]
    assert inset == pytest.approx(10.0)


def test_write_plt_file_letter_safe(tmp_path: Path) -> None:
    from mtg_proxies.makercraft import write_plt_file

    plt_file = write_plt_file(
        tmp_path / "letter.plt",
        papersize=np.array([8.5 * 25.4, 11 * 25.4]),
        cardsize=np.array([2.5 * 25.4, 3.5 * 25.4]),
        border_crop=14,
        gap=1.5,
        corner_radius=2.5,
        mark_inset=10,
        overcut=1,
        max_cards=np.array([3, 2]),
    )

    text = plt_file.read_text(encoding="utf-8")
    assert "TB25,10376,7836;" in text
    assert text.count("\nU") == 7  # Six card slots plus the final U0,0


def test_write_plt_file_is_full_sheet(tmp_path: Path) -> None:
    from mtg_proxies.makercraft import write_plt_file

    plt_file = write_plt_file(
        tmp_path / "makercraft.plt",
        papersize=np.array([203.2, 254.0]),
        cardsize=np.array([63.5, 88.9]),
        border_crop=14,
        gap=1.5,
        corner_radius=2.5,
        mark_inset=7,
        overcut=1,
    )

    text = plt_file.read_text(encoding="utf-8")
    assert "TB25,9600,7568;" in text
    assert text.count("\nU") == 7  # Six card slots plus the final U0,0
    assert "U8290,7411;" in text

    second = write_plt_file(
        tmp_path / "second.plt",
        papersize=np.array([203.2, 254.0]),
        cardsize=np.array([63.5, 88.9]),
        border_crop=14,
        gap=1.5,
        corner_radius=2.5,
        mark_inset=7,
        overcut=1,
    )
    assert second.read_bytes() == plt_file.read_bytes()


def test_load_plt_payload_injects_settings(tmp_path: Path) -> None:
    from mtg_proxies.makercraft import load_plt_payload

    plt_file = tmp_path / "job.plt"
    plt_file.write_text("IN;\nPA;\nP0;\nU0,0;\n@;\n", encoding="utf-8")

    payload = load_plt_payload(plt_file, force=55, speed=5).decode("utf-8")

    assert "US5;\nVS5;\n!FS55;\nU0,0;" in payload
    assert payload.endswith("@;\n")


def test_registration_mark_segments() -> None:
    from mtg_proxies.print_cards import _registration_mark_segments

    segments = _registration_mark_segments(np.array([100.0, 100.0]), inset=7, arm=10)

    assert len(segments) == 5
    assert segments[0] == [(7.0, 17.0), (7.0, 7.0), (17.0, 7.0)]
    assert segments[4] == [(73.0, 93.0), (78.0, 93.0)]

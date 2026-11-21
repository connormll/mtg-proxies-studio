from pathlib import Path
from unittest.mock import patch

import pytest


def test_papersize_letter() -> None:
    from mtg_proxies.cli import papersize

    assert papersize("letter").tolist() == [8.5, 11.0]


def test_send_dry_run(capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
    """The send command should print the payload without touching hardware."""
    from mtg_proxies.cli import main

    plt_file = tmp_path / "job.plt"
    plt_file.write_text("IN;\nPA;\nP0;\nU0,0;\n@;\n", encoding="utf-8")

    with patch("sys.argv", ["mtg-proxies", "send", str(plt_file), "--dry-run"]):
        main()

    captured = capsys.readouterr()
    assert "IN;\nPA;\nP0;\nU0,0;\n@;" in captured.out


def test_print_makercraft_writes_one_template(tmp_path: Path) -> None:
    """A print run should write one reusable full-sheet template, not one per page."""
    from mtg_proxies.cli import main

    outfile = tmp_path / "deck.pdf"
    argv = [
        "mtg-proxies",
        "print",
        "decklist.txt",
        str(outfile),
        "--paper",
        "8x10",
        "--gap",
        "1.5",
        "--makercraft",
    ]

    with (
        patch("sys.argv", argv),
        patch("mtg_proxies.cli.parse_decklist_spec", return_value=object()),
        patch("mtg_proxies.cli.fetch_scans_scryfall", return_value=["front.png", "back.png"]),
        patch("mtg_proxies.cli.print_cards_fpdf"),
    ):
        main()

    template = tmp_path / "makercraft.plt"
    assert template.is_file()
    assert not list(tmp_path.glob("makercraft_*.plt"))
    assert not list(tmp_path.glob("*.svg"))
    text = template.read_text(encoding="utf-8")
    assert text.count("\nU") == 7  # Six card slots plus the final U0,0


def test_print_makercraft_letter_uses_safe_layout(tmp_path: Path) -> None:
    """Letter MakerCraft output should fit the C10 camera and cut area."""
    from mtg_proxies.cli import main

    outfile = tmp_path / "letter.pdf"
    argv = [
        "mtg-proxies",
        "print",
        "decklist.txt",
        str(outfile),
        "--paper",
        "8.5x11",
        "--gap",
        "1.5",
        "--makercraft",
    ]

    with (
        patch("sys.argv", argv),
        patch("mtg_proxies.cli.parse_decklist_spec", return_value=object()),
        patch("mtg_proxies.cli.fetch_scans_scryfall", return_value=["front.png", "back.png"]),
        patch("mtg_proxies.cli.print_cards_fpdf") as print_cards,
    ):
        main()

    assert print_cards.call_args.kwargs["mark_inset"] == pytest.approx(10.0)
    assert print_cards.call_args.kwargs["max_cards"].tolist() == [3, 2]

    template = tmp_path / "makercraft.plt"
    text = template.read_text(encoding="utf-8")
    assert text.startswith("IN;\nTB25,10376,7836;\nCT1;")
    assert text.count("\nU") == 7


def test_print_handcut_writes_guides_without_machine_files(tmp_path: Path) -> None:
    """--handcut should add PDF guides, use square corners, and skip machine files."""
    from mtg_proxies.cli import main

    outfile = tmp_path / "handcut.pdf"
    argv = [
        "mtg-proxies",
        "print",
        "decklist.txt",
        str(outfile),
        "--paper",
        "8.5x11",
        "--handcut",
    ]

    with (
        patch("sys.argv", argv),
        patch("mtg_proxies.cli.parse_decklist_spec", return_value=object()),
        patch("mtg_proxies.cli.fetch_scans_scryfall", return_value=["front.png", "back.png"]),
        patch("mtg_proxies.cli.print_cards_fpdf") as print_cards,
    ):
        main()

    kwargs = print_cards.call_args.kwargs
    assert kwargs["handcut"] is True
    assert kwargs["corner_radius"] == pytest.approx(0.0)
    assert kwargs["cropmarks"] is False
    assert kwargs["registration_marks"] is False
    assert not list(tmp_path.glob("*.plt"))
    assert not list(tmp_path.glob("*.svg"))


def test_print_handcut_keeps_explicit_corner_radius(tmp_path: Path) -> None:
    """An explicit --corner-radius should still work with --handcut."""
    from mtg_proxies.cli import main

    argv = [
        "mtg-proxies",
        "print",
        "decklist.txt",
        str(tmp_path / "handcut.pdf"),
        "--paper",
        "8.5x11",
        "--handcut",
        "--corner-radius",
        "2.5",
    ]

    with (
        patch("sys.argv", argv),
        patch("mtg_proxies.cli.parse_decklist_spec", return_value=object()),
        patch("mtg_proxies.cli.fetch_scans_scryfall", return_value=["front.png"]),
        patch("mtg_proxies.cli.print_cards_fpdf") as print_cards,
    ):
        main()

    assert print_cards.call_args.kwargs["corner_radius"] == pytest.approx(2.5)


def test_print_handcut_rejects_makercraft(tmp_path: Path) -> None:
    """Hand cutting and camera registration marks are separate workflows."""
    from mtg_proxies.cli import main

    argv = [
        "mtg-proxies",
        "print",
        "decklist.txt",
        str(tmp_path / "deck.pdf"),
        "--handcut",
        "--makercraft",
    ]

    with patch("sys.argv", argv), pytest.raises(SystemExit):
        main()


def test_print_slider_uses_bleed_and_margin_guides(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """--slider should add bleed, use the nine-card layout, and skip machine files."""
    from mtg_proxies.cli import main

    argv = [
        "mtg-proxies",
        "print",
        "decklist.txt",
        str(tmp_path / "slider.pdf"),
        "--paper",
        "8.5x11",
        "--slider",
    ]

    with (
        patch("sys.argv", argv),
        patch("mtg_proxies.cli.parse_decklist_spec", return_value=object()),
        patch("mtg_proxies.cli.fetch_scans_scryfall", return_value=["front.png", "back.png"]),
        patch("mtg_proxies.cli.print_cards_fpdf") as print_cards,
    ):
        main()

    kwargs = print_cards.call_args.kwargs
    assert kwargs["slider"] is True
    assert kwargs["handcut"] is False
    assert kwargs["bleed"] == pytest.approx(2.0)
    assert kwargs["corner_radius"] == pytest.approx(0.0)
    assert kwargs["cropmarks"] is False
    assert kwargs["registration_marks"] is False
    assert not list(tmp_path.glob("*.plt"))
    assert not list(tmp_path.glob("*.svg"))
    assert "Slider layout: 9 cards/page (3x3)" in capsys.readouterr().out


def test_print_slider_rejects_handcut(tmp_path: Path) -> None:
    """Sliding-trimmer and handcut modes have different guide styles."""
    from mtg_proxies.cli import main

    argv = [
        "mtg-proxies",
        "print",
        "decklist.txt",
        str(tmp_path / "deck.pdf"),
        "--slider",
        "--handcut",
    ]

    with patch("sys.argv", argv), pytest.raises(SystemExit):
        main()


def test_print_no_tokens(capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
    """The --no-tokens flag should leave token cards out of the print."""
    from mtg_proxies.cli import main
    from mtg_proxies.decklists import Decklist

    decklist = Decklist()
    decklist.append_card(1, {"name": "Sol Ring", "layout": "normal", "type_line": "Artifact"})
    decklist.append_card(1, {"name": "Treasure", "layout": "token", "type_line": "Token Artifact — Treasure"})

    argv = [
        "mtg-proxies",
        "print",
        "decklist.txt",
        str(tmp_path / "deck.pdf"),
        "--no-tokens",
        "--no-cut-file",
    ]

    with (
        patch("sys.argv", argv),
        patch("mtg_proxies.cli.parse_decklist_spec", return_value=decklist),
        patch("mtg_proxies.cli.fetch_scans_scryfall", return_value=["sol-ring.png"]) as fetch,
        patch("mtg_proxies.cli.print_cards_fpdf"),
    ):
        main()

    printed_decklist = fetch.call_args.args[0]
    assert [card["name"] for card in printed_decklist.cards] == ["Sol Ring"]
    assert "Excluded 1 token(s) from the print." in capsys.readouterr().out


def test_print_applies_printing_override(tmp_path: Path) -> None:
    """--printing should replace the selected print before fetching scans."""
    from mtg_proxies import scryfall
    from mtg_proxies.cli import main
    from mtg_proxies.decklists import Decklist

    decklist = Decklist()
    decklist.append_card(1, scryfall.get_card("Command Tower", "CMD", "269"))
    expected = scryfall.get_card("Command Tower", "C15", "281")

    argv = [
        "mtg-proxies",
        "print",
        "decklist.txt",
        str(tmp_path / "deck.pdf"),
        "--no-cut-file",
        "--printing",
        "Command Tower=C15 281",
    ]

    with (
        patch("sys.argv", argv),
        patch("mtg_proxies.cli.parse_decklist_spec", return_value=decklist),
        patch("mtg_proxies.cli.fetch_scans_scryfall", return_value=["tower.png"]) as fetch,
        patch("mtg_proxies.cli.print_cards_fpdf"),
    ):
        main()

    printed_decklist = fetch.call_args.args[0]
    assert printed_decklist.cards[0]["id"] == expected["id"]


def test_printings_command(capsys: pytest.CaptureFixture) -> None:
    """The printings command should list choices and show the override syntax."""
    from mtg_proxies.cli import main

    with patch("sys.argv", ["mtg-proxies", "printings", "Command Tower", "--limit", "3"]):
        main()

    output = capsys.readouterr().out
    assert "Command Tower: " in output
    assert "unique art" in output
    assert "Command Tower (" in output
    assert "Choose one with --printing" in output


def test_convert_applies_printing_override(tmp_path: Path) -> None:
    """--printing should be written to the converted decklist."""
    from mtg_proxies import scryfall
    from mtg_proxies.cli import main
    from mtg_proxies.decklists import Decklist

    decklist = Decklist()
    decklist.append_card(1, scryfall.get_card("Command Tower", "CMD", "269"))
    outfile = tmp_path / "decklist.txt"

    argv = [
        "mtg-proxies",
        "convert",
        "decklist.txt",
        str(outfile),
        "--printing",
        "Command Tower=C15 281",
    ]

    with (
        patch("sys.argv", argv),
        patch("mtg_proxies.cli.parse_decklist_spec", return_value=decklist),
    ):
        main()

    assert outfile.read_text(encoding="utf-8").strip() == "1 Command Tower (C15) 281"


def test_main(capsys: pytest.CaptureFixture) -> None:
    """Test the main function.

    Ensure that ther a are no import errors and that the help message is printed correctly.
    """
    from mtg_proxies.cli import main

    # Mock argv
    with patch("sys.argv", ["mtg-proxies", "--help"]), pytest.raises(SystemExit):
        main()

    # Check output
    captured = capsys.readouterr()
    assert (
        captured.out
        == """usage: mtg-proxies [-h]
                   {print,printings,convert,tokens,deck_value,send,gui} ...

Create high quality MtG proxies from your decklist.

positional arguments:
  {print,printings,convert,tokens,deck_value,send,gui}
    print               Prepare a decklist for printing
    printings           List available printings for a card
    convert             Convert a decklist to text or arena format
    tokens              Append the created tokens to a decklist
    deck_value          Show deck value decomposition
    send                Send an HPGL .plt cut file to a Skycut/MakerCraft over
                        USB
    gui                 Start the local browser interface

options:
  -h, --help            show this help message and exit
"""
    )

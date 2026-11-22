import argparse
from collections.abc import Container
from pathlib import Path

import numpy as np

from mtg_proxies import (
    fetch_scans_scryfall,
    handcut_layout,
    makercraft_layout,
    print_cards_fpdf,
    print_cards_matplotlib,
    slider_layout,
    write_cut_files,
)
from mtg_proxies.deck_value import show_deck_value
from mtg_proxies.decklists import archidekt, manastack, parse_decklist
from mtg_proxies.decklists.decklist import Decklist
from mtg_proxies.format import format_print
from mtg_proxies.makercraft import list_devices, send_plt, write_plt_file
from mtg_proxies.print_cards import SLIDER_DEFAULT_BLEED, effective_border_crop
from mtg_proxies.printings import PrintingOverride, apply_printing_overrides, parse_printing_override
from mtg_proxies.scryfall import get_faces, get_printings, unique_artworks
from mtg_proxies.tokens import get_tokens


def parse_decklist_spec(decklist_spec: str, warn_levels: Container[str] = ("ERROR", "WARNING", "COSMETIC")) -> Decklist:
    """Attempt to parse a decklist from different locations.

    Args:
        decklist_spec: File path or ManaStack id
        warn_levels: Levels of warnings to show
    """
    print("Parsing decklist ...")
    if Path(decklist_spec).is_file():  # Decklist is file
        decklist, ok, warnings = parse_decklist(decklist_spec)
    elif decklist_spec.lower().startswith("manastack:") and decklist_spec.split(":")[-1].isdigit():
        # Decklist on Manastack
        manastack_id = decklist_spec.split(":")[-1]
        decklist, ok, warnings = manastack.parse_decklist(manastack_id)
    elif decklist_spec.lower().startswith("archidekt:") and decklist_spec.split(":")[-1].isdigit():
        # Decklist on Archidekt
        archidekt_id = decklist_spec.split(":")[-1]
        decklist, ok, warnings = archidekt.parse_decklist(archidekt_id)
    else:
        print(f"Cant find decklist '{decklist_spec}'")
        quit()

    # Print warnings
    for warning in warnings:
        if warning.level in warn_levels:
            print(warning)

    # Check for grave errors
    if not ok:
        print("Decklist contains invalid card names. Fix errors above before reattempting.")
        quit()

    print(f"Found {decklist.total_count} cards in total with {decklist.total_count_unique} unique cards.")

    return decklist


def papersize(string: str) -> np.ndarray:
    """Parse paper size from string.

    Supports preconfigured formats (e.g. "a4") and custom formats (e.g. "8.5x11" in inches).
    """
    spec = string.lower()
    if spec == "a4":
        return np.array([21, 29.7]) / 2.54
    if spec == "letter":
        return np.array([8.5, 11.0])
    if "x" in spec:
        split = spec.split("x")
        return np.array([float(split[0]), float(split[1])])
    raise argparse.ArgumentTypeError()


def gap_mm(string: str) -> float:
    """Parse the gap between cards in mm."""
    try:
        value = float(string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid gap: {string!r}") from None
    if not 0 <= value <= 3:
        raise argparse.ArgumentTypeError("gap must be between 0 and 3 mm")
    return value


def bleed_mm(string: str) -> float:
    """Parse the bleed around each card in mm."""
    try:
        value = float(string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid bleed: {string!r}") from None
    if not 0 <= value <= 10:
        raise argparse.ArgumentTypeError("bleed must be between 0 and 10 mm")
    return value


def corner_radius_mm(string: str) -> float:
    """Parse the corner radius of printed cards in mm."""
    try:
        value = float(string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid corner radius: {string!r}") from None
    if not 0 <= value <= 10:
        raise argparse.ArgumentTypeError("corner radius must be between 0 and 10 mm")
    return value


def cutter_pressure(string: str) -> int:
    """Parse a Skycut pressure value."""
    try:
        value = int(string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid pressure: {string!r}") from None
    if not 1 <= value <= 160:
        raise argparse.ArgumentTypeError("pressure must be between 1 and 160")
    return value


def cutter_speed(string: str) -> int:
    """Parse a Skycut speed value."""
    try:
        value = int(string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid speed: {string!r}") from None
    if not 1 <= value <= 12:
        raise argparse.ArgumentTypeError("speed must be between 1 and 12")
    return value


def printing_override(string: str) -> PrintingOverride:
    """Parse a card printing override."""
    try:
        return parse_printing_override(string)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def gui_port(string: str) -> int:
    """Parse a TCP port for the local web interface."""
    try:
        value = int(string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid port: {string!r}") from None
    if not 1 <= value <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return value


def apply_overrides(decklist: Decklist, overrides: list[PrintingOverride]) -> Decklist:
    """Apply printing overrides or exit with a helpful error."""
    try:
        decklist, unmatched = apply_printing_overrides(decklist, overrides)
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from None

    for override in unmatched:
        print(f"Warning: {override.card_name!r} is not in the decklist; printing override ignored.")
    return decklist


def _artwork_id(card: dict) -> str:
    """Return the identifier used to group printings by artwork."""
    face = get_faces(card)[0]
    return face.get("illustration_id") or card["id"]


def show_printings(card_name: str, *, show_all: bool, limit: int | None, urls: bool) -> None:
    """Print the available printings for a card."""
    printings = get_printings(card_name)
    if not printings:
        print(f"No printings found for {card_name!r}.")
        raise SystemExit(1)

    recommended = printings[0]
    artworks = unique_artworks(printings)
    if not show_all:
        recommended_artwork = _artwork_id(recommended)
        artworks = [recommended if _artwork_id(card) == recommended_artwork else card for card in artworks]

    def display_order(card: dict) -> tuple[bool, str, str, str]:
        return (
            card["id"] != recommended["id"],
            card.get("released_at") or "9999-12-31",
            card.get("set") or "",
            str(card.get("collector_number") or ""),
        )

    selected = sorted(printings if show_all else artworks, key=display_order)
    if limit is not None:
        selected = selected[:limit]

    total = len(printings)
    print(f"{recommended['name']}: {total} printing{'s' if total != 1 else ''}")
    if not show_all and len(artworks) != total:
        count = len(artworks)
        print(f"{count} unique artwork{'s' if count != 1 else ''} (use --all to see every printing)")
    print()
    print("  * = recommended; alternatives are listed oldest first")

    for card in selected:
        marker = "*" if card["id"] == recommended["id"] else " "
        details = [card.get("set_name") or card["set"].upper(), card.get("released_at") or "unknown release"]
        if card.get("border_color") not in {None, "black"}:
            details.append(f"{card['border_color']} border")
        line = f"{marker} {format_print(card)} — " + ", ".join(details)
        if urls and card.get("scryfall_uri"):
            line += f" — {card['scryfall_uri']}"
        print(line)

    available = len(printings) if show_all else len(artworks)
    if len(selected) < available:
        print(f"  ... and {available - len(selected)} more; use --limit to show more")

    if len(selected) > 1:
        example = selected[1]
    elif selected:
        example = selected[0]
    else:
        example = recommended
    print()
    print(f'Choose one with --printing "{example["name"]}={example["set"].upper()} {example["collector_number"]}",')
    print(f'or add "({example["set"].upper()}) {example["collector_number"]}" to its decklist line.')


def main() -> None:
    """Run mtg-proxies CLI."""
    parser = argparse.ArgumentParser("mtg-proxies", description="Create high quality MtG proxies from your decklist.")
    subparsers = parser.add_subparsers(dest="command")

    # Print tool
    print_parser = subparsers.add_parser(
        "print",
        help="Prepare a decklist for printing",
        description="Prepare a decklist for printing.",
    )
    print_parser.add_argument(
        "decklist",
        help="path to a decklist in text/arena format, or manastack:{manastack_id}, or archidekt:{archidekt_id}",
    )
    print_parser.add_argument("outfile", help="output file. Supports pdf, png and jpg.")
    print_parser.add_argument(
        "--dpi",
        help="dpi of output file for raster formats (png, jpg); ignored for pdf (default: %(default)d)",
        type=int,
        default=300,
    )
    print_parser.add_argument(
        "--paper",
        help="paper size in inches, or a4/letter (default: %(default)s)",
        type=papersize,
        default="a4",
        metavar="WIDTHxHEIGHT",
    )
    print_parser.add_argument(
        "--scale",
        help="scaling factor for printed cards (default: %(default)s)",
        type=float,
        default=1.0,
        metavar="FLOAT",
    )
    print_parser.add_argument(
        "--border_crop",
        help=(
            "how much to crop inner borders of printed cards, in source image pixels; "
            "ignored for rounded cards, which print at full size (default: %(default)s)"
        ),
        type=int,
        default=14,
        metavar="PIXELS",
    )
    print_parser.add_argument(
        "--gap",
        help="gap between cards in mm, between 0 and 3 (default: %(default)s)",
        type=gap_mm,
        default=0.0,
        metavar="MM",
    )
    print_parser.add_argument(
        "--bleed",
        help=(
            "add mirrored-edge bleed around each card in mm, between 0 and 10; "
            "use without a value for 3 mm (default: 0, or 2 with --slider)"
        ),
        type=bleed_mm,
        nargs="?",
        const=3.0,
        default=None,
        metavar="MM",
    )
    print_parser.add_argument(
        "--corner-radius",
        "--corner_radius",
        help=(
            "corner radius of printed cards in mm, between 0 and 10; 0 disables rounding "
            "and keeps the sleeve-proxy border crop; rounded cards print at full size "
            "(default: 2.5, or 0 with --handcut/--slider)"
        ),
        type=corner_radius_mm,
        default=None,
        metavar="MM",
    )
    print_parser.add_argument(
        "--cut-file",
        help=(
            "write SVG cut file(s) for a cutting machine; PATH sets the base name "
            "(default: <outfile>_cut.svg, numbered per page for multi-page outputs)"
        ),
        type=Path,
        default=None,
        metavar="PATH",
    )
    print_parser.add_argument(
        "--no-cut-file",
        dest="cut_file",
        action="store_const",
        const=False,
        help="do not write SVG cut file(s)",
    )
    print_parser.add_argument(
        "--makercraft",
        help=(
            "add Skycut/MakerCraft registration marks and write one reusable full-sheet HPGL .plt template; "
            "SVG cut files are skipped unless --cut-file is given"
        ),
        action="store_true",
    )
    print_parser.add_argument(
        "--handcut",
        "--hand-cut",
        help=(
            "add cut lines to the PDF for hand trimming with a guillotine or rotary trimmer; "
            "uses square corners unless --corner-radius is given, and skips SVG cut files unless --cut-file is given"
        ),
        action="store_true",
    )
    print_parser.add_argument(
        "--slider",
        "--sliding-trimmer",
        help=(
            "optimize the PDF for a manual sliding-blade paper trimmer: use the largest bleed layout, "
            "print full-page cut lines along every card edge, use square corners unless --corner-radius "
            "is given, and skip SVG cut files unless --cut-file is given"
        ),
        action="store_true",
    )
    print_parser.add_argument(
        "--mark-inset",
        help=(
            "distance of MakerCraft registration marks from the page edge in mm; "
            "raised automatically when needed for the C10 (default: %(default)s)"
        ),
        type=float,
        default=7.0,
        metavar="MM",
    )
    print_parser.add_argument(
        "--mark-arm",
        help="arm length of the L-shaped MakerCraft registration marks in mm (default: %(default)s)",
        type=float,
        default=10.0,
        metavar="MM",
    )
    print_parser.add_argument(
        "--mark-stroke",
        help="line width of the MakerCraft registration marks in mm (default: %(default)s)",
        type=float,
        default=1.0,
        metavar="MM",
    )
    print_parser.add_argument(
        "--overcut",
        help="extend MakerCraft cut paths past the start to close the knife seam in mm (default: %(default)s)",
        type=float,
        default=1.0,
        metavar="MM",
    )
    print_parser.add_argument(
        "--plt-file",
        help="path for the reusable MakerCraft .plt template (default: makercraft.plt next to the PDF)",
        type=Path,
        default=None,
        metavar="PATH",
    )
    print_parser.add_argument(
        "--no-basic-lands",
        help="exclude basic lands from the print",
        action="store_true",
    )
    print_parser.add_argument(
        "--no-tokens",
        help="exclude tokens from the print",
        action="store_true",
    )
    print_parser.add_argument(
        "--background",
        help='background color, either by name or by hex code (e.g. black or "#ff0000", default: %(default)s)',
        type=str,
        default=None,
        metavar="COLOR",
    )
    print_parser.add_argument(
        "--cropmarks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="add crop marks (png, jpg); ignored for pdf ",
    )
    print_parser.add_argument(
        "--faces",
        help="which faces to print (default: %(default)s)",
        choices=["all", "front", "back"],
        default="all",
    )
    print_parser.add_argument(
        "--printing",
        dest="printings",
        action="append",
        type=printing_override,
        default=[],
        metavar="CARD=SET NUMBER",
        help=("use a specific printing for a card, e.g. 'Command Tower=C15 281'; can be repeated for multiple cards"),
    )

    # Printings tool
    printings_parser = subparsers.add_parser(
        "printings",
        help="List available printings for a card",
        description="List available printings for a card.",
    )
    printings_parser.add_argument("card", help="card name")
    printings_parser.add_argument(
        "--all",
        help="list every printing instead of one per artwork",
        action="store_true",
    )
    printings_parser.add_argument(
        "--limit",
        help="maximum number of printings to show",
        type=int,
        default=None,
        metavar="N",
    )
    printings_parser.add_argument(
        "--urls",
        help="show Scryfall links",
        action="store_true",
    )

    # Convert tool
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a decklist to text or arena format",
        description="Convert a decklist to text or arena format.",
    )
    convert_parser.add_argument(
        "decklist",
        help="path to a decklist in text/arena format, or manastack:{manastack_id}, or archidekt:{archidekt_id}",
    )
    convert_parser.add_argument("outfile", help="output file", type=Path)
    convert_parser.add_argument(
        "--format", help="output format (default: %(default)s)", choices=["arena", "text"], default="arena"
    )
    convert_parser.add_argument("--clean", action="store_true", help="remove all non-card lines")
    convert_parser.add_argument(
        "--printing",
        dest="printings",
        action="append",
        type=printing_override,
        default=[],
        metavar="CARD=SET NUMBER",
        help=("use a specific printing for a card, e.g. 'Command Tower=C15 281'; can be repeated for multiple cards"),
    )

    # Tokens tool
    tokens_parser = subparsers.add_parser(
        "tokens",
        help="Append the created tokens to a decklist",
        description="Append the created tokens to a decklist.",
    )
    tokens_parser.add_argument(
        "decklist",
        help="path to a decklist in text/arena format, or manastack:{manastack_id}, or archidekt:{archidekt_id}",
    )
    tokens_parser.add_argument(
        "--format", help="output format (default: %(default)s)", choices=["arena", "text"], default="arena"
    )

    # Deck value tool
    deck_value_parser = subparsers.add_parser(
        "deck_value", help="Show deck value decomposition", description="Show deck value decomposition."
    )
    deck_value_parser.add_argument(
        "decklist",
        help="path to a decklist in text/arena format, or manastack:{manastack_id}, or archidekt:{archidekt_id}",
    )
    deck_value_parser.add_argument(
        "--lump-threshold",
        help="lump together cards with lesser proportional value (default: %(default)s)",
        type=float,
        default=0.03,
        metavar="FLOAT",
    )

    # Send tool
    send_parser = subparsers.add_parser(
        "send",
        help="Send an HPGL .plt cut file to a Skycut/MakerCraft over USB",
        description="Send an HPGL .plt cut file to a Skycut/MakerCraft over USB.",
    )
    send_parser.add_argument(
        "plt",
        help="path to the .plt file to send",
        type=Path,
        nargs="?",
    )
    send_parser.add_argument(
        "--list",
        help="list connected Skycut/MakerCraft devices",
        action="store_true",
    )
    send_parser.add_argument(
        "--device",
        help="serial number or product-string substring to select a device",
        type=str,
        default=None,
    )
    send_parser.add_argument(
        "--yes",
        help="do not ask for confirmation before sending",
        action="store_true",
    )
    send_parser.add_argument(
        "--force",
        help="override cut pressure (1-160)",
        type=cutter_pressure,
        default=None,
    )
    send_parser.add_argument(
        "--speed",
        help="override speed (1-12)",
        type=cutter_speed,
        default=None,
    )
    send_parser.add_argument(
        "--dry-run",
        help="print the HPGL payload instead of sending",
        action="store_true",
    )

    # Local web interface
    gui_parser = subparsers.add_parser(
        "gui",
        help="Start the local browser interface",
        description="Start the local browser interface for preparing proxies.",
    )
    gui_parser.add_argument(
        "--port",
        help="port for the local web server (default: %(default)d)",
        type=gui_port,
        default=8000,
        metavar="PORT",
    )
    gui_parser.add_argument(
        "--no-browser",
        help="do not open the default browser automatically",
        action="store_true",
    )

    args = parser.parse_args()

    if args.command == "print":
        modes = {"--makercraft": args.makercraft, "--handcut": args.handcut, "--slider": args.slider}
        selected_modes = [name for name, enabled in modes.items() if enabled]
        if len(selected_modes) > 1:
            print_parser.error(f"{' and '.join(selected_modes)} cannot be combined")
        if args.makercraft and not args.outfile.lower().endswith(".pdf"):
            print_parser.error("--makercraft requires a PDF output")
        if args.handcut and not args.outfile.lower().endswith(".pdf"):
            print_parser.error("--handcut requires a PDF output")
        if args.slider and not args.outfile.lower().endswith(".pdf"):
            print_parser.error("--slider requires a PDF output")
        if args.plt_file is not None and not args.makercraft:
            print_parser.error("--plt-file requires --makercraft")
        if args.bleed is None:
            args.bleed = SLIDER_DEFAULT_BLEED if args.slider else 0.0
        if args.corner_radius is None:
            args.corner_radius = 0.0 if (args.handcut or args.slider) else 2.5
        args.border_crop = effective_border_crop(args.border_crop, args.corner_radius)

    match args.command:
        case "print":
            # Parse decklist
            decklist = parse_decklist_spec(args.decklist)

            if args.no_basic_lands:
                count_before = decklist.total_count
                decklist = decklist.without_basic_lands()
                print(f"Excluded {count_before - decklist.total_count} basic land(s) from the print.")

            if args.no_tokens:
                count_before = decklist.total_count
                decklist = decklist.without_tokens()
                print(f"Excluded {count_before - decklist.total_count} token(s) from the print.")

            if args.printings:
                decklist = apply_overrides(decklist, args.printings)

            # Fetch scans
            images = fetch_scans_scryfall(decklist, faces=args.faces)

            papersize_mm = args.paper * 25.4
            cardsize_mm = np.array([2.5, 3.5]) * 25.4 * args.scale
            max_cards = None
            mark_inset = args.mark_inset
            slider_gap = args.gap
            if args.makercraft:
                max_cards, mark_inset = makercraft_layout(
                    papersize_mm,
                    cardsize_mm,
                    args.border_crop,
                    args.gap,
                    mark_inset=args.mark_inset,
                    mark_arm=args.mark_arm,
                    mark_stroke=args.mark_stroke,
                )
                if not np.isclose(mark_inset, args.mark_inset):
                    print(
                        f"Using a {mark_inset:g} mm mark inset instead of {args.mark_inset:g} mm "
                        "to keep the marks inside the C10 area."
                    )
                cards_per_page = int(np.prod(max_cards))
                print(
                    f"MakerCraft layout: {cards_per_page} cards/page "
                    f"({max_cards[0]}x{max_cards[1]}), {mark_inset:g} mm mark inset."
                )
            elif args.handcut:
                handcut_cards, handcut_size, _ = handcut_layout(
                    papersize_mm,
                    cardsize_mm,
                    args.border_crop,
                    args.gap,
                )
                cards_per_page = int(np.prod(handcut_cards))
                print(
                    f"Handcut layout: {cards_per_page} cards/page "
                    f"({handcut_cards[0]}x{handcut_cards[1]}), "
                    f"{handcut_size[0]:.1f} x {handcut_size[1]:.1f} mm finished cards. "
                    "Cut along the black lines."
                )
            elif args.slider:
                slider_cards, slider_size, slider_margin, slider_gap = slider_layout(
                    papersize_mm,
                    cardsize_mm,
                    args.border_crop,
                    bleed=args.bleed,
                    gap=args.gap,
                )
                cards_per_page = int(np.prod(slider_cards))
                print(
                    f"Slider layout: {cards_per_page} cards/page "
                    f"({slider_cards[0]}x{slider_cards[1]}), "
                    f"{slider_size[0]:.1f} x {slider_size[1]:.1f} mm finished cards, "
                    f"{args.bleed:g} mm bleed, {slider_gap:g} mm gutters. "
                    f"Cut guides run along every card edge from page edge to page edge "
                    f"({slider_margin[0]:.1f} mm left/right, {slider_margin[1]:.1f} mm top/bottom)."
                )

            # Plot cards
            if args.outfile.endswith(".pdf"):
                import matplotlib.colors as colors

                background_color = args.background
                if background_color is not None:
                    background_color = (np.array(colors.to_rgb(background_color)) * 255).astype(int)

                print_cards_fpdf(
                    images,
                    args.outfile,
                    papersize=papersize_mm,
                    cardsize=cardsize_mm,
                    border_crop=args.border_crop,
                    background_color=background_color,
                    cropmarks=args.cropmarks and not (args.handcut or args.slider),
                    gap=args.gap,
                    bleed=args.bleed,
                    corner_radius=args.corner_radius,
                    registration_marks=args.makercraft,
                    mark_inset=mark_inset,
                    mark_arm=args.mark_arm,
                    mark_stroke=args.mark_stroke,
                    handcut=args.handcut,
                    slider=args.slider,
                    max_cards=max_cards,
                )
            else:
                print_cards_matplotlib(
                    images,
                    args.outfile,
                    papersize=args.paper,
                    cardsize=np.array([2.5, 3.5]) * args.scale,
                    dpi=args.dpi,
                    border_crop=args.border_crop,
                    background_color=args.background,
                    gap=args.gap,
                    bleed=args.bleed,
                    corner_radius=args.corner_radius,
                )

            # Write companion SVG cut file(s). MakerCraft, handcut, and slider
            # modes use their own guides by default, so SVG is only written when
            # explicitly requested.
            if args.cut_file is not False and not (
                (args.makercraft or args.handcut or args.slider) and args.cut_file is None
            ):
                cut_file = args.cut_file
                if cut_file is None:
                    outfile = Path(args.outfile)
                    cut_file = outfile.with_name(outfile.stem + "_cut.svg")
                cut_files = write_cut_files(
                    len(images),
                    cut_file,
                    papersize=papersize_mm,
                    cardsize=cardsize_mm,
                    border_crop=args.border_crop,
                    gap=slider_gap if args.slider else args.gap,
                    corner_radius=args.corner_radius,
                    max_cards=max_cards,
                )
                for cut_path in cut_files:
                    print(f"Writing cut file to {cut_path}")

            # Write one reusable Skycut/MakerCraft HPGL template
            if args.makercraft:
                plt_file = args.plt_file
                if plt_file is None:
                    outfile = Path(args.outfile)
                    plt_file = outfile.with_name("makercraft.plt")
                plt_path = write_plt_file(
                    plt_file,
                    papersize=papersize_mm,
                    cardsize=cardsize_mm,
                    border_crop=args.border_crop,
                    gap=args.gap,
                    corner_radius=args.corner_radius,
                    mark_inset=mark_inset,
                    overcut=args.overcut,
                    max_cards=max_cards,
                )
                print(f"MakerCraft cut template: {plt_path} (reuse for every page)")

        case "printings":
            show_printings(args.card, show_all=args.all, limit=args.limit, urls=args.urls)

        case "convert":
            # Parse decklist
            decklist = parse_decklist_spec(args.decklist, warn_levels=["ERROR", "WARNING"])

            if args.printings:
                decklist = apply_overrides(decklist, args.printings)

            # Write decklist
            decklist.save(args.outfile, fmt=args.format)

            print(f"Successfully wrote decklist to {args.outfile.resolve()}.")

        case "tokens":
            # Parse decklist
            decklist = parse_decklist_spec(args.decklist, warn_levels=["ERROR", "WARNING"])

            # Find tokens
            tokens = get_tokens(decklist)
            print(f"Found {len(tokens)} created tokens.")

            # Append tokens
            decklist.append_comment("")
            decklist.append_comment("Tokens")
            for token in tokens:
                decklist.append_card(1, token)

            # Write decklist
            out_file = args.decklist if Path(args.decklist).is_file() else f"{args.decklist.split(':')[-1]}.txt"
            decklist.save(out_file, fmt=args.format)

            print(f"Successfully appended tokens to {Path(out_file).resolve()}.")

        case "deck_value":
            # Parse decklist
            decklist = parse_decklist_spec(args.decklist, warn_levels=["ERROR", "WARNING"])

            # Show deck value decomposition
            show_deck_value(decklist, lump_threshold=args.lump_threshold)

        case "send":
            if args.list or args.plt is None:
                list_devices()
            else:
                try:
                    send_plt(
                        args.plt,
                        yes=args.yes,
                        force=args.force,
                        speed=args.speed,
                        dry_run=args.dry_run,
                        device=args.device,
                    )
                except (RuntimeError, FileNotFoundError) as exc:
                    print(f"Error: {exc}")
                    raise SystemExit(1) from None

        case "gui":
            try:
                from mtg_proxies.gui.launcher import run_gui

                run_gui(port=args.port, open_browser=not args.no_browser)
            except RuntimeError as exc:
                print(f"Error: {exc}")
                raise SystemExit(1) from None

"""MakerCraft/Skycut HPGL cut files and USB transport."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import numpy as np

from mtg_proxies.print_cards import (
    DEFAULT_MARK_INSET,
    MAX_CORNER_RADIUS,
    _layout,
    _trim_origin,
    effective_border_crop,
)

HPGL_SCALE = 40  # Skycut HPGL units per millimetre
SKYCUT_VID = 0x0483
SKYCUT_PID = 0x5750
DEFAULT_OVERCUT = 1.0


def _rounded_rect_points(
    origin: np.ndarray,
    size: np.ndarray,
    radius: float,
    segments_per_corner: int = 24,
) -> list[tuple[float, float]]:
    """Return a closed rounded rectangle as a point list, in millimetres."""
    x, y = (float(value) for value in origin)
    width, height = (float(value) for value in size)
    radius = min(max(float(radius), 0.0), width / 2, height / 2)

    if radius <= 0:
        return [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)]

    points: list[tuple[float, float]] = [(x + radius, y)]
    # Top edge
    points.append((x + width - radius, y))
    # Top-right corner
    for index in range(1, segments_per_corner + 1):
        angle = -math.pi / 2 + (math.pi / 2) * index / segments_per_corner
        points.append((
            x + width - radius + radius * math.cos(angle),
            y + radius + radius * math.sin(angle),
        ))
    # Right edge
    points.append((x + width, y + height - radius))
    # Bottom-right corner
    for index in range(1, segments_per_corner + 1):
        angle = (math.pi / 2) * index / segments_per_corner
        points.append((
            x + width - radius + radius * math.cos(angle),
            y + height - radius + radius * math.sin(angle),
        ))
    # Bottom edge
    points.append((x + radius, y + height))
    # Bottom-left corner
    for index in range(1, segments_per_corner + 1):
        angle = math.pi / 2 + (math.pi / 2) * index / segments_per_corner
        points.append((
            x + radius + radius * math.cos(angle),
            y + height - radius + radius * math.sin(angle),
        ))
    # Left edge
    points.append((x, y + radius))
    # Top-left corner
    for index in range(1, segments_per_corner + 1):
        angle = math.pi + (math.pi / 2) * index / segments_per_corner
        points.append((
            x + radius + radius * math.cos(angle),
            y + radius + radius * math.sin(angle),
        ))
    return points


def _with_overcut(points: list[tuple[float, float]], overcut: float) -> list[tuple[float, float]]:
    """Extend a closed outline past its start point by ``overcut`` millimetres."""
    if overcut <= 0 or len(points) < 2:
        return points
    x0, y0 = points[0]
    x1, y1 = points[1]
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length == 0:
        return points
    return [*points, (x0 + dx / length * overcut, y0 + dy / length * overcut)]


def _hpgl_point(x: float, y: float, max_x: float, max_y: float) -> tuple[int, int]:
    """Convert top-left millimetres to Skycut HPGL coordinates."""
    return (
        round((max_y - y) * HPGL_SCALE),
        round((max_x - x) * HPGL_SCALE),
    )


def _make_hpgl(
    polylines: list[list[tuple[float, float]]],
    papersize: np.ndarray,
    mark_inset: float = DEFAULT_MARK_INSET,
    speed: int | None = None,
    force: int | None = None,
) -> str:
    """Assemble a complete Skycut HPGL job for one page."""
    width, height = (float(value) for value in papersize)
    min_x = min_y = float(mark_inset)
    max_x = width - float(mark_inset)
    max_y = height - float(mark_inset)
    if max_x <= min_x or max_y <= min_y:
        raise ValueError("Registration mark inset is too large for the paper size")

    height_units = round((max_y - min_y) * HPGL_SCALE)
    width_units = round((max_x - min_x) * HPGL_SCALE)

    lines = ["IN;", f"TB25,{height_units},{width_units};", "CT1;", "PA;", "P0;"]
    if speed is not None:
        lines.extend([f"US{speed};", f"VS{speed};"])
    if force is not None:
        lines.append(f"!FS{force};")

    for polyline in polylines:
        for index, (x, y) in enumerate(polyline):
            hpgl_x, hpgl_y = _hpgl_point(x, y, max_x, max_y)
            lines.append(("U" if index == 0 else "D") + f"{hpgl_x},{hpgl_y};")

    lines.extend(["U0,0;", "@;", "@;"])
    return "\n".join(lines) + "\n"


def write_plt_file(
    filepath: str | Path,
    papersize: np.ndarray = np.array([210.0, 297.0]),
    cardsize: np.ndarray = np.array([2.5 * 25.4, 3.5 * 25.4]),
    border_crop: int = 14,
    gap: float = 0.0,
    corner_radius: float = 2.5,
    mark_inset: float = DEFAULT_MARK_INSET,
    overcut: float = DEFAULT_OVERCUT,
    speed: int | None = None,
    force: int | None = None,
    max_cards: np.ndarray | None = None,
) -> Path:
    """Write one reusable Skycut/MakerCraft HPGL template for a full sheet.

    The template contains every card slot in the print grid. The same file can
    be sent for every page of a print run; pages with fewer cards simply cut
    blank slots.

    Args:
        filepath: Path for the .plt file. A missing ``.plt`` suffix is added.
        papersize: Size of the paper in mm.
        cardsize: Size of a card in mm.
        border_crop: How many pixels to crop from the border of each card.
        gap: Gap between cards in mm.
        corner_radius: Corner radius of the cards in mm.
        mark_inset: Distance of the printed registration marks from the page edge in mm.
        overcut: How far to run past the start point to close the knife seam in mm.
        speed: Optional Skycut speed (1-12); omit to use the panel setting.
        force: Optional Skycut pressure (1-160); omit to use the panel setting.
        max_cards: Optional maximum ``(columns, rows)`` grid.

    Returns:
        The path of the written .plt file.
    """
    if gap < 0:
        raise ValueError(f"Gap must not be negative: {gap}")
    if not 0 <= corner_radius <= MAX_CORNER_RADIUS:
        raise ValueError(f"Corner radius must be between 0 and {MAX_CORNER_RADIUS:g} mm: {corner_radius}")
    if mark_inset <= 0:
        raise ValueError(f"Registration mark inset must be positive: {mark_inset}")
    if overcut < 0:
        raise ValueError(f"Overcut must not be negative: {overcut}")
    border_crop = effective_border_crop(border_crop, corner_radius)

    n_cards, trim_size, margin = _layout(papersize, cardsize, border_crop, gap, max_cards=max_cards)
    cards_per_sheet = int(np.prod(n_cards))
    if cards_per_sheet == 0:
        raise ValueError("Paper size is too small for a single card")

    polylines = []
    for card in range(cards_per_sheet):
        x = card % n_cards[0]
        y = card // n_cards[0]
        origin = _trim_origin(margin, trim_size, gap, x, y)
        points = _rounded_rect_points(origin, trim_size, corner_radius)
        polylines.append(_with_overcut(points, overcut))

    filepath = Path(filepath)
    if filepath.suffix.lower() != ".plt":
        filepath = filepath.with_name(filepath.name + ".plt")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    contents = _make_hpgl(polylines, papersize, mark_inset=mark_inset, speed=speed, force=force)
    if not filepath.exists() or filepath.read_text(encoding="utf-8") != contents:
        filepath.write_text(contents, encoding="utf-8")
    return filepath


def load_plt_payload(
    path: str | Path,
    force: int | None = None,
    speed: int | None = None,
) -> bytes:
    """Load a .plt file, optionally injecting force/speed, and ensure it ends cleanly."""
    payload = Path(path).read_text(encoding="utf-8")
    if force is not None or speed is not None:
        lines = [line for line in payload.splitlines() if not re.fullmatch(r"(US|VS|!FS)\d+;", line)]
        injected = []
        if speed is not None:
            injected.extend([f"US{speed};", f"VS{speed};"])
        if force is not None:
            injected.append(f"!FS{force};")
        try:
            insert_at = lines.index("P0;") + 1
        except ValueError:
            insert_at = 1
        lines[insert_at:insert_at] = injected
        payload = "\n".join(lines) + "\n"

    if not payload.rstrip().endswith("@;"):
        payload = payload.rstrip() + "\n@;\n"
    return payload.encode("utf-8")


def _require_usb() -> tuple[Any, Any]:
    """Import pyusb lazily so the print path does not require it."""
    try:
        import usb.core
        import usb.util
    except ImportError as exc:
        raise RuntimeError(
            "pyusb is required for the send command. Install it with `uv pip install pyusb` (or reinstall mtg-proxies)."
        ) from exc
    return usb.core, usb.util


def find_devices() -> list[Any]:
    """Return connected Skycut/MakerCraft USB devices."""
    usb_core, _ = _require_usb()
    return list(usb_core.find(find_all=True, idVendor=SKYCUT_VID, idProduct=SKYCUT_PID))


def device_label(device: Any) -> str:  # ruff: ignore[any-type]
    """Return a human-readable label for a USB device."""
    _, usb_util = _require_usb()
    try:
        product = usb_util.get_string(device, device.iProduct) or "Skycut"
        serial = usb_util.get_string(device, device.iSerialNumber) or ""
        return f"{product} {serial}".strip()
    except Exception:
        return f"{device.idVendor:04x}:{device.idProduct:04x}"


def list_devices() -> list[Any]:
    """Print connected cutters and return them."""
    devices = find_devices()
    if not devices:
        print("No Skycut/MakerCraft found (USB 0483:5750).")
        return []
    for device in devices:
        print(f"{device_label(device)}  bus={device.bus} address={device.address}")
    return devices


def send_plt(
    path: str | Path,
    *,
    yes: bool = False,
    force: int | None = None,
    speed: int | None = None,
    dry_run: bool = False,
    device: str | None = None,
) -> None:
    """Send a .plt file to a Skycut/MakerCraft over USB.

    Args:
        path: Path to the .plt file.
        yes: Do not ask for confirmation.
        force: Optional pressure override (1-160).
        speed: Optional speed override (1-12).
        dry_run: Print the payload instead of touching the cutter.
        device: Optional serial number or product-string substring.
    """
    payload = load_plt_payload(path, force=force, speed=speed)

    if dry_run:
        print(payload.decode("utf-8"))
        return

    usb_core, usb_util = _require_usb()
    devices = find_devices()
    if device:
        devices = [candidate for candidate in devices if device.lower() in device_label(candidate).lower()]
    if not devices:
        available = ", ".join(device_label(candidate) for candidate in find_devices()) or "none"
        raise RuntimeError(
            f"No matching Skycut/MakerCraft found (USB {SKYCUT_VID:04x}:{SKYCUT_PID:04x}). Available: {available}"
        )

    selected = devices[0]
    print(f"Device: {device_label(selected)}")

    if not yes:
        answer = input(f"Send {Path(path).name} ({len(payload)} bytes) to the cutter? [y/N] ")
        if answer.strip().lower() not in {"y", "yes"}:
            print("Cancelled.")
            return

    try:
        if selected.is_kernel_driver_active(0):
            selected.detach_kernel_driver(0)
        usb_util.claim_interface(selected, 0)
    except usb_core.USBError as exc:
        raise RuntimeError(
            "Could not claim the cutter's USB interface. If usblp has grabbed it, "
            "run `sudo modprobe -r usblp` and try again."
        ) from exc

    try:
        interface = selected.get_active_configuration()[0, 0]
        endpoint = usb_util.find_descriptor(
            interface,
            custom_match=lambda candidate: (
                usb_util.endpoint_direction(candidate.bEndpointAddress) == usb_util.ENDPOINT_OUT
            ),
        )
        if endpoint is None:
            raise RuntimeError("Cutter has no bulk OUT endpoint")
        sent = 0
        for start in range(0, len(payload), 4096):
            sent += selected.write(endpoint, payload[start : start + 4096], timeout=15000)
        print(f"Sent {sent} bytes to {Path(path).name}")
    except usb_core.USBError as exc:
        raise RuntimeError(f"USB transfer failed: {exc}") from exc
    finally:
        usb_util.release_interface(selected, 0)
        usb_util.dispose_resources(selected)

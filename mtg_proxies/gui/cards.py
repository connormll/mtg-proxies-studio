"""Conversions from Scryfall card objects to GUI response models."""

from __future__ import annotations

from typing import Any

import mtg_proxies.scryfall as scryfall
from mtg_proxies.decklists import Card
from mtg_proxies.decklists.sanitizing import get_print_warnings
from mtg_proxies.gui.models import CardSummary, CardWarning, PrintingOption


def _face_image_uris(face: dict[str, Any]) -> dict[str, str]:
    """Return the image URI mapping of one card face."""
    image_uris = face.get("image_uris")
    return image_uris if isinstance(image_uris, dict) else {}


def card_faces(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the faces of a card, or an empty list for unknown layouts."""
    try:
        return scryfall.get_faces(card)
    except ValueError:
        return []


def card_images(card: dict[str, Any]) -> tuple[str | None, str | None, list[str]]:
    """Return front image, back image, and face names for a card."""
    faces = card_faces(card)
    image_url = None
    image_back_url = None
    if faces:
        image_url = _face_image_uris(faces[0]).get("normal")
        if len(faces) > 1:
            image_back_url = _face_image_uris(faces[1]).get("normal")
    return image_url, image_back_url, [face.get("name", card.get("name", "")) for face in faces]


def card_warnings(card: dict[str, Any]) -> tuple[list[CardWarning], bool, bool]:
    """Convert Scryfall print warnings to card warning models and flags."""
    warnings: list[CardWarning] = []
    low_res = False
    non_english = False
    for message in get_print_warnings(card):
        code = "printing"
        if "low resolution" in message:
            code = "low_res"
            low_res = True
        elif "non-english" in message:
            code = "non_english"
            non_english = True
        elif "promo" in message:
            code = "promo"
        elif "border" in message:
            code = "border"
        warnings.append(CardWarning(code=code, message=message.capitalize()))
    return warnings, low_res, non_english


def card_key(card: dict[str, Any]) -> str:
    """Return a stable key that merges different printings of one card."""
    oracle_id = card.get("oracle_id")
    if oracle_id:
        return f"oracle:{oracle_id}"
    faces = card_faces(card)
    for face in faces:
        oracle_id = face.get("oracle_id")
        if oracle_id:
            return f"oracle:{oracle_id}"
    return f"card:{card['id']}"


def card_summary(
    card: dict[str, Any],
    *,
    count: int,
    source_lines: list[int] | None = None,
) -> CardSummary:
    """Build the GUI representation of a selected card printing."""
    image_url, image_back_url, face_names = card_images(card)
    warnings, low_res, non_english = card_warnings(card)
    entry = Card(count, card)
    return CardSummary(
        key=card_key(card),
        printing_id=card["id"],
        name=card.get("name", "Unknown card"),
        set_code=str(card.get("set", "")).upper(),
        set_name=card.get("set_name") or str(card.get("set", "")).upper(),
        collector_number=str(card.get("collector_number", "")),
        released_at=card.get("released_at"),
        count=count,
        image_url=image_url,
        image_back_url=image_back_url,
        face_names=face_names,
        is_basic_land=entry.is_basic_land,
        is_token=entry.is_token,
        warnings=warnings,
        low_res=low_res,
        non_english=non_english,
        source_lines=source_lines or [],
    )


def printing_option(card: dict[str, Any], *, recommended_id: str) -> PrintingOption:
    """Build a selectable printing option from a Scryfall card."""
    image_url, image_back_url, face_names = card_images(card)
    warnings, low_res, non_english = card_warnings(card)
    return PrintingOption(
        id=card["id"],
        name=card.get("name", "Unknown card"),
        set_code=str(card.get("set", "")).upper(),
        set_name=card.get("set_name") or str(card.get("set", "")).upper(),
        collector_number=str(card.get("collector_number", "")),
        released_at=card.get("released_at"),
        rarity=str(card.get("rarity", "")),
        border_color=str(card.get("border_color", "")),
        language=str(card.get("lang", "")),
        high_res=bool(card.get("highres_image")),
        digital=bool(card.get("digital")),
        is_recommended=card["id"] == recommended_id,
        image_url=image_url,
        image_back_url=image_back_url,
        face_names=face_names,
        warnings=warnings,
        low_res=low_res,
        non_english=non_english,
    )

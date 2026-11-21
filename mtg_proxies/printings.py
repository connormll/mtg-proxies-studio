"""Utilities for listing and selecting card printings."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import unquote

import mtg_proxies.scryfall as scryfall
from mtg_proxies.decklists import Card, Decklist
from mtg_proxies.decklists.sanitizing import validate_card_name
from mtg_proxies.format import format_print


@dataclass(frozen=True, slots=True)
class PrintingOverride:
    """A printing selected for a card."""

    card_name: str
    set_id: str
    collector_number: str

    def __str__(self) -> str:
        return f"{self.card_name}={self.set_id.upper()} {self.collector_number}"


_PRINTING_RE = re.compile(r"^\(?([A-Za-z0-9]+)\)?[\s/]+(\S+)$")
_SCRYFALL_URL_RE = re.compile(
    r"^https?://(?:www\.)?scryfall\.com/card/([^/\s]+)/([^/?#\s]+)(?:[/?#].*)?$",
    re.IGNORECASE,
)


def parse_printing_override(spec: str) -> PrintingOverride:
    """Parse a printing override.

    Accepted formats:
        Card Name=SET NUMBER
        Card Name=(SET) NUMBER
        Card Name=SET/NUMBER
        Card Name=https://scryfall.com/card/SET/NUMBER/...
    """
    card_name, separator, printing = spec.partition("=")
    card_name = card_name.strip()
    printing = printing.strip()
    if not separator or not card_name or not printing:
        raise ValueError(
            f"Invalid printing override {spec!r}. Use 'Card Name=SET NUMBER', e.g. 'Command Tower=C15 281'."
        )

    url_match = _SCRYFALL_URL_RE.fullmatch(printing)
    if url_match:
        return PrintingOverride(card_name, url_match.group(1).lower(), unquote(url_match.group(2)))

    printing_match = _PRINTING_RE.fullmatch(printing)
    if printing_match is None:
        raise ValueError(
            f"Invalid printing {printing!r} in {spec!r}. Use 'Card Name=SET NUMBER', e.g. 'Command Tower=C15 281'."
        )
    return PrintingOverride(card_name, printing_match.group(1).lower(), printing_match.group(2))


def resolve_printing_override(override: PrintingOverride) -> dict:
    """Resolve a printing override to a Scryfall card.

    Raises:
        ValueError: If the card or printing cannot be found.
    """
    card_name, _ = validate_card_name(override.card_name)
    if card_name is None:
        raise ValueError(
            f"Unknown card {override.card_name!r}. "
            f"Check the spelling or run `mtg-proxies printings {override.card_name!r}`."
        )

    card = scryfall.get_card(card_name, override.set_id, override.collector_number)
    if card is None:
        raise ValueError(
            f"Unable to find printing {format_print(card_name, override.set_id, override.collector_number)!r}. "
            f"Run `mtg-proxies printings {card_name!r}` to list available printings."
        )
    return card


def _oracle_ids(card: dict) -> set[str]:
    """Return all oracle ids on a card, including both faces of a reversible card."""
    if "oracle_id" in card:
        return {card["oracle_id"]}
    return {face["oracle_id"] for face in card.get("card_faces", []) if "oracle_id" in face}


def _name_key(card: dict) -> str:
    """Return the normalized full name of a card."""
    return scryfall.canonic_card_name(card["name"])


def apply_printing_overrides(
    decklist: Decklist,
    overrides: Sequence[PrintingOverride],
) -> tuple[Decklist, list[PrintingOverride]]:
    """Return a copy of a decklist with the requested printings applied.

    Cards are matched by oracle id, so every printing of the same card is
    replaced. Overrides that do not match any card are returned separately.

    Args:
        decklist: Decklist to update.
        overrides: Printings to apply.

    Returns:
        The updated decklist and the overrides that matched no card.
    """
    by_oracle_id: dict[str, tuple[dict, list[int]]] = {}
    by_name: dict[str, tuple[dict, list[int]]] = {}
    for index, override in enumerate(overrides):
        card = resolve_printing_override(override)
        for oracle_id in _oracle_ids(card):
            indices = by_oracle_id.get(oracle_id, (card, []))[1]
            by_oracle_id[oracle_id] = (card, [*indices, index])
        name = _name_key(card)
        indices = by_name.get(name, (card, []))[1]
        by_name[name] = (card, [*indices, index])

    matched: set[int] = set()
    entries = []
    for entry in decklist.entries:
        if isinstance(entry, Card):
            replacement = next(
                (by_oracle_id[oracle_id] for oracle_id in _oracle_ids(entry.card) if oracle_id in by_oracle_id),
                None,
            )
            if replacement is None:
                replacement = by_name.get(_name_key(entry.card))
            if replacement is not None:
                card, indices = replacement
                entries.append(Card(entry.count, card))
                matched.update(indices)
                continue
        entries.append(entry)

    unmatched = [override for index, override in enumerate(overrides) if index not in matched]
    return Decklist(entries=entries, name=decklist.name), unmatched

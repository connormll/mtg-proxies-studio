"""Printing selection for the local web interface."""

from __future__ import annotations

import mtg_proxies.scryfall as scryfall
from mtg_proxies.gui.cards import printing_option
from mtg_proxies.gui.models import PrintingOption, PrintingScope, PrintingsResult


def list_printings(printing_id: str, scope: PrintingScope) -> PrintingsResult:
    """Return artworks or every printing for the card behind ``printing_id``."""
    card = scryfall.card_by_id().get(printing_id)
    if card is None:
        raise LookupError("That card is no longer available in the local Scryfall database.")

    printings = scryfall.get_printings(card.get("name", ""))
    if not printings:
        printings = [card]

    recommended = printings[0]
    selected = printings if scope == "all" else scryfall.unique_artworks(printings)

    selected_ids = {candidate["id"] for candidate in selected}
    if card["id"] not in selected_ids:
        selected = [card, *selected]
    elif scope == "artworks":
        # Show the selected printing instead of a different print of the same artwork.
        selected = [card, *(candidate for candidate in selected if candidate["id"] != card["id"])]

    options: list[PrintingOption] = [
        printing_option(candidate, recommended_id=recommended["id"]) for candidate in selected
    ]
    return PrintingsResult(
        card_name=card.get("name", "Unknown card"),
        recommended_id=recommended["id"],
        options=options,
        scope=scope,
    )

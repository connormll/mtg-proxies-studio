from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from tqdm import tqdm

import mtg_proxies.scryfall as scryfall
from mtg_proxies.decklists.decklist import Decklist


def fetch_scans_scryfall(
    decklist: Decklist,
    faces: Literal["all", "front", "back"] = "all",
    progress: Callable[[int, int, str], None] | None = None,
) -> list[str]:
    """Search Scryfall for scans of a decklist.

    Args:
        decklist: The decklist to fetch scans for
        faces: Which faces to fetch ("all", "front", "back")
        progress: Optional callback receiving completed scans, total scans, and a card name

    Returns:
        List: List of image files
    """
    if faces == "all":
        face_counts = [len(card.image_uris) for card in decklist.cards]
    elif faces == "front":
        face_counts = [min(1, len(card.image_uris)) for card in decklist.cards]
    else:
        face_counts = [max(0, len(card.image_uris) - 1) for card in decklist.cards]
    total = sum(count * face_count for count, face_count in zip((card.count for card in decklist.cards), face_counts))

    images: list[str] = []
    completed = 0
    for card in tqdm(decklist.cards, desc="Fetching artwork"):
        for index, image_uri in enumerate(card.image_uris):
            if faces != "all" and not ((faces == "front" and index == 0) or (faces == "back" and index > 0)):
                continue
            for _ in range(card.count):
                images.append(scryfall.get_image(image_uri["png"], silent=True))
                completed += 1
                if progress is not None:
                    progress(completed, total, card["name"])
    return images

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("Command Tower=C15 281", ("Command Tower", "c15", "281")),
        ("Command Tower=(C15) 281", ("Command Tower", "c15", "281")),
        ("Command Tower=C15/281", ("Command Tower", "c15", "281")),
        (
            "Command Tower=https://scryfall.com/card/c15/281/command-tower",
            ("Command Tower", "c15", "281"),
        ),
    ],
)
def test_parse_printing_override(spec: str, expected: tuple[str, str, str]) -> None:
    from mtg_proxies.printings import parse_printing_override

    override = parse_printing_override(spec)

    assert (override.card_name, override.set_id, override.collector_number) == expected


@pytest.mark.parametrize(
    "spec",
    [
        "Command Tower",
        "=C15 281",
        "Command Tower=",
        "Command Tower=nonsense",
    ],
)
def test_parse_printing_override_invalid(spec: str) -> None:
    from mtg_proxies.printings import parse_printing_override

    with pytest.raises(ValueError, match="printing"):
        parse_printing_override(spec)


def test_get_printings_is_recommended_first() -> None:
    from mtg_proxies import scryfall

    printings = scryfall.get_printings("Command Tower")

    assert len(printings) > 1
    assert printings[0] == scryfall.recommend_print(card_name="Command Tower")
    assert any(card["set"] == "c15" and card["collector_number"] == "281" for card in printings)


def test_get_printings_unknown_card() -> None:
    from mtg_proxies import scryfall

    assert scryfall.get_printings("Definitely Not A Card") == []


def test_get_printings_matches_front_face() -> None:
    from mtg_proxies import scryfall

    printings = scryfall.get_printings("Murderous Rider")

    assert len(printings) > 0
    assert all(card["name"] == "Murderous Rider // Swift End" for card in printings)


def test_unique_artworks() -> None:
    from mtg_proxies import scryfall

    printings = scryfall.get_printings("Command Tower")
    artworks = scryfall.unique_artworks(printings)

    assert 0 < len(artworks) < len(printings)
    artwork_ids = [scryfall.get_faces(card)[0]["illustration_id"] for card in artworks]
    assert len(artwork_ids) == len(set(artwork_ids))
    assert artworks[0] == printings[0]


def _fake_print(
    card_id: str,
    *,
    illustration_id: str,
    highres_image: bool,
    image_status: str,
    lang: str = "en",
    released_at: str = "2020-01-01",
) -> dict:
    return {
        "id": card_id,
        "oracle_id": "test-oracle-id",
        "name": "Test Card",
        "set": "tst",
        "collector_number": "1",
        "released_at": released_at,
        "layout": "normal",
        "lang": lang,
        "frame": "2015",
        "border_color": "black",
        "digital": False,
        "nonfoil": True,
        "highres_image": highres_image,
        "image_status": image_status,
        "illustration_id": illustration_id,
        "image_uris": {"normal": f"https://example.test/{card_id}.jpg"},
    }


def test_unique_artworks_prefers_high_res_duplicate_over_english() -> None:
    """A low-res English print must not beat a high-res print of the same image."""
    from mtg_proxies import scryfall

    low_res = _fake_print(
        "low-res",
        illustration_id="same-art",
        highres_image=False,
        image_status="lowres",
        lang="en",
        released_at="2020-01-01",
    )
    high_res = _fake_print(
        "high-res",
        illustration_id="same-art",
        highres_image=True,
        image_status="highres_scan",
        lang="ja",
        released_at="2021-01-01",
    )

    assert scryfall.print_score(low_res) > scryfall.print_score(high_res)
    assert scryfall.unique_artworks([low_res, high_res]) == [high_res]


def test_unique_artworks_uses_image_status_for_resolution() -> None:
    """A low-res scan is rejected even when the highres_image flag is set."""
    from mtg_proxies import scryfall

    flagged_low_res = _fake_print(
        "flagged-low-res",
        illustration_id="same-art",
        highres_image=True,
        image_status="lowres",
        released_at="2020-01-01",
    )
    high_res = _fake_print(
        "high-res",
        illustration_id="same-art",
        highres_image=True,
        image_status="highres_scan",
        released_at="2021-01-01",
    )

    assert scryfall.unique_artworks([flagged_low_res, high_res]) == [high_res]


def test_recommend_print_prefers_high_res_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    from mtg_proxies import scryfall
    from mtg_proxies.scryfall import scryfall as scryfall_module

    low_res = _fake_print(
        "low-res",
        illustration_id="same-art",
        highres_image=False,
        image_status="lowres",
        lang="en",
    )
    high_res = _fake_print(
        "high-res",
        illustration_id="same-art",
        highres_image=True,
        image_status="highres_scan",
        lang="ja",
    )
    monkeypatch.setattr(scryfall_module, "cards_by_oracle_id", lambda: {"test-oracle-id": [low_res, high_res]})

    assert scryfall.recommend_print(low_res) == high_res
    assert scryfall.recommend_print(high_res) == high_res


def test_get_printings_lists_high_res_duplicate_first(monkeypatch: pytest.MonkeyPatch) -> None:
    from mtg_proxies.scryfall import scryfall as scryfall_module

    low_res = _fake_print(
        "low-res",
        illustration_id="same-art",
        highres_image=False,
        image_status="lowres",
        lang="en",
    )
    high_res = _fake_print(
        "high-res",
        illustration_id="same-art",
        highres_image=True,
        image_status="highres_scan",
        lang="ja",
    )
    monkeypatch.setattr(scryfall_module, "get_cards", lambda **_kwargs: [low_res, high_res])

    printings = scryfall_module.get_printings("Test Card")

    assert printings[0] == high_res
    assert low_res in printings


def test_low_res_warning_uses_image_status() -> None:
    from mtg_proxies.decklists.sanitizing import get_print_warnings

    flagged_low_res = _fake_print(
        "flagged-low-res",
        illustration_id="same-art",
        highres_image=True,
        image_status="lowres",
    )

    assert "low resolution scan" in get_print_warnings(flagged_low_res)


def test_apply_printing_overrides() -> None:
    from mtg_proxies import scryfall
    from mtg_proxies.decklists import Decklist
    from mtg_proxies.printings import apply_printing_overrides, parse_printing_override

    old_tower = scryfall.get_card("Command Tower", "CMD", "269")
    new_tower = scryfall.get_card("Command Tower", "C15", "281")
    sol_ring = scryfall.get_card("Sol Ring", "C15", "268")

    decklist = Decklist()
    decklist.append_comment("Deck")
    decklist.append_card(2, old_tower)
    decklist.append_card(1, sol_ring)

    updated, unmatched = apply_printing_overrides(decklist, [parse_printing_override("Command Tower=C15 281")])

    assert updated.entries[0].text == "Deck"
    assert updated.cards[0].count == 2
    assert updated.cards[0]["id"] == new_tower["id"]
    assert updated.cards[1]["id"] == sol_ring["id"]
    assert unmatched == []
    # The original decklist is not modified
    assert decklist.cards[0]["id"] == old_tower["id"]


def test_apply_printing_overrides_reports_unmatched() -> None:
    from mtg_proxies import scryfall
    from mtg_proxies.decklists import Decklist
    from mtg_proxies.printings import apply_printing_overrides, parse_printing_override

    decklist = Decklist()
    decklist.append_card(1, scryfall.get_card("Sol Ring", "C15", "268"))

    override = parse_printing_override("Command Tower=C15 281")
    updated, unmatched = apply_printing_overrides(decklist, [override])

    assert updated.cards[0]["name"] == "Sol Ring"
    assert unmatched == [override]


def test_apply_printing_overrides_last_duplicate_wins() -> None:
    """Repeated overrides for one card should all count as matched."""
    from mtg_proxies import scryfall
    from mtg_proxies.decklists import Decklist
    from mtg_proxies.printings import apply_printing_overrides, parse_printing_override

    decklist = Decklist()
    decklist.append_card(1, scryfall.get_card("Command Tower", "CMD", "269"))
    expected = scryfall.get_card("Command Tower", "C15", "281")

    updated, unmatched = apply_printing_overrides(
        decklist,
        [
            parse_printing_override("Command Tower=CMD 269"),
            parse_printing_override("Command Tower=C15 281"),
        ],
    )

    assert updated.cards[0]["id"] == expected["id"]
    assert unmatched == []


def test_apply_printing_overrides_does_not_match_front_faces() -> None:
    """A double-faced card should not replace a token with the same front name."""
    from mtg_proxies import scryfall
    from mtg_proxies.decklists import Decklist
    from mtg_proxies.printings import apply_printing_overrides, parse_printing_override

    token = scryfall.get_card("Illusion", "TXLN", "2")
    card = scryfall.get_card("Illusion // Reality", "DMR", "213")

    decklist = Decklist()
    decklist.append_card(1, token)
    decklist.append_card(1, card)

    updated, unmatched = apply_printing_overrides(
        decklist,
        [parse_printing_override("Illusion // Reality=DMR 213")],
    )

    assert updated.cards[0]["id"] == token["id"]
    assert updated.cards[1]["id"] == card["id"]
    assert unmatched == []


def test_resolve_unknown_printing() -> None:
    from mtg_proxies.printings import parse_printing_override, resolve_printing_override

    override = parse_printing_override("Command Tower=ZZZ 999")

    with pytest.raises(ValueError, match="Unable to find printing"):
        resolve_printing_override(override)


def test_format_print_with_name_in_title() -> None:
    from mtg_proxies.format import format_print

    assert format_print("Name Dropper", "m21", "1") == "Name Dropper (M21) 1"

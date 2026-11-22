"""Kimi-powered replacement suggestions for the local web interface."""

from __future__ import annotations

import json
import os
import re
import uuid
from importlib.metadata import version
from typing import Any

import requests

import mtg_proxies.scryfall as scryfall
from mtg_proxies.gui import settings as gui_settings
from mtg_proxies.gui.cards import card_key, card_summary
from mtg_proxies.gui.models import ReplacementRequest, ReplacementResult, ReplacementSuggestion
from mtg_proxies.gui.progress import ProgressReporter

_API_KEY_ENV = "OPENCODE_API_KEY"
_API_KEY_ALIASES = ("OPENCODE_GO_API_KEY", "OPENCODE_ZEN_API_KEY")
_BASE_URL_ENV = "MTG_PROXIES_SUGGESTION_BASE_URL"
_MODEL_ENV = "MTG_PROXIES_SUGGESTION_MODEL"
_EFFORT_ENV = "MTG_PROXIES_SUGGESTION_EFFORT"
_DEFAULT_BASE_URL = "https://opencode.ai/inference/go/openai/v1"
_DEFAULT_MODEL = "kimi-k3.1-pro"
_DEFAULT_REASONING_EFFORT = "low"
_MAX_COMPLETION_TOKENS = 8192
_CONNECT_TIMEOUT = 15
# Kimi K3.1 Pro always reasons before answering, so allow several minutes for the reply.
_READ_TIMEOUT = 300
_SUGGESTION_COUNT = 5
_COLOR_ORDER = "WUBRG"
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _environment_api_key() -> str | None:
    """Return an API key from the process environment, if any."""
    for name in (_API_KEY_ENV, *_API_KEY_ALIASES):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def opencode_api_key() -> str | None:
    """Return the configured OpenCode Go API key, if any."""
    return _environment_api_key() or gui_settings.saved_api_key()


def opencode_api_key_source() -> str | None:
    """Return where the API key comes from, or None when it is not configured."""
    if _environment_api_key():
        return "environment"
    if gui_settings.saved_api_key():
        return "saved"
    return None


def save_opencode_api_key(api_key: str) -> None:
    """Save an OpenCode Go API key for later launches."""
    value = api_key.strip()
    if not value:
        raise ValueError("Enter an OpenCode Go API key first.")
    gui_settings.save_api_key(value)


def clear_opencode_api_key() -> None:
    """Remove the locally saved OpenCode Go API key."""
    gui_settings.save_api_key(None)


def model_name() -> str:
    """Return the Kimi model used for replacement suggestions."""
    model = os.environ.get(_MODEL_ENV, "").strip() or _DEFAULT_MODEL
    return model.removeprefix("opencode-go/")


def reasoning_effort() -> str:
    """Return the Kimi reasoning effort, defaulting to the fastest useful level."""
    value = os.environ.get(_EFFORT_ENV, "").strip().lower()
    return value if value in {"low", "high", "max"} else _DEFAULT_REASONING_EFFORT


def _base_url() -> str:
    """Return the OpenCode Go Chat Completions base URL."""
    return (os.environ.get(_BASE_URL_ENV, "").strip() or _DEFAULT_BASE_URL).rstrip("/")


def _card_faces(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Return card faces, or a single face for normal cards."""
    faces = card.get("card_faces")
    if isinstance(faces, list) and faces:
        return [face for face in faces if isinstance(face, dict)]
    return [card]


def _append_face(lines: list[str], face: dict[str, Any], *, indent: str) -> None:
    """Append the rules fields of one card face to a prompt."""
    fields = (
        ("mana_cost", "Mana cost"),
        ("type_line", "Type"),
        ("oracle_text", "Rules text"),
    )
    for key, label in fields:
        value = face.get(key)
        if isinstance(value, str) and value.strip():
            text = value.strip().replace("\n", f"\n{indent}")
            lines.append(f"{indent}{label}: {text}")

    stats = " / ".join(str(face[key]) for key in ("power", "toughness") if face.get(key) is not None)
    if stats:
        lines.append(f"{indent}Power/toughness: {stats}")
    if face.get("loyalty") is not None:
        lines.append(f"{indent}Loyalty: {face['loyalty']}")


def _describe_card(card: dict[str, Any]) -> str:
    """Render the Scryfall fields Kimi needs to judge a card's effect."""
    faces = _card_faces(card)
    lines = [f"Name: {card.get('name', 'Unknown card')}"]
    if len(faces) == 1:
        _append_face(lines, faces[0], indent="")
    else:
        for index, face in enumerate(faces, start=1):
            lines.append(f"Face {index}: {face.get('name', '')}")
            _append_face(lines, face, indent="  ")

    colors = "".join(str(color) for color in card.get("color_identity") or [])
    lines.append(f"Color identity: {colors or 'colorless'}")

    legalities = card.get("legalities")
    if isinstance(legalities, dict) and isinstance(legalities.get("commander"), str):
        lines.append(f"Commander legality: {legalities['commander']}")

    keywords = card.get("keywords")
    if isinstance(keywords, list) and keywords:
        lines.append(f"Keywords: {', '.join(str(keyword) for keyword in keywords)}")
    return "\n".join(lines)


def _deck_context(
    deck_entries: list[tuple[int, dict[str, Any]]],
    target_key: str,
) -> tuple[str, set[str]]:
    """Return a compact deck list and the combined color identity for the prompt."""
    colors: set[str] = set()
    lines: list[str] = []
    for count, card in deck_entries:
        colors.update(str(color) for color in card.get("color_identity") or [])
        if card_key(card) == target_key:
            continue
        lines.append(f"{count} {card.get('name', 'Unknown card')}")

    if not lines:
        lines.append("(no other cards)")
    return "\n".join(lines), colors


def _build_prompt(target: dict[str, Any], deck_entries: list[tuple[int, dict[str, Any]]]) -> str:
    """Build the replacement request sent to Kimi."""
    target_key = card_key(target)
    deck_text, colors = _deck_context(deck_entries, target_key)
    colors.update(str(color) for color in target.get("color_identity") or [])
    color_text = "".join(color for color in _COLOR_ORDER if color in colors) or "colorless"

    return (
        "You are an expert Magic: The Gathering deck builder helping a Commander player "
        "replace one card.\n\n"
        "Find the cards that most accurately achieve the same effect as the card being replaced.\n\n"
        "Requirements:\n"
        "- Judge the card by what it actually does, not by its name.\n"
        "- Use the deck list to understand the card's role in this deck, then preserve that role.\n"
        "- Stay within the deck's color identity and match the mana value and timing as closely as possible.\n"
        "- Prefer cards that are legal in Commander and available in paper Magic.\n"
        "- Do not suggest the card being replaced or any card already in the deck.\n"
        f"- Suggest exactly {_SUGGESTION_COUNT} cards with exact English names, best first.\n"
        "- For each card, explain in one or two sentences how it produces the same effect and note "
        "the closest tradeoff.\n"
        "- Return only JSON, with no markdown fences or commentary, in this exact shape:\n"
        '{"suggestions":[{"name":"Exact English card name","reason":"Why it fills the same role."}]}\n\n'
        "CARD TO REPLACE\n"
        f"{_describe_card(target)}\n\n"
        "DECK CONTEXT\n"
        f"Deck color identity: {color_text}\n"
        "Other cards in the deck:\n"
        f"{deck_text}\n"
    )


def _error_detail(response: requests.Response) -> str:
    """Return a short server error message without leaking credentials."""
    try:
        body = response.json()
    except ValueError:
        return ""
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        message = error["message"].strip()[:200]
        return f": {message}" if message else ""
    return ""


def _raise_for_status(response: requests.Response) -> None:
    """Map OpenCode Go HTTP errors to actionable messages."""
    if response.status_code < 400:
        return
    if response.status_code in {401, 403}:
        raise RuntimeError(
            "OpenCode Go rejected the API key. Set OPENCODE_API_KEY to a valid key with an active "
            "Go subscription, then restart the GUI."
        )
    if response.status_code == 429:
        raise RuntimeError("OpenCode Go is rate-limiting requests. Wait a moment and try again.")
    raise RuntimeError(f"OpenCode Go returned HTTP {response.status_code}{_error_detail(response)}.")


def _response_content(body: dict[str, Any]) -> str:
    """Extract the assistant message from a Chat Completions response."""
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeError("Kimi returned an unexpected response.")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeError("Kimi returned an unexpected response.")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [part["text"] for part in content if isinstance(part, dict) and isinstance(part.get("text"), str)]
        if parts:
            return "".join(parts)
    raise RuntimeError("Kimi returned an unexpected response.")


def _json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating markdown fences and surrounding prose."""
    cleaned = _JSON_FENCE_RE.sub("", text.strip())
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match is None:
            raise RuntimeError("Kimi returned a response that was not valid JSON.") from None
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Kimi returned a response that was not valid JSON.") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Kimi returned a response that was not a JSON object.")
    return value


def _parse_suggestions(content: str) -> list[dict[str, str]]:
    """Extract the named suggestions from Kimi's message."""
    body = _json_object(content)
    raw_suggestions = body.get("suggestions")
    if not isinstance(raw_suggestions, list):
        raise RuntimeError("Kimi's response did not include a suggestion list.")

    parsed: list[dict[str, str]] = []
    for item in raw_suggestions[:_SUGGESTION_COUNT]:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        reason = item.get("reason")
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(reason, str) or not reason.strip():
            reason = "Kimi did not include a reason for this card."
        parsed.append({"name": name.strip()[:200], "reason": reason.strip()[:1000]})
    return parsed


def _request_suggestions(prompt: str) -> list[dict[str, str]]:
    """Ask Kimi for suggestions through the OpenCode Go inference API."""
    api_key = opencode_api_key()
    if api_key is None:
        raise RuntimeError(
            "Kimi replacement suggestions need an OpenCode Go API key. Set OPENCODE_API_KEY before "
            "starting the GUI, then try again."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": f"mtg-proxies/{version('mtg-proxies')}",
        "x-opencode-session": uuid.uuid4().hex,
    }
    payload = {
        "model": model_name(),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert Magic: The Gathering deck builder. Answer only with the requested JSON object."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "max_completion_tokens": _MAX_COMPLETION_TOKENS,
    }
    if model_name().startswith("kimi-k3.1"):
        payload["reasoning_effort"] = reasoning_effort()

    try:
        response = requests.post(
            f"{_base_url()}/chat/completions",
            headers=headers,
            json=payload,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
    except requests.ConnectTimeout as exc:
        raise RuntimeError(
            "Kimi could not be reached through OpenCode Go. Check your connection and try again."
        ) from exc
    except requests.Timeout as exc:
        raise RuntimeError(
            "Kimi took longer than five minutes to answer through OpenCode Go. Wait a moment and try again."
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(
            "Kimi could not be reached through OpenCode Go. Check your connection and try again."
        ) from exc

    _raise_for_status(response)
    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError("OpenCode Go returned a response that was not valid JSON.") from exc
    if not isinstance(body, dict):
        raise RuntimeError("OpenCode Go returned an unexpected response.")
    return _parse_suggestions(_response_content(body))


def _resolve_deck(
    request: ReplacementRequest,
    catalog: dict[str, dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    """Resolve the selected printings in the request to card objects."""
    entries: list[tuple[int, dict[str, Any]]] = []
    for selection in request.deck:
        card = catalog.get(selection.printing_id)
        if card is not None:
            entries.append((selection.count, card))
    return entries


def _resolve_suggestions(
    candidates: list[dict[str, str]],
    target: dict[str, Any],
    deck_entries: list[tuple[int, dict[str, Any]]],
) -> list[ReplacementSuggestion]:
    """Resolve names through Scryfall and remove duplicates or existing cards."""
    existing_keys = {card_key(target), *(card_key(card) for _, card in deck_entries)}
    deck_colors = {str(color) for color in target.get("color_identity") or []}
    for _, card in deck_entries:
        deck_colors.update(str(color) for color in card.get("color_identity") or [])

    suggestions: list[ReplacementSuggestion] = []
    seen_names: set[str] = set()
    seen_keys = set(existing_keys)
    for candidate in candidates:
        name = candidate["name"]
        canonical_name = scryfall.canonic_card_name(name)
        if canonical_name in seen_names:
            continue
        seen_names.add(canonical_name)

        printings = [
            card
            for card in scryfall.get_printings(name)
            if card.get("layout") not in {"token", "double_faced_token", "art_series", "emblem", "planar", "scheme"}
        ]
        if not printings:
            continue
        card = printings[0]
        key = card_key(card)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        card_colors = {str(color) for color in card.get("color_identity") or []}
        suggestions.append(
            ReplacementSuggestion(
                name=str(card.get("name", name)),
                reason=candidate["reason"],
                card=card_summary(card, count=1),
                off_color_identity=bool(deck_colors and card_colors - deck_colors),
            )
        )
        if len(suggestions) >= _SUGGESTION_COUNT:
            break
    return suggestions


def _deck_color_identity(cards: list[dict[str, Any]]) -> str:
    """Return the combined color identity of the deck in WUBRG order."""
    colors: set[str] = set()
    for card in cards:
        colors.update(str(color) for color in card.get("color_identity") or [])
    return "".join(color for color in _COLOR_ORDER if color in colors)


def suggest_replacements(
    request: ReplacementRequest,
    report: ProgressReporter,
) -> ReplacementResult:
    """Ask Kimi for cards that fill the same role as one deck card."""
    catalog = scryfall.card_by_id()
    target = catalog.get(request.printing_id)
    if target is None:
        raise RuntimeError("That card is no longer available in the local Scryfall database.")

    report("Reading the deck", 0, 3, "Resolving the cards around the replacement.")
    deck_entries = _resolve_deck(request, catalog)

    report("Asking Kimi", 1, 3, "Kimi is comparing effects and looking for the same role.")
    prompt = _build_prompt(target, deck_entries)
    candidates = _request_suggestions(prompt)

    report("Checking suggestions", 2, 3, "Validating Kimi's picks against the local Scryfall database.")
    suggestions = _resolve_suggestions(candidates, target, deck_entries)
    if not suggestions:
        raise RuntimeError("Kimi did not return a card that Scryfall could resolve. Try again.")

    report("Suggestions ready", 3, 3, f"Found {len(suggestions)} replacement candidates.")
    deck_cards = [card for _, card in deck_entries]
    return ReplacementResult(
        card_name=str(target.get("name", "Unknown card")),
        model=model_name(),
        deck_color_identity=_deck_color_identity([*deck_cards, target]),
        suggestions=suggestions,
    )

from __future__ import annotations

import gzip
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest


class FakeResponse:
    """Minimal stand-in for a streaming requests response."""

    def __init__(self, content: bytes, *, content_length: int | None = None) -> None:
        """Store the payload and optional advertised content length."""
        self.content = content
        self.headers = {} if content_length is None else {"Content-Length": str(content_length)}

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def raise_for_status(self) -> None:
        """Pretend the response status is fine."""

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        """Yield the payload in chunks like requests does."""
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]


def test_download_writes_file_atomically(tmp_path: Path) -> None:
    from mtg_proxies.scryfall import scryfall

    dst = tmp_path / "card.png"
    payload = b"complete image"
    response = FakeResponse(payload, content_length=len(payload))

    with patch.object(scryfall.requests, "get", return_value=response):
        scryfall.download("https://example.com/card.png", dst, silent=True)

    assert dst.read_bytes() == payload
    assert list(tmp_path.iterdir()) == [dst]  # No partial file left behind


def test_download_rejects_incomplete_response(tmp_path: Path) -> None:
    from mtg_proxies.scryfall import scryfall

    dst = tmp_path / "card.png"
    response = FakeResponse(b"truncated", content_length=100)

    with (
        patch.object(scryfall.requests, "get", return_value=response),
        pytest.raises(OSError, match="Incomplete download"),
    ):
        scryfall.download("https://example.com/card.png", dst, silent=True)

    assert not dst.exists()
    assert not list(tmp_path.glob("*.part"))


def test_get_image_replaces_truncated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from mtg_proxies.scryfall import scryfall

    monkeypatch.setattr(scryfall, "_cache_folder", tmp_path)
    url = "https://cards.scryfall.io/png/front/a/b/abc123.png?1"
    cached = tmp_path / "png_front_abc123.png"
    cached.write_bytes(b"partial download")
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    requests: list[tuple[str, Path]] = []

    def fake_download(url: str, dst: Path | str, *, silent: bool = False) -> None:
        _ = silent
        requests.append((url, Path(dst)))
        Path(dst).write_bytes(payload)

    monkeypatch.setattr(scryfall, "download", fake_download)

    path = scryfall.get_image(url, silent=True)

    assert Path(path) == cached
    assert cached.read_bytes() == payload
    assert requests == [(url, cached)]


def test_get_database_supports_scryfall_jsonl_bulk_data(tmp_path: Path) -> None:
    from mtg_proxies.scryfall import scryfall

    download_url = "https://data.scryfall.io/default-cards/default-cards.jsonl.gz"
    bulk_file = tmp_path / "default-cards.jsonl.gz"

    with gzip.open(bulk_file, "wt") as f:
        f.write('{"name": "Lightning Bolt"}\n')

    with (
        patch.object(
            scryfall, "depaginate", return_value=[{"type": "default_cards", "jsonl_download_uri": download_url}]
        ),
        patch.object(scryfall, "get_file", return_value=str(bulk_file)),
    ):
        scryfall._get_database.cache_clear()
        assert scryfall._get_database() == [{"name": "Lightning Bolt"}]
        scryfall._get_database.cache_clear()


@pytest.mark.parametrize(
    ("card_id", "n_faces"),
    [
        ("76ac5b70-47db-4cdb-91e7-e5c18c42e516", 1),
        ("c470539a-9cc7-4175-8f7c-c982b6072b6d", 2),  # Modal double-faced
        ("c1f53d7a-9dad-46e8-b686-cd1362867445", 2),  # Transforming double-faced
        ("6ee6cd34-c117-4d7e-97d1-8f8464bfaac8", 1),  # Flip
    ],
)
def test_get_faces(card_id: str, n_faces: int) -> None:
    from mtg_proxies import scryfall

    card = scryfall.card_by_id()[card_id]
    faces = scryfall.get_faces(card)

    assert type(faces) is list
    assert len(faces) == n_faces
    for face in faces:
        assert "illustration_id" in face


@pytest.mark.parametrize(
    ("name", "expected_id"),
    [
        ("Vedalken Aethermage", "496eb37d-5c8f-4dd7-a0a7-3ed1bd2210d6"),
        ("vedalken aethermage", "496eb37d-5c8f-4dd7-a0a7-3ed1bd2210d6"),
        ("vedalken Æthermage", "496eb37d-5c8f-4dd7-a0a7-3ed1bd2210d6"),
        ("vedalken æthermage", "496eb37d-5c8f-4dd7-a0a7-3ed1bd2210d6"),
    ],
)
def test_canonic_card_name(name: str, expected_id: str) -> None:
    from mtg_proxies import scryfall

    card = scryfall.get_card(name)

    assert card["id"] == expected_id

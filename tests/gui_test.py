from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

CardDict = dict[str, object]


def _card(
    card_id: str,
    name: str,
    *,
    oracle_id: str,
    set_code: str = "TST",
    collector_number: str = "1",
    type_line: str = "Artifact",
    layout: str = "normal",
    lang: str = "en",
    high_res: bool = True,
    digital: bool = False,
) -> CardDict:
    return {
        "id": card_id,
        "oracle_id": oracle_id,
        "name": name,
        "set": set_code,
        "set_name": f"{set_code.upper()} Test Set",
        "collector_number": collector_number,
        "released_at": "2024-01-01",
        "type_line": type_line,
        "layout": layout,
        "lang": lang,
        "highres_image": high_res,
        "digital": digital,
        "border_color": "black",
        "rarity": "rare",
        "image_uris": {"normal": f"https://example.test/{card_id}.jpg"},
    }


def _wait_for_job(client: TestClient, job_id: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"succeeded", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_import_merges_cards_and_reports_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    from mtg_proxies.decklists import ParseWarning
    from mtg_proxies.gui import importer

    sol_ring = _card("sol-id", "Sol Ring", oracle_id="sol-oracle", set_code="C21", collector_number="263")
    forest = _card(
        "forest-id",
        "Forest",
        oracle_id="forest-oracle",
        set_code="MIR",
        collector_number="303",
        type_line="Basic Land — Forest",
        lang="ja",
        high_res=False,
    )

    def validate_name(name: str) -> tuple[str | None, list[ParseWarning]]:
        if name == "Unknown Card":
            return None, [ParseWarning("ERROR", "Unable to find card 'Unknown Card'.")]
        return name, []

    def validate_print(name: str, _set: str | None, _number: str | None) -> tuple[dict, list[ParseWarning]]:
        if name == "Forest":
            return forest, [ParseWarning("WARNING", "Using a fallback Forest printing.")]
        return sol_ring, []

    monkeypatch.setattr(importer.scryfall, "get_cards", list)
    monkeypatch.setattr(importer, "validate_card_name", validate_name)
    monkeypatch.setattr(importer, "validate_print", validate_print)

    updates: list[tuple[str, int, int]] = []
    result = importer.import_decklist(
        "1 Sol Ring (C21) 263\n1 Sol Ring\n1 Forest (MIR) 303\n1 Unknown Card\n",
        lambda stage, completed, total, _detail: updates.append((stage, completed, total)),
    )

    assert [(card.name, card.count) for card in result.cards] == [("Sol Ring", 2), ("Forest", 1)]
    assert result.total_count == 3
    assert result.cards[0].source_lines == [1, 2]
    assert result.cards[1].low_res is True
    assert result.cards[1].non_english is True
    assert result.cards[1].is_basic_land is True
    missing = [issue for issue in result.issues if issue.line == 4]
    assert missing
    assert all(issue.severity == "warning" and issue.skipped for issue in missing)
    assert not any(issue.severity == "error" for issue in result.issues)
    assert any(issue.severity == "warning" and issue.line == 3 and not issue.skipped for issue in result.issues)
    assert any(stage == "Reading decklist" and total == 4 for stage, _, total in updates)


def test_generate_skips_printings_missing_from_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from mtg_proxies.gui import generation
    from mtg_proxies.gui.models import GenerateOptions, GenerateRequest, SelectedCard

    sol_ring = _card("sol-id", "Sol Ring", oracle_id="sol-oracle")
    monkeypatch.setattr(generation.scryfall, "card_by_id", lambda: {"sol-id": sol_ring})
    monkeypatch.setattr(generation, "fetch_scans_scryfall", lambda *_args, **_kwargs: ["front.png"])
    monkeypatch.setattr(
        generation,
        "print_cards_fpdf",
        lambda _images, path, **_kwargs: Path(path).write_bytes(b"%PDF-1.4 test"),
    )

    request = GenerateRequest(
        cards=[
            SelectedCard(printing_id="sol-id", count=1),
            SelectedCard(printing_id="gone-id", count=2),
        ],
        options=GenerateOptions(mode="standard", paper_width=8.5, paper_height=11),
    )

    result = generation.generate_files(request, tmp_path, lambda *_args: None)

    assert result.card_count == 1
    assert result.filters == ["Skipped 2 copies no longer available in the card database."]
    assert (tmp_path / "proxies.pdf").is_file()


def test_generate_standard_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from mtg_proxies.gui import generation
    from mtg_proxies.gui.models import GenerateOptions, GenerateRequest, SelectedCard

    sol_ring = _card("sol-id", "Sol Ring", oracle_id="sol-oracle")
    forest = _card(
        "forest-id",
        "Forest",
        oracle_id="forest-oracle",
        type_line="Basic Land — Forest",
    )
    token = _card("token-id", "Treasure", oracle_id="token-oracle", type_line="Token Artifact", layout="token")
    cards = {"sol-id": sol_ring, "forest-id": forest, "token-id": token}

    def fake_scans(_decklist: object, faces: str, progress: Callable[[int, int, str], None]) -> list[str]:
        assert faces == "all"
        progress(1, 1, "Sol Ring")
        return ["front.png"]

    def fake_pdf(images: object, path: Path, **_kwargs: object) -> None:
        assert len(images) == 1  # type: ignore[arg-type]
        assert list(images) == ["front.png"]  # type: ignore[arg-type]
        Path(path).write_bytes(b"%PDF-1.4 test")

    def fake_cut_files(_num: int, path: Path, **_kwargs: object) -> list[Path]:
        path = Path(path)
        path.write_text("<svg/>", encoding="utf-8")
        return [path]

    monkeypatch.setattr(generation.scryfall, "card_by_id", lambda: cards)
    monkeypatch.setattr(generation, "fetch_scans_scryfall", fake_scans)
    monkeypatch.setattr(generation, "print_cards_fpdf", fake_pdf)
    monkeypatch.setattr(generation, "write_cut_files", fake_cut_files)

    request = GenerateRequest(
        cards=[
            SelectedCard(printing_id="sol-id", count=2),
            SelectedCard(printing_id="forest-id", count=1),
            SelectedCard(printing_id="token-id", count=1),
        ],
        options=GenerateOptions(
            mode="standard",
            paper_width=8.5,
            paper_height=11,
            no_basic_lands=True,
            no_tokens=True,
            cut_file=True,
        ),
    )

    result = generation.generate_files(request, tmp_path, lambda *_args: None)

    assert result.card_count == 2
    assert result.filters == ["Excluded 1 basic land.", "Excluded 1 token."]
    assert [artifact.kind for artifact in result.artifacts] == ["pdf", "svg"]
    assert (tmp_path / "proxies.pdf").is_file()
    assert (tmp_path / "proxies_cut.svg").is_file()


def test_generate_makercraft_template(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from mtg_proxies.gui import generation
    from mtg_proxies.gui.models import GenerateOptions, GenerateRequest, SelectedCard

    sol_ring = _card("sol-id", "Sol Ring", oracle_id="sol-oracle")

    def fake_pdf(_images: object, path: Path, **rest: object) -> None:
        assert rest["mark_inset"] == pytest.approx(10.0)
        assert rest["max_cards"].tolist() == [3, 2]  # type: ignore[attr-defined]
        Path(path).write_bytes(b"%PDF-1.4 test")

    def fake_plt(path: Path, **kwargs: object) -> Path:
        assert kwargs["mark_inset"] == pytest.approx(10.0)
        assert kwargs["max_cards"].tolist() == [3, 2]  # type: ignore[attr-defined]
        Path(path).write_text("IN;", encoding="utf-8")
        return Path(path)

    monkeypatch.setattr(generation.scryfall, "card_by_id", lambda: {"sol-id": sol_ring})
    monkeypatch.setattr(generation, "fetch_scans_scryfall", lambda *_args, **_kwargs: ["front.png"])
    monkeypatch.setattr(generation, "print_cards_fpdf", fake_pdf)
    monkeypatch.setattr(generation, "write_plt_file", fake_plt)

    request = GenerateRequest(
        cards=[SelectedCard(printing_id="sol-id", count=1)],
        options=GenerateOptions(
            mode="makercraft",
            paper_width=8.5,
            paper_height=11,
            gap=1.5,
            cut_file=False,
        ),
    )

    result = generation.generate_files(request, tmp_path, lambda *_args: None)

    assert [artifact.kind for artifact in result.artifacts] == ["pdf", "plt"]
    assert "6 cards/page (3x2)" in result.layout
    assert (tmp_path / "makercraft.plt").is_file()


def test_api_import_and_generate_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from mtg_proxies.gui import app as app_module
    from mtg_proxies.gui.jobs import JobManager
    from mtg_proxies.gui.models import GenerationResult, ImportResult

    def fake_import(_text: str, _report: object) -> ImportResult:
        return ImportResult(cards=[], issues=[], total_count=0)

    def fake_generate_valid(_request: object, output_dir: Path, _report: object) -> GenerationResult:
        from mtg_proxies.gui.models import Artifact

        pdf = output_dir / "proxies.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")
        plt = output_dir / "makercraft.plt"
        plt.write_text("IN;", encoding="utf-8")
        return GenerationResult(
            artifacts=[
                Artifact(
                    id="proxies.pdf",
                    filename="proxies.pdf",
                    label="Print sheet PDF",
                    kind="pdf",
                    media_type="application/pdf",
                    size=pdf.stat().st_size,
                ),
                Artifact(
                    id="makercraft.plt",
                    filename="makercraft.plt",
                    label="MakerCraft cut template",
                    kind="plt",
                    media_type="application/octet-stream",
                    size=plt.stat().st_size,
                ),
            ],
            layout="test layout",
            card_count=1,
            image_count=1,
            cards_per_page=1,
            pages=1,
            filters=[],
        )

    sent: dict[str, object] = {}

    def fake_send(path: Path, **kwargs: object) -> None:
        sent["path"] = path
        sent["kwargs"] = kwargs

    monkeypatch.setattr(app_module, "import_decklist", fake_import)
    monkeypatch.setattr(app_module, "generate_files", fake_generate_valid)
    monkeypatch.setattr(app_module, "send_plt", fake_send)

    manager = JobManager(tmp_path / "jobs", max_workers=1)
    app = app_module.create_app(manager)
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "MTG Proxy Studio" in page.text

        started = client.post("/api/import", json={"text": "1 Sol Ring"})
        assert started.status_code == 202
        import_job = _wait_for_job(client, started.json()["job_id"])
        assert import_job["status"] == "succeeded"

        payload = {
            "cards": [{"printing_id": "sol-id", "count": 1}],
            "options": {
                "mode": "makercraft",
                "paper_width": 8.5,
                "paper_height": 11,
                "scale": 1,
                "border_crop": 14,
                "gap": 0,
                "bleed": 0,
                "corner_radius": 2.5,
                "no_basic_lands": False,
                "no_tokens": False,
                "faces": "all",
                "background": None,
                "cropmarks": True,
                "cut_file": False,
                "mark_inset": 7,
                "mark_arm": 10,
                "mark_stroke": 1,
                "overcut": 1,
            },
        }
        generated = client.post("/api/generate", json=payload)
        assert generated.status_code == 202
        job_id = generated.json()["job_id"]
        generate_job = _wait_for_job(client, job_id)
        assert generate_job["status"] == "succeeded"

        pdf = client.get(f"/api/jobs/{job_id}/files/proxies.pdf")
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.headers["content-disposition"].startswith("inline")
        assert pdf.content.startswith(b"%PDF")

        downloaded = client.get(f"/api/jobs/{job_id}/files/proxies.pdf?download=true")
        assert downloaded.headers["content-disposition"].startswith("attachment")

        traversal = client.get(f"/api/jobs/{job_id}/files/..%2Fsecret")
        assert traversal.status_code == 404

        cutter = client.post(
            "/api/cutter/send",
            json={"job_id": job_id, "device": "SKY32 Vi test-serial"},
        )
        assert cutter.status_code == 200
        assert cutter.json()["ok"] is True
        assert sent["kwargs"] == {"yes": True, "device": "SKY32 Vi test-serial"}
        assert Path(sent["path"]).name == "makercraft.plt"  # type: ignore[arg-type]


def test_cutter_endpoints(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from mtg_proxies.gui import app as app_module
    from mtg_proxies.gui.jobs import JobManager

    class Device:
        bus = 1
        address = 2

    monkeypatch.setattr(app_module, "find_devices", lambda: [Device()])
    monkeypatch.setattr(app_module, "device_label", lambda _device: "SKY32 Vi test-serial")
    monkeypatch.setattr(app_module, "send_plt", lambda *_args, **_kwargs: None)

    manager = JobManager(tmp_path / "jobs", max_workers=1)
    app = app_module.create_app(manager)
    with TestClient(app) as client:
        devices = client.get("/api/cutter/devices")
        assert devices.status_code == 200
        assert devices.json()["devices"] == [{"label": "SKY32 Vi test-serial", "bus": 1, "address": 2}]

        missing = client.post("/api/cutter/send", json={"job_id": "missing"})
        assert missing.status_code == 404


def test_replacement_suggestions_resolve_and_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    from mtg_proxies.gui import replacements
    from mtg_proxies.gui.models import ReplacementRequest, SelectedCard

    sol_ring = _card("sol-id", "Sol Ring", oracle_id="sol-oracle", set_code="C21", collector_number="263")
    sol_ring.update({
        "mana_cost": "{1}",
        "oracle_text": "{T}: Add {C}{C}.",
        "color_identity": [],
    })
    signet = _card("signet-id", "Arcane Signet", oracle_id="signet-oracle")
    signet.update({"mana_cost": "{2}", "oracle_text": "{T}: Add one mana of any color.", "color_identity": []})
    mana_vault = _card("vault-id", "Mana Vault", oracle_id="vault-oracle")
    mana_vault.update({"mana_cost": "{1}", "oracle_text": "Mana Vault doesn't untap.", "color_identity": []})

    prompts: list[str] = []

    def fake_request(prompt: str) -> list[dict[str, str]]:
        prompts.append(prompt)
        return [
            {"name": "Mana Vault", "reason": "Ramps for two mana and untaps."},
            {"name": "Arcane Signet", "reason": "Already in the deck."},
            {"name": "Sol Ring", "reason": "The original card."},
            {"name": "Not A Real Card", "reason": "Should not resolve."},
        ]

    def fake_printings(name: str) -> list[CardDict]:
        return {
            "Mana Vault": [mana_vault],
            "Arcane Signet": [signet],
            "Sol Ring": [sol_ring],
        }.get(name, [])

    monkeypatch.setattr(replacements, "_request_suggestions", fake_request)
    monkeypatch.setattr(
        replacements.scryfall,
        "card_by_id",
        lambda: {"sol-id": sol_ring, "signet-id": signet},
    )
    monkeypatch.setattr(replacements.scryfall, "get_printings", fake_printings)

    request = ReplacementRequest(
        printing_id="sol-id",
        deck=[
            SelectedCard(printing_id="sol-id", count=1),
            SelectedCard(printing_id="signet-id", count=1),
        ],
    )
    result = replacements.suggest_replacements(request, lambda *_args: None)

    assert [suggestion.name for suggestion in result.suggestions] == ["Mana Vault"]
    assert result.suggestions[0].card.name == "Mana Vault"
    assert result.suggestions[0].card.count == 1
    assert result.suggestions[0].reason == "Ramps for two mana and untaps."
    assert result.card_name == "Sol Ring"
    assert result.model == "kimi-k3.1-pro"
    assert "Rules text: {T}: Add {C}{C}." in prompts[0]
    assert "1 Arcane Signet" in prompts[0]


def test_replacement_suggestions_parse_fenced_json() -> None:
    from mtg_proxies.gui import replacements

    content = '```json\n{"suggestions":[{"name":"Mana Vault","reason":"Same ramp."}]}\n```'

    assert replacements._parse_suggestions(content) == [{"name": "Mana Vault", "reason": "Same ramp."}]


def test_replacement_suggestions_require_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from mtg_proxies.gui import replacements

    monkeypatch.setenv("MTG_PROXIES_CONFIG_DIR", str(tmp_path))
    for name in ("OPENCODE_API_KEY", "OPENCODE_GO_API_KEY", "OPENCODE_ZEN_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="OPENCODE_API_KEY"):
        replacements._request_suggestions("prompt")


def test_replacement_suggestions_remember_saved_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import stat

    from mtg_proxies.gui import replacements, settings

    monkeypatch.setenv("MTG_PROXIES_CONFIG_DIR", str(tmp_path))
    for name in ("OPENCODE_API_KEY", "OPENCODE_GO_API_KEY", "OPENCODE_ZEN_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    assert replacements.opencode_api_key() is None
    replacements.save_opencode_api_key("  oc_sk_saved  ")

    assert replacements.opencode_api_key() == "oc_sk_saved"
    assert replacements.opencode_api_key_source() == "saved"
    config = settings.config_path()
    assert config.is_file()
    assert stat.S_IMODE(config.stat().st_mode) == 0o600

    replacements.clear_opencode_api_key()
    assert replacements.opencode_api_key() is None
    assert replacements.opencode_api_key_source() is None


def test_replacement_suggestions_environment_key_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from mtg_proxies.gui import replacements

    monkeypatch.setenv("MTG_PROXIES_CONFIG_DIR", str(tmp_path))
    replacements.save_opencode_api_key("oc_sk_saved")
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "oc_sk_environment")

    assert replacements.opencode_api_key() == "oc_sk_environment"
    assert replacements.opencode_api_key_source() == "environment"


def test_replacement_settings_api_saves_and_forgets_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    from mtg_proxies.gui import app as app_module

    monkeypatch.setenv("MTG_PROXIES_CONFIG_DIR", str(tmp_path))
    for name in ("OPENCODE_API_KEY", "OPENCODE_GO_API_KEY", "OPENCODE_ZEN_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    manager = app_module.JobManager(tmp_path / "jobs", max_workers=1)
    app = app_module.create_app(manager)
    with TestClient(app) as client:
        initial = client.get("/api/replace/settings")
        assert initial.status_code == 200
        assert initial.json() == {"configured": False, "source": None, "model": "kimi-k3.1-pro"}

        saved = client.put("/api/replace/settings", json={"api_key": "oc_sk_saved"})
        assert saved.status_code == 200
        assert saved.json() == {"configured": True, "source": "saved", "model": "kimi-k3.1-pro"}
        assert "oc_sk_saved" not in saved.text

        remembered = client.get("/api/replace/settings")
        assert remembered.json()["configured"] is True
        assert remembered.json()["source"] == "saved"

        cleared = client.delete("/api/replace/settings")
    assert cleared.status_code == 200
    assert cleared.json() == {"configured": False, "source": None, "model": "kimi-k3.1-pro"}


def test_replacement_suggestions_call_opencode_go(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from mtg_proxies.gui import replacements

    captured: dict[str, object] = {}

    class Response:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {
                "choices": [{"message": {"content": '{"suggestions":[{"name":"Mana Vault","reason":"Same role."}]}'}}]
            }

    def fake_post(url: str, **kwargs: object) -> Response:
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["body"] = kwargs["json"]
        captured["timeout"] = kwargs["timeout"]
        return Response()

    monkeypatch.setenv("MTG_PROXIES_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("OPENCODE_API_KEY", "oc_sk_test")
    monkeypatch.setattr(replacements.requests, "post", fake_post)

    result = replacements._request_suggestions("prompt")

    assert captured["url"] == "https://opencode.ai/inference/go/openai/v1/chat/completions"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer oc_sk_test"
    assert "x-opencode-session" in headers
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "kimi-k3.1-pro"
    assert body["response_format"] == {"type": "json_object"}
    assert body["reasoning_effort"] == "low"
    assert body["max_completion_tokens"] == 8192
    assert "temperature" not in body
    assert captured["timeout"] == (15, 300)
    assert result == [{"name": "Mana Vault", "reason": "Same role."}]


def test_replacement_suggestions_effort_and_model_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    from mtg_proxies.gui import replacements

    monkeypatch.delenv("MTG_PROXIES_SUGGESTION_EFFORT", raising=False)
    assert replacements.reasoning_effort() == "low"

    monkeypatch.setenv("MTG_PROXIES_SUGGESTION_EFFORT", "max")
    assert replacements.reasoning_effort() == "max"

    monkeypatch.setenv("MTG_PROXIES_SUGGESTION_EFFORT", "bogus")
    assert replacements.reasoning_effort() == "low"

    monkeypatch.setenv("MTG_PROXIES_SUGGESTION_MODEL", "opencode-go/kimi-k3.1-pro")
    assert replacements.model_name() == "kimi-k3.1-pro"


def test_replacement_suggestions_report_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from mtg_proxies.gui import replacements

    def fake_post(_url: str, **_kwargs: object) -> None:
        raise replacements.requests.Timeout("read timed out")

    monkeypatch.setenv("MTG_PROXIES_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("OPENCODE_API_KEY", "oc_sk_test")
    monkeypatch.setattr(replacements.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="took longer than five minutes"):
        replacements._request_suggestions("prompt")


def test_replacement_suggestions_report_connection_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from mtg_proxies.gui import replacements

    def fake_post(_url: str, **_kwargs: object) -> None:
        raise replacements.requests.ConnectionError("connection refused")

    monkeypatch.setenv("MTG_PROXIES_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("OPENCODE_API_KEY", "oc_sk_test")
    monkeypatch.setattr(replacements.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="could not be reached"):
        replacements._request_suggestions("prompt")


def test_api_replacement_suggestions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from mtg_proxies.gui import app as app_module
    from mtg_proxies.gui.cards import card_summary
    from mtg_proxies.gui.jobs import JobManager
    from mtg_proxies.gui.models import ReplacementResult, ReplacementSuggestion

    suggested = _card("vault-id", "Mana Vault", oracle_id="vault-oracle")
    result = ReplacementResult(
        card_name="Sol Ring",
        model="kimi-k3.1-pro",
        deck_color_identity="",
        suggestions=[
            ReplacementSuggestion(
                name="Mana Vault",
                reason="Same fast mana role.",
                card=card_summary(suggested, count=1),
            )
        ],
    )

    def fake_suggestions(_request: object, _report: object) -> ReplacementResult:
        return result

    monkeypatch.setattr(app_module, "suggest_replacements", fake_suggestions)
    monkeypatch.setattr(app_module, "opencode_api_key", lambda: "test-key")

    manager = JobManager(tmp_path / "jobs", max_workers=1)
    app = app_module.create_app(manager)
    with TestClient(app) as client:
        started = client.post(
            "/api/replace/suggestions",
            json={"printing_id": "sol-id", "deck": [{"printing_id": "sol-id", "count": 1}]},
        )
        assert started.status_code == 202
        job = _wait_for_job(client, started.json()["job_id"])

    assert job["status"] == "succeeded"
    assert job["kind"] == "suggest"
    assert job["result"]["suggestions"][0]["name"] == "Mana Vault"


def test_api_replacement_suggestions_require_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from mtg_proxies.gui import app as app_module
    from mtg_proxies.gui.jobs import JobManager

    monkeypatch.setattr(app_module, "opencode_api_key", lambda: None)

    manager = JobManager(tmp_path / "jobs", max_workers=1)
    app = app_module.create_app(manager)
    with TestClient(app) as client:
        response = client.post("/api/replace/suggestions", json={"printing_id": "sol-id", "deck": []})

    assert response.status_code == 503
    assert "OPENCODE_API_KEY" in response.json()["detail"]


def test_gui_cli_passes_port() -> None:
    from unittest.mock import patch

    from mtg_proxies.cli import main

    with (
        patch("sys.argv", ["mtg-proxies", "gui", "--port", "9123", "--no-browser"]),
        patch("mtg_proxies.gui.launcher.run_gui") as run_gui,
    ):
        main()

    run_gui.assert_called_once_with(port=9123, open_browser=False)


@pytest.mark.parametrize(
    ("mode", "expected_bleed", "expected_handcut", "expected_slider"),
    [
        ("handcut", 0.0, True, False),
        ("slider", 2.0, False, True),
    ],
)
def test_generate_manual_cut_modes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: str,
    expected_bleed: float,
    expected_handcut: bool,
    expected_slider: bool,
) -> None:
    from mtg_proxies.gui import generation
    from mtg_proxies.gui.models import GenerateOptions, GenerateRequest, SelectedCard

    sol_ring = _card("sol-id", "Sol Ring", oracle_id="sol-oracle")
    captured: dict[str, object] = {}

    def fake_pdf(_images: object, path: Path, **kwargs: object) -> None:
        captured.update(kwargs)
        Path(path).write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(generation.scryfall, "card_by_id", lambda: {"sol-id": sol_ring})
    monkeypatch.setattr(generation, "fetch_scans_scryfall", lambda *_args, **_kwargs: ["front.png"])
    monkeypatch.setattr(generation, "print_cards_fpdf", fake_pdf)

    request = GenerateRequest(
        cards=[SelectedCard(printing_id="sol-id", count=1)],
        options=GenerateOptions(
            mode=mode,  # type: ignore[arg-type]
            paper_width=8.5,
            paper_height=11,
            bleed=None,
            corner_radius=None,
            cut_file=False,
        ),
    )

    generation.generate_files(request, tmp_path, lambda *_args: None)

    assert captured["bleed"] == pytest.approx(expected_bleed)
    assert captured["corner_radius"] == pytest.approx(0.0)
    assert captured["border_crop"] == 14
    assert captured["handcut"] is expected_handcut
    assert captured["slider"] is expected_slider
    assert captured["cropmarks"] is False


def test_generate_rounded_cards_use_full_size(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The GUI should print rounded cards at full size too."""
    from mtg_proxies.gui import generation
    from mtg_proxies.gui.models import GenerateOptions, GenerateRequest, SelectedCard

    sol_ring = _card("sol-id", "Sol Ring", oracle_id="sol-oracle")
    captured: dict[str, object] = {}

    def fake_pdf(_images: object, path: Path, **kwargs: object) -> None:
        captured.update(kwargs)
        Path(path).write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(generation.scryfall, "card_by_id", lambda: {"sol-id": sol_ring})
    monkeypatch.setattr(generation, "fetch_scans_scryfall", lambda *_args, **_kwargs: ["front.png"])
    monkeypatch.setattr(generation, "print_cards_fpdf", fake_pdf)

    request = GenerateRequest(
        cards=[SelectedCard(printing_id="sol-id", count=1)],
        options=GenerateOptions(
            mode="standard",
            paper_width=8.5,
            paper_height=11,
            corner_radius=None,
            cut_file=False,
        ),
    )

    generation.generate_files(request, tmp_path, lambda *_args: None)

    assert captured["corner_radius"] == pytest.approx(2.5)
    assert captured["border_crop"] == 0

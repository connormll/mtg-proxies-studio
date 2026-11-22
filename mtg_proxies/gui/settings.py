"""Persistent local settings for the browser workspace."""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

_CONFIG_DIR_ENV = "MTG_PROXIES_CONFIG_DIR"
_CONFIG_FILE = "config.json"
_API_KEY_FIELD = "opencode_api_key"


def config_dir() -> Path:
    """Return the directory that stores local GUI settings."""
    override = os.environ.get(_CONFIG_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "").strip()
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "mtg-proxies"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "mtg-proxies"

    xdg_config = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    return base / "mtg-proxies"


def config_path() -> Path:
    """Return the path of the local GUI settings file."""
    return config_dir() / _CONFIG_FILE


def _read_config() -> dict[str, Any]:
    """Return the saved settings, or an empty mapping when none are readable."""
    try:
        raw = config_path().read_text(encoding="utf-8")
    except OSError:
        return {}

    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _write_config(config: dict[str, Any]) -> None:
    """Write the settings atomically, readable only by the current user."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
            handle.write("\n")
        Path(temporary_path).replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise

    with contextlib.suppress(OSError):
        path.chmod(0o600)


def saved_api_key() -> str | None:
    """Return the API key saved on this computer, if any."""
    value = _read_config().get(_API_KEY_FIELD)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def save_api_key(api_key: str | None) -> None:
    """Save an API key locally, or remove the saved key when given None."""
    config = _read_config()
    if api_key is None:
        config.pop(_API_KEY_FIELD, None)
    else:
        config[_API_KEY_FIELD] = api_key
    _write_config(config)

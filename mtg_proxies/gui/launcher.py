"""Launch the local mtg-proxies web interface."""

from __future__ import annotations

import threading
import webbrowser


def run_gui(*, port: int = 8000, open_browser: bool = True) -> None:
    """Serve the GUI on localhost and optionally open the default browser."""
    try:
        import fastapi  # ruff: ignore[unused-import]
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "The GUI requires optional web dependencies. Install them with "
            "`uv tool install 'mtg-proxies[web]'` or `uv sync --extra web`."
        ) from exc

    url = f"http://127.0.0.1:{port}/"
    if open_browser:
        timer = threading.Timer(1.0, webbrowser.open, args=(url,))
        timer.daemon = True
        timer.start()

    uvicorn.run(
        "mtg_proxies.gui.app:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )

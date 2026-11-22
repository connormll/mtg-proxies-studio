# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The primary users are the maintainer and their playgroup: casual Magic: The Gathering players preparing paper proxies at home for Commander and kitchen-table play. They want to test and play decks without buying every card, and they are comfortable working from a decklist but do not want to operate a print pipeline by hand.

## Product Purpose

mtg-proxies turns a decklist into a print-ready proxy sheet, locally. It covers the full path from decklist import through card and printing review to a PDF, SVG cut files, and cutter templates. Success means a sheet that prints at the correct physical size and cuts cleanly on the first attempt, with every card and layout choice checked before paper and ink are committed.

## Positioning

- **Local and uncompromised:** decklists and generated files stay on the user's machine. Full-resolution Scryfall scans print at exact physical scale, with no upload, account, or bandwidth cap.
- **One pipeline through cutting:** the PDF, SVG cut files, and MakerCraft template all come from the same verified layout, so the cut path matches the print without a second tool.
- **Per-card visual control:** every card and printing can be reviewed or overridden, with low-resolution, non-English, and substitution warnings instead of blind automation.
- **Forgiving decklist input:** text, Arena, ManaStack, and Archidekt sources work, including mixed formats, with clear per-line feedback.

## Operating Context

- Sessions happen at a home desk with a consumer printer, paper, and a cutting method: a Skycut/MakerCraft C10 over USB, a guillotine or rotary trimmer, or a sliding-blade trimmer.
- The physical workflow assumes printing at 100% / Actual size and slipping finished proxies into sleeves in front of real cards.
- The browser workspace defaults to US Letter; the command line defaults to A4.
- Decklists are pasted, uploaded as `.txt`, or referenced by ManaStack/Archidekt id. Scryfall supplies card data, printings, and artwork. The optional Kimi replacement feature sends the selected card and decklist card names to OpenCode Go, but only when the user explicitly asks for suggestions.
- The browser workspace is the primary experience; the CLI remains the scripting and power-user path.

## Capabilities and Constraints

- CLI commands: `print`, `convert`, `printings`, `tokens`, `send`, `deck_value`, and `gui`.
- Print options include paper size, scale, border crop, gap, bleed, corner radius, faces, background, crop marks, basic-land and token exclusion, and per-card printing overrides.
- Output modes: standard PDF with optional SVG cut files, MakerCraft registration marks plus a reusable HPGL `.plt` template and USB sending, handcut sheets for trimmers, and slider-trimmer sheets with full-page cut lines along every card edge.
- The GUI is a React + TypeScript frontend built into `mtg_proxies/gui/static/` and served by a FastAPI backend on `127.0.0.1` only. It requires the optional `web` extra; Node is needed only to rebuild the frontend.
- Kimi replacement suggestions use the OpenCode Go Chat Completions API and require an API key with an active Go subscription. The key can be pasted into the replacement dialog once and saved owner-only in the local settings folder, or supplied through `OPENCODE_API_KEY` (which takes precedence). The default model is `kimi-k3.1-pro` with low reasoning effort for responsive suggestions; `MTG_PROXIES_SUGGESTION_EFFORT` can raise it. Suggestions are validated against Scryfall, filtered for duplicates and existing deck cards, and flagged when they fall outside the deck's color identity.
- There are no accounts, no database, no telemetry, and no external data store. Generated files are not persisted by the server; decklist and layout settings live in browser `localStorage`, while only the optional OpenCode Go key is saved owner-only in the local settings folder. The GUI can download and restore a workspace backup file containing the decklist, chosen printings, and layout settings.
- Requires Python 3.12 or newer. USB sending uses `pyusb`; on Linux the cutter normally needs `lp` group membership.
- Accessibility standard: undecided; no product-specific requirement has been established.

## Brand Commitments

The product name is `mtg-proxies`. No logo system, voice guide, or other identity constraints have been established.

## Evidence on Hand

- Working implementation and tests for the CLI and GUI, including mocked Scryfall and USB paths.
- Complete usage documentation in `README.md` and `docs/` (`gui.md`, `makercraft.md`, `handcut.md`, `slider.md`).
- Example screenshots at `examples/decklist.png` and `examples/deck_value.png`.
- Real cutter and printing procedures derived from the maintainer's own hardware.
- No testimonials, customer counts, benchmarks, pricing claims, or external user research exist. Future work must not fabricate them.

## Product Principles

1. **Keep it local.** Decklists, artwork, and generated files stay on the user's machine. The only outbound request beyond Scryfall is an explicit, user-triggered replacement-suggestion request to OpenCode Go; nothing is stored there by this product, and telemetry is never acceptable.
2. **Physical truth wins.** Verify dimensions, scale, bleed, and cut alignment against the real sheet — not just the screen.
3. **Show the work before printing.** Surface printings, warnings, and substitutions so the user can decide before committing paper and ink.
4. **One layout, every output.** PDF, cut files, and cutter templates must always describe the same geometry.
5. **Meet decklists where they are.** Accept the formats and sources players already use, and turn them into precise output.

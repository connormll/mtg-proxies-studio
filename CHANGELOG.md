## Unreleased

### Feat

- Add `mtg-proxies gui`, a local browser workspace with decklist import, visual printing selection, the full print options panel, PDF/cut-file downloads, browser printing, and optional MakerCraft sending
- Add Kimi replacement suggestions to the GUI: ask OpenCode Go for cards that fill the same role as a selected card, validate the picks against Scryfall, and replace every copy without leaving the editor
- Add a workspace backup bar to the GUI that downloads the decklist, chosen printings, and layout settings as JSON and restores them later
- Add `printings` to browse available card printings, and `--printing CARD=SET NUMBER` overrides to `print` and `convert`
- MakerCraft/Skycut registration marks, reusable full-sheet HPGL `.plt` template, and USB `send` command
- Add a complete procedure for using the MakerCraft/Skycut cutter in `docs/makercraft.md`
- Add `--mark-stroke` control and an automatic C10-safe MakerCraft grid/inset for Letter, A4, and 8x10 paper (6 cards/page on Letter, 10 mm inset)
- Document the Skycut origin at the bottom-right L corner and the 3-inch right-end-cap clearance
- Add `print --no-tokens` to exclude token cards from the print
- Add `print --handcut` to print full-page cut lines for a guillotine or rotary trimmer, using the largest grid that fits
- Add `print --slider` for sliding-blade paper trimmers with mirrored bleed, nine-card Letter layout, and full-page cut lines along every card edge
- Keep slider cut guides across the whole sheet, so the cross-cut lines remain after the first set of cuts

### Fix

- Skip cards that cannot be found during GUI import with a warning instead of blocking the whole deck, and skip printings missing from the local Scryfall database during generation
- Use low Kimi reasoning effort and a bounded completion size by default, so replacement suggestions return much faster; `MTG_PROXIES_SUGGESTION_EFFORT=high` or `max` restores deeper analysis
- Wait up to five minutes for Kimi replacement suggestions and report slow responses as a timeout instead of a connection failure
- Clamp rounded-image composition to the valid 0–1 RGB range
- Write downloaded cache files atomically and recover from truncated cached images

## 0.3.1 (2026-10-03)

### Fix

- support Scryfall JSONL bulk data
- provide user-agent during initial bulk data fetch

## 0.3.0 (2026-03-09)

### BREAKING CHANGE

- All commands use the `mtg-proxies` entrypoint now. Use `mtg-proxies print` instad of `print.py` now.

### Feat

- Merged entrypoints to a single mtg-proxies command
- Added support for "x" after the numbers in decklists

### Refactor

- Refactored warnings into ParseWarning class

## 0.2.1 (2026-02-15)

### Fix

- added headers for Scryfall API

## 0.2.0 (2026-02-15)

### Refactor

- refactored module structure

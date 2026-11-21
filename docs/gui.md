# Local browser interface

`mtg-proxies gui` starts a local workspace for preparing proxy sheets. It covers the PDF and cut-file path from the command line, with a visual card grid and printing picker.

The server listens only on `127.0.0.1`. There are no accounts, no database, and no telemetry. Card data and artwork come from Scryfall.

## Install and start

```bash
uv tool install "mtg-proxies[web] @ git+https://github.com/connormll/mtg-proxies-studio"
mtg-proxies gui --port 8000
```

The GUI opens `http://127.0.0.1:8000/` in the default browser. Use `--no-browser` if you only want to print the URL.

For a source checkout:

```bash
uv sync --extra web
uv run mtg-proxies gui --port 8000
```

## Workflow

1. **Import a decklist.** Paste text or Arena format, or upload a `.txt` file. Unknown cards are skipped with a line-specific warning, so the rest of the deck can still be generated. Misspelled names and substituted printings also produce warnings.
2. **Review the cards.** Duplicate lines for the same card are merged. Change quantities, remove cards, or exclude basic lands and tokens without deleting them. Low-resolution and non-English printings are flagged. If a card needs to be swapped, click **Replace** to ask Kimi for cards that fill the same role.
3. **Choose printings.** Click a card or its artwork. The picker shows one option per artwork by default, or every printing. The recommendation is marked, and the selected printing is applied to every copy of that card.
4. **Set the layout.** The modes are Standard, MakerCraft, Hand cut, and Slider trimmer. All PDF options are available, including paper size, scale, border crop, gap, bleed, corner radius, faces, background, crop marks, SVG cut files, and the MakerCraft registration settings.
5. **Generate.** The PDF and cut files are produced in a background job with progress updates. Downloads are separate; there is no ZIP.
6. **Print.** **Print PDF** sends the generated PDF to the browser's print dialog. In Brave, choose the same paper size and set scale to **100% / Actual size**. Do not use “Fit to page” or shrink-to-fit. The PDF can also be opened in a new tab.

The GUI defaults to **US Letter**. The command line defaults to A4. The paper setting is saved with the other options.

Changing a card, quantity, printing, or layout option clears the current outputs. Generate again before downloading, printing, or cutting.

## Replacement suggestions

The **Replace** button on a card tile asks Kimi to suggest cards that achieve the same effect. Kimi receives the card's rules text, type, mana cost, color identity, and your decklist card names. It returns up to five candidates with a short explanation of the equivalent effect and the closest tradeoff.

Suggestions are checked against the local Scryfall database before they are shown. Cards that cannot be resolved, the original card, and cards already in the deck are filtered out. If a suggestion is outside the deck's color identity, the dialog marks it. Choosing a suggestion replaces every copy of the original card and keeps the quantity; the dialog stays open until you pick a card, and nothing changes if you close it.

The feature requires [OpenCode Go](https://opencode.ai/docs/go/) and an API key with an active subscription. Create a personal key in the OpenCode Console and export it before starting the server:

```bash
export OPENCODE_API_KEY="oc_sk_..."
mtg-proxies gui
```

`OPENCODE_GO_API_KEY` is accepted as an alias. The default model is `kimi-k3.1-pro`. Kimi always reasons before answering, so the GUI requests the `low` reasoning effort by default; set `MTG_PROXIES_SUGGESTION_EFFORT=high` or `max` if you want slower, deeper analysis. Set `MTG_PROXIES_SUGGESTION_MODEL` to another model ID, or `MTG_PROXIES_SUGGESTION_BASE_URL` if your Go endpoint differs. The request sends only the selected card's data and your decklist card names; no generated files or artwork leave the machine.

## Printing and cutting

Use the exported PDF for the physical print. If an SVG cut file was requested, each page has its own download. In MakerCraft mode, the `.plt` template is always generated and is reusable for every page of the run.

When a MakerCraft template is present, **Send to Cutter** checks for a connected Skycut/MakerCraft over USB. It sends the template once after confirmation, for the sheet currently loaded in the cutter. The cutter uses its panel force and speed settings. The GUI does not change alignment, calibration, or cut pressure.

The cutter section only appears for the MakerCraft layout. If you do not use a cutter, the rest of the GUI is unaffected.

## Saved state

The decklist, quantities, card selections, print options, and import warnings are saved in the browser's `localStorage`. The OpenCode API key is read from the server environment and is never saved in the browser. Generated files are not saved in `localStorage` and must be generated again after reopening or reloading the app.

## Backups

The **Workspace backup** bar downloads a JSON file with the decklist, chosen printings, import notes, and layout settings. **Restore backup** loads one of those files and asks for confirmation before replacing cards that are already in the editor. The file stays on your machine; nothing is uploaded. Backups made before the backup format existed, containing only the saved workspace state, can also be restored.

Background jobs write temporary files under `mtg-proxies-gui` in the system temporary directory. Output folders older than one day are removed on the next launch.

## Frontend development

The React + TypeScript frontend lives in `web/`. Its production build is written to `mtg_proxies/gui/static/` and checked in, so running the GUI does not require Node.

For frontend development, run the backend and Vite separately:

```bash
# terminal 1
uv run --extra web mtg-proxies gui --port 8000 --no-browser

# terminal 2
cd web
npm install
npm run dev
```

Vite serves `http://127.0.0.1:5173/` and proxies `/api` to the backend on port 8000.

After changing frontend source, rebuild the packaged assets:

```bash
cd web
npm run build
```

The backend tests mock Scryfall and USB access:

```bash
uv run --extra web --extra dev pytest tests/gui_test.py
```

## Troubleshooting

- **`mtg-proxies: command not found`**: `~/.local/bin` is not on your shell PATH. Run `uv tool update-shell` and restart the shell. For fish, `fish_add_path ~/.local/bin` applies it immediately.
- **“The GUI requires optional web dependencies”**: the installed tool is missing the `web` extra. Reinstall it with the extra: `uv tool install --force --editable '.[web]'` from a checkout, or `uv tool install --force 'mtg-proxies[web] @ git+https://github.com/connormll/mtg-proxies-studio'`. Running `uv sync --extra web` only fixes the project virtualenv, not an installed tool.
- **“The GUI frontend has not been built”**: run `npm install && npm run build` in `web/`. This page only appears when the packaged `static/index.html` is missing.
- **Printing is slightly small or large**: verify the PDF print scale is 100% / Actual size and that the paper size matches the GUI setting. Do not use fit-to-page.
- **USB permission error**: the cutter normally requires membership in the `lp` group. If `usblp` claimed the interface, run `sudo modprobe -r usblp` and check again. The same advice and cut settings are in [`makercraft.md`](makercraft.md).
- **No cutter found**: check the USB cable, power, and `lsusb`; the device appears as `0483:5750`. Use the refresh button in the cutter panel after connecting it.
- **Replace says an API key is missing**: set `OPENCODE_API_KEY` to an OpenCode Go key before starting `mtg-proxies gui`, then restart the server. A key without an active Go subscription is rejected by OpenCode Go.
- **Replace times out**: Kimi reasons before answering and can take several minutes on a large deck list. The GUI waits up to five minutes, then asks you to try again. A dropped connection is reported separately as unreachable.

[![Tests](https://github.com/connormll/mtg-proxies-studio/actions/workflows/python-package.yml/badge.svg)](https://github.com/connormll/mtg-proxies-studio/actions/workflows/python-package.yml)

# MtG-Proxies

Create a high quality printable PDF from your decklist or a list of cards you want to proxy.

> **Fork notice:** This is a modified fork of [DiddiZ/mtg-proxies](https://github.com/DiddiZ/mtg-proxies), originally created by Robin Kupper and contributors. The original MIT license and copyright notice are preserved in [LICENSE](LICENSE); see [ATTRIBUTION.md](ATTRIBUTION.md) for details.

![](examples/decklist.png)

## Features

- **High resolution prints**  
  In contrast to online tools that provide this service (e.g. [MTG Press](http://www.mtgpress.net/)), this project creates the PDF file locally.
  This allows to use highest resolution Scryfall scans to create a large, high-dpi PDF file without regard for bandwidth limitations. For example, the generated PDF for a complete Commander decklist has a size of about 140MB.

- **Up-to-date card scans**  
  By directly utilizing the Scryfall API, all the latest sets are automatically availble as soon as they're available on Scryfall (which is usually incredibly fast). To not overrun Scryfall with requests, this project makes use of [Scryfall bulk data](https://scryfall.com/docs/api/bulk-data) to reduce API calls as much as possible. As requested by Scryfall, a small delay of 100ms is added between requests. However, as most work is done with a local copy of the bulk data, this is hardly noticeable.

- **Support for both text and Arena format decklists**
  `mtg-proxies` can work with both text and Arena format decklists.
  The Arena format is recommended, as it allows you to keep the same prints when moving decklists between multiple tools.
  There are even cases (i.e. tokens) where the name alone is not sufficient to uniquely specify a card.
  The Arena format helps in these case, as set and collector number are unique identifiers.
  However, as tools often only work with one of these formats, `mtg-proxies` is a flexible as possible, even supporting mixed mode.
  This is especially when you are making quick additions to a decklist and don't want to search for set and collector numbers.
  The `mtg-proxies convert` tool can be used to convert decklists between the two formats.

- **Sanity checks and recommender engine**  
  `mtg-proxies` warns you if you attempt to print a low-resolution scan and is able to offer alternatives.
  The `mtg-proxies convert` tool can automatically selects the best print for each card in a decklist with high accuracy, eliminating the need to manually select good prints.

- **Choose your printings**  
  Browse the available printings of a card with `mtg-proxies printings "Command Tower"` and pin a specific one with `--printing "Command Tower=C15 281"`.
  This is useful when the automatic recommendation picks an artwork you do not like.

- **Kimi replacement suggestions**  
  When a card needs to be swapped, click **Replace** on its tile in the browser workspace. Kimi, through OpenCode Go, reads the card's rules text and your decklist, then proposes cards that fill the same role, with a short explanation of each. Every suggestion is checked against Scryfall before it appears. This is optional and needs an OpenCode Go subscription and API key; see the browser interface section below.

- **Proxy print studio in the browser**  
  Run `mtg-proxies gui` for a local workspace where you can paste or upload a decklist, review every card, pick a printing from visual alternatives, tune the layout, and generate the PDF and cut files. Print the PDF directly from Brave, or send the MakerCraft template to a connected cutter. Download a workspace backup to keep the decklist, chosen printings, and layout settings in a file. The GUI runs only on localhost.

- **Print tuning**  
  Adjust the gap between cards (up to 3mm), add a mirrored bleed around each card, round the card corners, or exclude basic lands and tokens from the print.

- **Cutting machine support**  
  Generate a companion SVG cut file for each printed page, with card outlines that match the print layout exactly. For the Monoprice MakerCraft / Skycut C10, `--makercraft` adds camera registration marks and writes one reusable HPGL `.plt` template for the whole print run, and `mtg-proxies send` sends it directly over USB.

- **Hand cutting support**  
  Add `--handcut` to print cut lines for a guillotine, rotary trimmer, or craft knife. Cards are laid out edge to edge on the largest grid that fits the paper, square-cornered by default, so a few straight cuts separate the whole sheet. See [`docs/handcut.md`](docs/handcut.md).
  Add `--slider` for a manual paper trimmer with a sliding blade: it uses the same nine-card Letter grid, adds mirrored bleed, and prints full-page cut lines along every card edge. See [`docs/slider.md`](docs/slider.md).

- **Token support**  
  The `mtg-proxies tokens` tool appends the tokens created by the cards in a decklist to it, so you don't miss one accidentally. Caveat: This only works when Scryfall has the data on associated tokens. This is the case for cards printed or reprinted since Tenth Edition.

- **ManaStack and Archidekt integration**
  Directly use ManaStack and Archidekt deck ids as input for many functions instead of local decklist files.

  Decks on Archidekt must be set to public to be read.

## Usage

1. Install `mtg-proxies` using [uv](https://docs.astral.sh/uv/#installation).

```bash
uv tool install git+https://github.com/connormll/mtg-proxies-studio
```

2. (Optional) Prepare your decklist in MtG Arena format.
   This is not required, but recommended as it allows for more control over the process.

```txt
COUNT FULL_NAME (SET) COLLECTOR_NUMBER
```

E.g.:

```txt
1 Alela, Artful Provocateur (ELD) 324
1 Korvold, Fae-Cursed King (ELD) 329
1 Liliana, Dreadhorde General (WAR) 97
1 Murderous Rider // Swift End (ELD) 287
```

Or use the `convert` tool to convert a plain decklist to Arena format:

```bash
mtg-proxies convert tests/data/decklist_text.txt decklist.txt
```

4. Create a PDF file.

```bash
mtg-proxies print tests/data/decklist.txt decklist.pdf
```

Examples:

- Create separate outputs for front and back faces

```bash
mtg-proxies print tests/data/decklist.txt decklist_fronts.pdf --face front
mtg-proxies print tests/data/decklist.txt decklist_backs.pdf --face back
```

- Add a 2mm gap and 1mm bleed, and skip basic lands

```bash
mtg-proxies print tests/data/decklist.txt decklist.pdf --gap 2 --bleed 1 --no-basic-lands
```

- Skip token cards, for example when the decklist includes tokens appended by `mtg-proxies tokens`

```bash
mtg-proxies print tests/data/decklist.txt decklist.pdf --no-tokens
```

- Use a specific printing for a card, for example when the automatic recommendation picks art you do not like

```bash
mtg-proxies printings "Command Tower"
mtg-proxies print tests/data/decklist.txt decklist.pdf --printing "Command Tower=C15 281"
```

`mtg-proxies printings` shows one entry per distinct artwork by default, with the recommended print marked `*`. Add `--all` to list every printing, `--urls` to show Scryfall links, or `--limit N` to shorten the list. A printing can be written as `SET NUMBER`, `(SET) NUMBER`, `SET/NUMBER`, or a Scryfall card URL. Repeat `--printing` to override several cards; an override applies to every copy of that card in the decklist.

To make a choice permanent, use `mtg-proxies convert decklist.txt decklist.txt --printing "Command Tower=C15 281"` or add `(SET) NUMBER` to the decklist line:

```txt
1 Command Tower (C15) 281
```

Cards have rounded corners with a 2.5mm radius by default. Use `--corner-radius 0` to disable rounding, or a value between 0 and 10mm.

A companion SVG cut file is written next to the output by default, unless `--makercraft` is used without `--cut-file`. It uses the same page size and millimetre coordinates as the print, and all red paths are cut lines. For a multi-page output, the files are numbered, e.g. `decklist_cut_1.svg`, `decklist_cut_2.svg`. Use `--cut-file cuts.svg` to choose a different base name, or `--no-cut-file` to disable it.

### Browser interface

For a visual workflow, install the optional web dependencies and start the local workspace:

```bash
uv tool install "mtg-proxies[web] @ git+https://github.com/connormll/mtg-proxies-studio"
mtg-proxies gui --port 8000
```

The command opens `http://127.0.0.1:8000/` in your default browser. Add `--no-browser` to leave that step out. The server binds only to localhost and has no accounts or external data store. Network traffic is limited to Scryfall for card data and artwork, plus the optional Kimi replacement request described below.

In the GUI you can paste or upload a decklist, adjust quantities, remove cards, and click any card to choose a printing from thumbnails. It shows low-resolution and non-English warnings, exposes all print options, and remembers your decklist and settings in the browser. Generated PDFs, SVG cut files, and MakerCraft templates are separate downloads. **Print PDF** invokes the browser's PDF print dialog; use **100% / Actual size** and the same paper size selected in the app.

MakerCraft mode also shows a small Send to Cutter panel when the PLT template has been generated. It detects a connected Skycut/MakerCraft over USB and sends one reusable template per confirmed click. It uses the force and speed set on the cutter panel.

The GUI defaults to US Letter, while the CLI defaults to A4. Change the paper setting in the interface if you need A4. See [`docs/gui.md`](docs/gui.md) for the complete guide and frontend development notes.

#### Kimi replacement suggestions

Each card tile has a **Replace** action. It opens a dialog where Kimi compares the card with the rest of the deck and suggests cards that achieve the same effect, ranked by how closely they match the original role and mana value. Pick one to replace every copy in the editor. Nothing changes until you choose a suggestion.

The feature uses [OpenCode Go](https://opencode.ai/docs/go/) and needs an API key with an active Go subscription. Create a key in the OpenCode Console, then start the GUI with it:

```bash
export OPENCODE_API_KEY="oc_sk_..."
mtg-proxies gui
```

`OPENCODE_GO_API_KEY` also works as an alias. The default model is `kimi-k3.1-pro` with low reasoning effort so suggestions return quickly; set `MTG_PROXIES_SUGGESTION_EFFORT=high` or `max` for deeper analysis, or `MTG_PROXIES_SUGGESTION_MODEL` to use another Go model. Kimi's suggestions are validated against the local Scryfall database, so unknown or duplicate cards are dropped. The selected card and your decklist card names are sent to OpenCode Go only when you ask for suggestions; generated files and artwork stay on your machine.

### MakerCraft / Skycut C10

The Monoprice MakerCraft Desktop is a rebadged Skycut C10. It uses HPGL
(`.plt`) cut files and camera registration marks instead of SVG. Add
`--makercraft` to the print command. See
[`docs/makercraft.md`](docs/makercraft.md) for the full step-by-step procedure,
including pen tests, cut settings, and troubleshooting.

```bash
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --gap 1.5 --makercraft
```

This does two things:

1. Adds four black L-shaped registration marks (plus a small orientation dash) to every page of the PDF. Print at **100 % / Actual size**; do not use "Fit to page", "Scale to fit", or borderless scaling.
2. Writes one reusable `makercraft.plt` template next to the PDF. The template contains the full card grid (six slots on Letter or 8x10), so the same file is used for every page. On the final page with fewer cards, the extra slots are simply cut as blank cards. The `TB25`/`CT1` preamble tells the cutter to scan the marks before cutting. The default overcut is 1 mm; use `--overcut 0` to disable it.

By default, `--makercraft` writes only the PDF and the one `makercraft.plt`; it skips the SVG cut files. Add `--cut-file cuts.svg` if you also want SVG output.

The `--gap 1.5` gives the blade a little room between cards. Use a larger value up to 3 mm if your material or blade needs it. `--makercraft` requires a PDF output, since the registration marks are printed on the sheet.

For the C10, MakerCraft mode automatically keeps the layout inside the cutter's limits. On Letter it uses a 3 × 2 grid (six cards/page), a 10 mm mark inset, and a 259 × 196 mm mark box. On 8x10 it uses the same six-card grid with a 7 mm inset. The command prints the chosen grid and inset. A nine-card 3 × 3 Letter grid leaves only about 8 mm above and below the cards, so the marks sit almost on the card edges; it is intentionally not used in MakerCraft mode. Six cards/page is the same density as the old 8x10 workflow. Without `--makercraft`, `--paper 8.5x11` still uses the normal nine-card grid.

The template is tied to the print layout: paper size, scale, border crop, gap, bleed, corner radius, mark inset/arm/stroke, and overcut. Keep those options the same whenever you reuse `makercraft.plt`. The deck only changes which card images fill the slots, not where the slots are, so the same template fits every page. If you change the paper or layout, regenerate both the PDF and the template. Use `--plt-file ~/makercraft-letter.plt` to keep a template outside the output folder or to keep separate templates for different formats.

Load the sheet with the top edge toward the back of the cutter. Put the blade tip on the **corner of the bottom-right L** (where its two arms meet), and keep that mark at least 3 inches (76 mm) from the right end cap so the camera has room to photograph it. Then on the cutter select **Set → Camera**, make **Align** red, check **AutoMark**, and press **Home**.

Do a pen test first:

```bash
mtg-proxies send makercraft.plt --force 5 --speed 5
```

This scans the marks and draws the card outlines. If they line up, switch to the blade and send the same file without `--force`/`--speed`, so the cutter uses the force and speed set on its panel:

```bash
mtg-proxies send makercraft.plt
```

`mtg-proxies send --list` lists connected devices. Add `--device <serial-or-product-substring>` if more than one is connected, and `--dry-run` to inspect the HPGL payload without touching the cutter. USB sending uses `pyusb`; on Linux the cutter is normally accessible to users in the `lp` group without root. The same `.plt` file can be copied to a FAT32 USB flash drive and opened from the cutter's **USB → Open File → USB DISK** menu, so SCAL and Windows are not required.

The registration marks are 7 mm from the page edge by default. In MakerCraft mode the tool raises the inset automatically when needed for the C10 (10 mm on Letter, 18.5 mm on A4). If your printer clips them, use a larger `--mark-inset` and regenerate both the PDF and the template. Use light-colored paper for the camera; if you print on dark cardstock, put a white box behind each mark.

### Hand cutting

Add `--handcut` to produce a sheet for a guillotine, rotary trimmer, or craft knife instead of a cutting machine:

```bash
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --handcut
```

This prints thin black cut lines along every card edge, running to the page edges. The lines never cross the card artwork, and they disappear when you cut along them. After printing at **100 % / Actual size**, align a straight edge or trimmer with a line and cut through the sheet.

Handcut mode differs from the default in three ways:

- It uses the largest grid that fits, so Letter paper gets nine cards in a 3 × 3 grid.
- Cards are square-cornered unless you pass `--corner-radius`. Square corners are easier to trim; if you want round corners, print with the default `--corner-radius 2.5` and use a 2.5 mm corner punch after cutting.
- SVG cut files are skipped unless you pass `--cut-file`.

The default border crop still applies, so the finished cards are about 61.1 × 86.5 mm. That is intentional: the proxy slips into a sleeve in front of a real card. Use `--border_crop 0` if you want the full 63.5 × 88.9 mm card size.

Leave `--gap` at 0 for the simplest workflow: cards are edge to edge and one straight cut separates each pair. If you set a gap, the tool prints two lines around each gutter, one on each card edge; cut along both to keep every card at the finished size.

See [`docs/handcut.md`](docs/handcut.md) for the full procedure and paper recommendations.

### Sliding-blade paper trimmer

Add `--slider` to optimize a sheet for a manual paper trimmer with a sliding blade. The mode maximizes the grid, adds mirrored bleed, and prints straight cut lines along every card edge, so the lines cross at every card corner and never cross the card art:

```bash
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --slider
```

With the default border crop this gives nine cards in a 3 × 3 grid on Letter, 2 mm of bleed on every side, and 4 mm gutters. The bleed occupies the gutter, so the two cut lines around each gutter sit exactly on the finished card edges. The lines run from one paper edge to the other, so they cross at every card corner and the cross-cut guides stay on the strips after the first set of cuts. Rotate the strips and cut along the remaining lines. Use `--bleed` to change the bleed and `--gap` to set a minimum gutter; the gutter is always at least twice the bleed.

The default 2 mm bleed leaves about 5.9 mm of paper above and below the card grid. If your printer clips the card edges, reduce the bleed or use `--border_crop 0` only after a test page. See [`docs/slider.md`](docs/slider.md) for the cutting order, paper settings, and the full layout table.

## Updating

```bash
uv tool upgrade mtg-proxies
```

## Help

### print

```txt
usage: mtg-proxies print [-h] [--dpi DPI] [--paper WIDTHxHEIGHT]
                         [--scale FLOAT] [--border_crop PIXELS] [--gap MM]
                         [--bleed [MM]] [--corner-radius MM] [--cut-file PATH]
                         [--no-cut-file] [--makercraft] [--handcut] [--slider]
                         [--mark-inset MM] [--mark-arm MM] [--mark-stroke MM]
                         [--overcut MM] [--plt-file PATH] [--no-basic-lands]
                         [--no-tokens] [--background COLOR]
                         [--cropmarks | --no-cropmarks]
                         [--faces {all,front,back}]
                         [--printing CARD=SET NUMBER]
                         decklist outfile

Prepare a decklist for printing.

positional arguments:
  decklist              path to a decklist in text/arena format, or manastack:{manastack_id}, or archidekt:{archidekt_id}
  outfile               output file. Supports pdf, png and jpg.

options:
  -h, --help            show this help message and exit
  --dpi DPI             dpi of output file for raster formats (png, jpg); ignored for pdf (default: 300)
  --paper WIDTHxHEIGHT  paper size in inches, or a4/letter (default: a4)
  --scale FLOAT         scaling factor for printed cards (default: 1.0)
  --border_crop PIXELS  how much to crop inner borders of printed cards, in source image pixels (default: 14)
  --gap MM              gap between cards in mm, between 0 and 3 (default: 0.0)
  --bleed [MM]          add mirrored-edge bleed around each card in mm, between 0 and 10; use without a value for 3 mm (default: 0, or 2 with --slider)
  --corner-radius, --corner_radius MM
                        corner radius of printed cards in mm, between 0 and
                        10; 0 disables rounding (default: 2.5, or 0 with
                        --handcut/--slider)
  --cut-file PATH       write SVG cut file(s) for a cutting machine; PATH sets the base name
                        (default: <outfile>_cut.svg, numbered per page for multi-page outputs)
  --no-cut-file         do not write SVG cut file(s)
  --makercraft          add Skycut/MakerCraft registration marks and write one
                        reusable full-sheet HPGL .plt template; SVG cut files
                        are skipped unless --cut-file is given
  --handcut, --hand-cut
                        add cut lines to the PDF for hand trimming with a
                        guillotine or rotary trimmer; uses square corners
                        unless --corner-radius is given, and skips SVG cut
                        files unless --cut-file is given
  --slider, --sliding-trimmer
                        optimize the PDF for a manual sliding-blade paper
                        trimmer: use the largest bleed layout, print full-page
                        cut lines along every card edge, use square corners
                        unless --corner-radius is given, and skip SVG cut files
                        unless --cut-file is given
  --mark-inset MM       distance of MakerCraft registration marks from the
                        page edge in mm; raised automatically when needed for
                        the C10 (default: 7.0)
  --mark-arm MM         arm length of the L-shaped MakerCraft registration
                        marks in mm (default: 10.0)
  --mark-stroke MM      line width of the MakerCraft registration marks in mm
                        (default: 1.0)
  --overcut MM          extend MakerCraft cut paths past the start to close
                        the knife seam in mm (default: 1.0)
  --plt-file PATH       path for the reusable MakerCraft .plt template
                        (default: makercraft.plt next to the PDF)
  --no-basic-lands      exclude basic lands from the print
  --no-tokens           exclude tokens from the print
  --background COLOR    background color, either by name or by hex code (e.g. black or "#ff0000", default: None)
  --cropmarks, --no-cropmarks
                        add crop marks (png, jpg); ignored for pdf
  --faces {all,front,back}
                        which faces to print (default: all)
  --printing CARD=SET NUMBER
                        use a specific printing for a card, e.g. 'Command
                        Tower=C15 281'; can be repeated for multiple cards
```

### printings

```txt
usage: mtg-proxies printings [-h] [--all] [--limit N] [--urls] card

List available printings for a card.

positional arguments:
  card        card name

options:
  -h, --help  show this help message and exit
  --all       list every printing instead of one per artwork
  --limit N   maximum number of printings to show
  --urls      show Scryfall links
```

### send

```txt
usage: mtg-proxies send [-h] [--list] [--device DEVICE] [--yes]
                        [--force FORCE] [--speed SPEED] [--dry-run]
                        [plt]

Send an HPGL .plt cut file to a Skycut/MakerCraft over USB.

positional arguments:
  plt              path to the .plt file to send

options:
  -h, --help       show this help message and exit
  --list           list connected Skycut/MakerCraft devices
  --device DEVICE  serial number or product-string substring to select a
                   device
  --yes            do not ask for confirmation before sending
  --force FORCE    override cut pressure (1-160)
  --speed SPEED    override speed (1-12)
  --dry-run        print the HPGL payload instead of sending
```

### gui

```txt
usage: mtg-proxies gui [-h] [--port PORT] [--no-browser]

Start the local browser interface for preparing proxies.

options:
  -h, --help     show this help message and exit
  --port PORT    port for the local web server (default: 8000)
  --no-browser   do not open the default browser automatically
```

### convert

```txt
usage: mtg-proxies convert [-h] [--format {arena,text}] [--clean]
                           [--printing CARD=SET NUMBER]
                           decklist outfile

Convert a decklist to text or arena format.

positional arguments:
  decklist              path to a decklist in text/arena format, or manastack:{manastack_id}, or archidekt:{archidekt_id}
  outfile               output file

options:
  -h, --help            show this help message and exit
  --format {arena,text}
                        output format (default: arena)
  --clean               remove all non-card lines
  --printing CARD=SET NUMBER
                        use a specific printing for a card, e.g. 'Command
                        Tower=C15 281'; can be repeated for multiple cards
```

### tokens

```txt
usage: mtg-proxies tokens [-h] [--format {arena,text}] decklist

Append the created tokens to a decklist.

positional arguments:
  decklist              path to a decklist in text/arena format, or manastack:{manastack_id}, or archidekt:{archidekt_id}

options:
  -h, --help            show this help message and exit
  --format {arena,text}
                        output format (default: arena)
```

Example:

```bash
tokens.py tests/data/token_generators.txt
```

### Deck Value Decomposition

```txt
usage: mtg-proxies deck_value [-h] [--lump-threshold FLOAT] decklist

Show deck value decomposition.

positional arguments:
  decklist              path to a decklist in text/arena format, or manastack:{manastack_id}, or archidekt:{archidekt_id}

options:
  -h, --help            show this help message and exit
  --lump-threshold FLOAT
                        lump together cards with lesser proportional value (default: 0.03)
```

Example:

```bash
mtg-proxies deck_value manastack:1234536
mtg-proxies deck_value archidekt:365563
```

![](examples/deck_value.png)

## Acknowledgements

- [MTG Press](http://www.mtgpress.net/) for being a very handy online tool, which inspired this project.
- [Scryfall](https://scryfall.com/) for their [excellent API](https://scryfall.com/docs/api).

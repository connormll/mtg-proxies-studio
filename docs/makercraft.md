# Using the MakerCraft / Skycut C10 cutter

This is the complete procedure for printing and cutting MTG proxies with the
Monoprice MakerCraft Desktop. The MakerCraft is a rebadged **Skycut C10**; it
accepts HPGL (`.plt`) jobs and uses camera registration marks. SCAL and Windows
are not required.

The workflow writes:

- a print PDF with registration marks on every page, and
- **one reusable `makercraft.plt` template** for the full card grid.

The same `.plt` file is used for every page. If the last page has fewer than six
cards, the template still cuts all six slots; the unused slots are blank cards.
That is expected.

## Quick start

1. Generate:
   ```bash
   mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --gap 1.5 --makercraft
   ```
   Use `--paper 8x10` instead if you are printing on 8 × 10 paper.
   `--paper letter` is an alias for `--paper 8.5x11`. The tool automatically
   chooses a C10-safe card grid and mark inset.
2. Print `proxies.pdf` at **100 % / Actual size**.
3. Load the sheet with the top edge toward the back. Put the blade tip on the
   **corner of the bottom-right L** (where its two arms meet), and keep that
   mark at least 3 inches (76 mm) from the right end cap. Set
   **Set → Camera → Align** red, check **AutoMark**, and press **Home**.
4. Pen test:
   ```bash
   mtg-proxies send makercraft.plt --force 5 --speed 5
   ```
5. Blade cut:
   ```bash
   mtg-proxies send makercraft.plt
   ```

The detailed steps, cut settings, and troubleshooting are below.

## 1. Generate the print PDF and cut template

From the `mtg-proxies` checkout:

```bash
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --gap 1.5 --makercraft
```

This creates:

| File | Purpose |
|---|---|
| `proxies.pdf` | Print file. Every page has four black L registration marks and an orientation dash. |
| `makercraft.plt` | One full-sheet HPGL template. Send the same file for every page. |

SVG cut files are skipped by default in MakerCraft mode. If you also want SVG
output, add `--cut-file cuts.svg`.

The command prints the layout it chose, for example:

```text
Using a 10 mm mark inset instead of 7 mm to keep the marks inside the C10 area.
MakerCraft layout: 6 cards/page (3x2), 10 mm mark inset.
```

On Letter paper, MakerCraft mode uses **six cards per page** in a 3 × 2 grid.
That leaves a clear band at the top and bottom for the registration marks. A
nine-card 3 × 3 Letter grid leaves only about 8 mm above and below the cards,
so the marks sit almost on the card edges and the camera can confuse them with
the card borders. Six cards per page is the same density as the 8 × 10 layout,
so the page count is unchanged from the old 8 × 10 workflow. An 80-card print
is 14 Letter pages instead of 9 pages with the unsafe 3 × 3 layout.

The examples below use the default `makercraft.plt`. If you used `--plt-file`,
substitute that path in the `send` commands.

The template is tied to the print layout: paper size, scale, border crop, gap,
bleed, corner radius, mark inset/arm/stroke, and overcut. Keep those options the same
when reusing `makercraft.plt`. If you change the paper or layout, regenerate both
the PDF and the template.

To keep a master template outside the output folder:

```bash
mtg-proxies print decklist.txt proxies.pdf \
  --paper 8.5x11 --gap 1.5 \
  --makercraft \
  --plt-file ~/makercraft-letter.plt
```

The deck itself does not change the template. Only the card images filling the
slots change.

## 2. Print the sheets

Print **all pages** of the PDF at **100 % / Actual size**.

Do **not** use:

- “Fit to page”
- “Scale to fit”
- “Shrink oversized pages”
- borderless printing, if it scales the page

The registration marks and the cut paths must stay at the same scale. Borderless
printing can enlarge the PDF slightly to reach the paper edges, which changes
the mark spacing even when the scaling box says 100 %.

### Paper

- **Matte printable sticker paper** — print, kiss-cut, peel, and stick each
  proxy onto a bulk common. This gives the best feel and thickness.
- **200–250 gsm matte cardstock** — print and cut through. Slightly thinner
  than a real card, but fine in sleeves.
- Avoid glossy paper for the first tests. The camera sees matte marks more
  reliably.

The marks must be black on a light background. If you print on colored
cardstock, put a white box behind each registration mark.

The PDF page follows the `--paper` option. For Letter it is 8.5 × 11 in
(215.9 × 279.4 mm); for 8 × 10 it is 8 × 10 in (203.2 × 254 mm). Set the
printer’s paper size to the paper you actually load, and set scaling to
**100 % / Actual size**. If the printer offers “fit to printable area,” turn it
off. Check that all four marks are on the paper before cutting.

For the C10, the relevant limits are:

- about **220 mm maximum contour-cutting width**;
- the tool keeps the mark box within about **260 mm**, the size of the proven
  8 × 10 layout;
- the starting mark should be at least **3 inches (76 mm) from the right end
  cap**, so the camera has room to move right and take the photo.

MakerCraft mode keeps the layout inside those limits automatically:

| Paper | Grid | Cards/page | Mark inset | Mark box (H × W) |
|---|---|---:|---:|---|
| 8.5 × 11 | 3 × 2 | 6 | 10 mm | 259 × 196 mm |
| 8 × 10 | 3 × 2 | 6 | 7 mm | 240 × 189 mm |
| A4 | 3 × 2 | 6 | 18.5 mm | 260 × 173 mm |

The tool will raise a smaller `--mark-inset` to the safe value for the paper,
and prints a line telling you what it used. A larger `--mark-inset` is respected
as long as the marks still fit outside the card grid.

The marks are 10 mm arms with a 1 mm stroke by default. The short orientation
dash is separate from the bottom-right L.

If your printer clips the corner marks, increase the inset and regenerate both
files:

```bash
mtg-proxies print decklist.txt proxies.pdf \
  --paper 8.5x11 --gap 1.5 \
  --makercraft \
  --mark-inset 12
```

The new template uses the new mark box; do not mix it with an older print.

If you already have an 8 × 10 PDF, you can still print it on Letter at 100 %
with the printer centering the 8 × 10 content. The extra white margin is just
waste. Generate a matching 8 × 10 `makercraft.plt` for that sheet.

## 3. Set up the cutter

1. Power on the cutter.
2. Install the blade holder with a **45° blade**, or install the test pen for
   the alignment check.
3. Set the blade depth shallow at first — just enough to expose the tip.
4. Put the printed sheet on the cutting mat, **printed side up**, with the **top
   edge of the page toward the back of the cutter**. Align the sheet with the
   mat’s grid lines so it is square and flat.
5. Position the sheet so all four corner marks are inside the usable cutting
   area and the bottom-right mark is near the lower-right/front-right area. The
   short 5 mm orientation dash should be near the front-right corner.
6. Keep the starting mark at least **3 inches (76 mm) from the right end cap**.
   If the right mark is closer than that, the camera cannot move far enough
   right to photograph it, and AutoMark will fail on the first mark. Shift the
   sheet left or center it in the cutter.
7. Keep all four corner marks visible. If the sheet slides, tape only the outer
   waste edge with painter's tape. Do not tape over the marks.
8. Load the mat into the cutter, make sure the pinch wheels sit on the mat (not
   on top of a corner mark), and lower the pinch-wheel lever.
9. Move the blade holder so the **blade tip is on the corner of the
   bottom-right L** — the point where its vertical and horizontal arms meet.
   This is the Skycut PNC origin; do not start below, to the right, or in the
   middle of the arms. Use the arrow keys; the middle button toggles slow
   movement for fine positioning.
10. On the cutter select **Set → Camera**. Make **Align** red and check
    **AutoMark** (some firmware calls this **Auto PNC**). Press **Home**.

The camera is a close-up around the carriage, not a full-page preview. Seeing
only one mark — or needing to move the head to find it — is normal. AutoMark
moves the head to the expected mark positions when the job starts.

The marks are already on the PDF, and the `.plt` contains the registration-mark
box in its `TB25` line. You do **not** need to type mark coordinates or draw
marks on the cutter. You normally do not need to enter a paper size on the
cutter either; the `TB25` line defines the mark box. If your panel has a paper
or media size option, leave it on Auto if possible. Otherwise use the same size
as the `--paper` option used to generate the files (8.5x11 in this example).
Avoid any fit/scale mode. If your panel has a `Mark Set` or `Array Mark` option,
leave it on the single/4-mark setting; those options are for repeat arrays, not
for this one-sheet job.

The cutter is now ready to scan the four L marks when the job starts.

### If the camera asks for an origin target

For normal PNC jobs, the four-mark scan does the alignment. If your panel asks
you to set an origin target first:

1. Move the blade holder roughly over the bottom-right registration mark.
2. Select **Set → Camera**, then press **OK** to take a photo.
3. Tap the corner of the bottom-right L in the photo so the red cross moves
   near the point where its arms meet.
4. Press **OK**, then use the arrow keys to center the red cross precisely on
   the mark.
5. Press **OK**, then press **Home**.

### Camera calibration

If this is a new cutter, or it has been moved or bumped, run
**Set → Camera → Calibrate** before trusting AutoMark. The calibration teaches
the cutter the camera offset from the blade. Use the test pen and follow the
panel prompts. Re-run it if cuts are consistently offset in one direction even
when the marks are detected.

## 4. Connect over USB

Plug the cutter into the computer and check that it is visible:

```bash
mtg-proxies send --list
```

You should see the cutter, for example:

```text
SKY32 Vi SKYCUT_61DE  bus=... address=...
```

The USB ID is `0483:5750`. `lsusb` may label it as an “LED badge”; that is a
stale name. The product string is the reliable identification.

If more than one cutter is connected, pass
`--device <serial-or-product-substring>` to `send`. Use `--dry-run` to inspect
the HPGL payload without moving the cutter.

On Linux, the cutter is normally accessible to users in the `lp` group:

```bash
groups | grep lp
```

If your user is not in `lp`, ask an administrator to add you and then log out
and back in. If another driver has claimed the interface, unload `usblp`:

```bash
sudo modprobe -r usblp
```

Close SCAL, Wine, or any other program that may be holding the cutter before
sending a job.

## 5. Do a pen test first

Use the test pen and a plain sheet, or a marked test print. Do not put a blade
near the paper until the pen lines line up.

With the sheet loaded, the origin set, the camera set to **Align** red and
**AutoMark** checked, and **Home** pressed, send the template with a light
pressure and slow speed:

```bash
mtg-proxies send makercraft.plt --force 5 --speed 5
```

The cutter scans the four marks and draws the six card outlines. They should sit
on the printed card borders.

If the outlines are consistently offset in one direction, adjust the camera
calibration (`Set → Camera → Calibrate`) or nudge the origin. If the outlines
are rotated or scaled, check:

- the PDF was printed at 100 %,
- the sheet is flat and not skewed on the mat,
- the marks are not clipped or covered,
- the camera lens is clean,
- AutoMark is checked.

Repeat the pen test until the outlines line up.

## 6. Cut with the blade

1. Install the 45° blade.
2. Set the blade depth, force, and speed on the cutter panel.
3. Do a test cut on scrap of the same material before cutting a printed sheet.
4. Load the printed sheet, set the origin, and run **Set → Camera → Home** as
   described above.
5. Send the same template:

```bash
mtg-proxies send makercraft.plt
```

The command asks for confirmation. Add `--yes` to skip the prompt for repeated
sheets. Keep hands clear of the carriage; if the panel shows **Start Cut**,
press it.

The cutter scans the marks, then cuts the six card outlines. For each new sheet,
load the sheet, set the origin, press **Home**, and send the same
`makercraft.plt` again. There is no separate page-2 file.

On the last page with fewer than six cards, the template still cuts all six
slots. The extra slots are blank; that is normal.

### Starting cut settings

Use these as starting points, then adjust for your material:

| Material | Blade | Force | Speed | Passes |
|---|---|---:|---:|---:|
| Printable sticker paper (kiss cut) | 45° | 10–25 | 5 | 1 |
| Sticker paper (cut through backing) | 45° | 35–55 | 5 | 1 |
| 110 lb / 200 gsm cardstock | 45° | 45–60 | 5 | 1–2 |
| 250 gsm cardstock | 45° | 55–75 | 4–5 | 2 |

The cutter’s force scale is 1–160 and its speed scale is 1–12. Start with a
shallow blade and low force. If the cut is about 90 % through, use **Multi-Cut**
instead of adding a lot of force. Too much force can drag the blade and cause
drift.

The `.plt` template does not set force or speed by default. The panel settings
are used. `--force` and `--speed` on the `send` command are for one-off jobs
such as the pen test; omit them for normal cutting.

## 7. Reusing the template

`makercraft.plt` is a full-sheet template, not a per-page file. Reuse it for:

- every page of the current deck,
- another deck printed with the same paper and layout settings,
- any page where you do not mind cutting blank card slots.

The file is only rewritten when the layout content changes. If you keep the
same paper, scale, border crop, gap, bleed, corner radius, mark inset/arm/stroke,
and overcut, repeated print runs produce the same template.

For separate formats, keep separate master files:

```bash
# Letter, 1.5 mm gap
mtg-proxies print decklist.txt proxies-letter.pdf \
  --paper 8.5x11 --gap 1.5 \
  --makercraft --plt-file ~/makercraft-letter.plt

# 8x10, 1.5 mm gap
mtg-proxies print decklist.txt proxies-8x10.pdf \
  --paper 8x10 --gap 1.5 \
  --makercraft --plt-file ~/makercraft-8x10.plt

# A4, no gap
mtg-proxies print decklist.txt proxies-a4.pdf \
  --paper a4 --gap 0 \
  --makercraft --plt-file ~/makercraft-a4.plt
```

The automatic C10-safe layout applies to each format. Do not use a template
from one format with a PDF printed in another format.

## 8. USB flash drive fallback

If USB sending is inconvenient, the cutter can run the same `.plt` from a USB
flash drive:

1. Copy `makercraft.plt` to a FAT32 USB flash drive.
2. Insert the drive into the cutter’s USB-flash port.
3. On the cutter select **USB → Open File → USB DISK** and choose the `.plt`
   file.
4. Set **Set → Camera → Align** red, check **AutoMark**, and press **Home**.
5. Press **Start Cut**.

The same `TB25`/`CT1` preamble makes the cutter scan the marks and cut. The same
template works for every page.

## 9. Optional network sending

If the cutter is on your network and you know its IP address, the Skycut command
extension uses raw TCP port 8080:

```bash
nc <cutter-ip> 8080 < makercraft.plt
```

USB is the primary path; network sending is optional.

## 10. Troubleshooting

### `send --list` shows no cutter

- Check the USB cable and the cutter’s power.
- Try another USB port.
- Run `lsusb`; the cutter may appear as `0483:5750` with the misleading name
  “LED badge”.
- Make sure no other program is using the cutter.
- Check that your user is in the `lp` group.

### Permission denied or interface busy

- Confirm `groups | grep lp`.
- If `usblp` has claimed the interface, run `sudo modprobe -r usblp` and try
  again.
- Close SCAL/Wine and any other cutter software.

### The camera does not find the marks

Work through these in order:

- Confirm you printed the **marked** PDF generated with `--makercraft`, not an
  older unmarked `finneas-print.pdf`.
- Regenerate both files with the current version. The PDF and `.plt` must come
  from the same run.
- Print at 100 % / Actual size. “Fit to page” changes the mark spacing and can
  make the camera fail.
- Use light-colored, matte paper. Glossy or dark paper can make the marks
  invisible to the camera.
- Keep all four marks fully visible; do not tape over them or cover them with a
  pinch wheel.
- Check that the marks were not clipped by the printer.
- Make sure the sheet is oriented with the top edge toward the back and the
  5 mm orientation dash near the front-right.
- Move the blade holder so the **blade tip is on the corner of the bottom-right
  L**. This is the Skycut PNC origin. Starting below, to the right, or in the
  middle of the arms can make the camera miss the first mark and offset the
  cut.
- Keep that starting mark **at least 3 inches (76 mm) from the right end cap**.
  If it is too close, the camera cannot move right far enough to photograph it.
  Shift the sheet left or center it in the cutter.
- Clean the camera lens.
- Run **Set → Camera → Calibrate** if the camera has never been calibrated on
  this cutter. AutoMark can fail or cut offset when the camera-to-blade offset
  is wrong.
- Confirm **AutoMark** or **Auto PNC** is checked and **Align** is red.
- Check the cutter’s paper/media size setting. It should be **Auto** or the
  same size used in `--paper` (8.5x11 here).
- If the camera screen shows a photo, check whether the marks are visible in
  the photo. If they are not, the issue is paper placement, lighting, or the
  camera view. If they are visible but not detected, the marks may be too thin
  or faint.
- If your panel has a mark type/size setting, use the four L-shaped corner
  marks. Do not use a 3-point or non-L mark type.
- Try the same `makercraft.plt` from a USB flash drive. If it works from USB,
  the issue is the send/start sequence rather than the marks.

The PLT header should match the paper and inset. For the automatic C10-safe
layouts it starts with:

```text
# 8.5 x 11, 10 mm inset -> 259.4 x 195.9 mm mark box
TB25,10376,7836;

# 8 x 10, 7 mm inset -> 240 x 189.2 mm mark box
TB25,9600,7568;
```

If it starts with `TB25,10616,8076;`, it is the old 8.5 × 11 layout with a
7 mm inset. That mark box is about 265 mm long and puts the marks too close to
the paper edge and the card grid. Regenerate with the current version; do not
cut that old sheet.

If the marks are visible but still not detected, regenerate a fresh pair with
longer and thicker marks:

```bash
mtg-proxies print decklist.txt proxies-test.pdf \
  --paper 8.5x11 --gap 1.5 \
  --makercraft \
  --mark-arm 12 \
  --mark-stroke 1.5
```

Use the new `proxies-test.pdf` with the new `makercraft.plt`. The automatic
layout still applies; the tool will report the grid and inset it chose. Changing
only `--mark-arm` or `--mark-stroke` does not change the mark box or the cut
paths, so the `.plt` stays identical; the template from your main print run is
still valid.

### The cut is offset from the printed cards

- Run the pen test again.
- Check that the PDF was printed at 100 %, not “Fit to page”.
- Adjust the camera calibration Δx/Δy or nudge the origin.
- Make sure the sheet is flat and not rotated on the mat.

### The blade does not cut through

- Increase blade depth slightly.
- Increase force in small steps.
- Use Multi-Cut for a second pass.
- Do not add excessive force; it can drag the blade and cause drift.

### The blade cuts too deeply

- Reduce blade depth first.
- Reduce force.
- Use a fresh cutting mat or a less worn area.

### The template no longer matches the print

- The template is tied to the print layout. Regenerate the PDF and the template
  together with the same options.
- Keep separate templates for different paper sizes or layouts.
- Do not reuse a template after changing `--paper`, `--scale`,
  `--border_crop`, `--gap`, `--bleed`, `--corner-radius`, `--mark-inset`,
  `--mark-arm`, `--mark-stroke`, or `--overcut`.

## Card size note

MakerCraft mode uses rounded corners by default, so the printed and cut cards
are about **63.5 × 88.9 mm**: full size, matching or slightly exceeding a real
card. The cut template matches that printed size. Rounding does not change the
card outline, so rounded cards do not use the smaller sleeve-proxy border crop.

If you want the smaller sleeve proxy, pass `--corner-radius 0`. The default
`--border_crop 14` then gives cards about 61.1 × 86.5 mm, which slip into a
sleeve in front of a real common. Regenerate the PDF and template together:

```bash
mtg-proxies print decklist.txt proxies.pdf \
  --paper 8.5x11 --gap 1.5 \
  --corner-radius 0 \
  --makercraft
```

Changing the corner radius or border crop changes the card grid and the cut
template; keep the matching PDF and `makercraft.plt` together.

## Why not SCAL?

SCAL’s USB path is a Windows printer-class driver, and Wine does not pass the
cutter through. The cutter itself accepts HPGL over its USB printer interface.
`mtg-proxies send` talks to it directly through libusb, which is the native
Linux equivalent of what SCAL does on Windows.

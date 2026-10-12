# PNG/JPG Rendering Guide

`generate_cards_from_csv.py` always writes SVG cards and can also render them to PNG, JPG and an A4 print PDF. This guide explains the raster options.

## Overview

Output formats:
- **SVG**: Vector format (always generated)
- **PNG**: Lossless raster, best quality
- **JPG**: Raster optimized for file size
- **PDF**: A4 printable sheets, 3x3 cards per page, each card repeated `Nombre` times

## Basic Usage

### Generate SVG Cards (Default)
```bash
python generate_cards_from_csv.py Updated_Cards.csv
```
This creates SVG files in the `output/` directory.

### Generate PNG Cards
```bash
python generate_cards_from_csv.py Updated_Cards.csv --png-output ./output_png
```
This creates PNG files in `output_png/`: by default each card is rendered at 1592x2164 px (2x the 796x1082 SVG) and surrounded by a 60 px border, so the files are 1712x2284 px.

### Generate JPG Cards
```bash
python generate_cards_from_csv.py Updated_Cards.csv --jpg-output ./output_jpg
```
This creates JPG files in the `output_jpg/` directory, with the same size and border as the PNGs.

### Generate Both PNG and JPG
```bash
python generate_cards_from_csv.py Updated_Cards.csv --png-output ./output_png --jpg-output ./output_jpg
```

### Generate All Formats (SVG + PNG + JPG + PDF)
```bash
python generate_cards_from_csv.py Updated_Cards.csv \
    --png-output ./output_png \
    --jpg-output ./output_jpg \
    --pdf-output ./cards.pdf
```

## Advanced Options

### Custom Image Dimensions

`--image-width` / `--image-height` set the card size in pixels, before the border:

```bash
python generate_cards_from_csv.py Updated_Cards.csv \
    --png-output ./output_png \
    --image-width 796 \
    --image-height 1082
```

**Common resolutions:**
- Default: `1592 x 2164` (2x the SVG)
- SVG native size: `796 x 1082`
- Small (preview): `398 x 541` (half the SVG)

Keep the 796:1082 ratio, otherwise the card is stretched.

### Border Around PNG/JPG Cards

`--png-vertical-margin` and `--png-horizontal-margin` (60 px each by default) add a border around every PNG/JPG card: the top and bottom use the card's own border colours, the sides use the `Margins.png` strip from the template. Set both to `0` to get the bare card.

### JPG Quality Control

Adjust the JPG compression quality (1-100, default 90):

```bash
python generate_cards_from_csv.py Updated_Cards.csv \
    --jpg-output ./output_jpg \
    --jpg-quality 95
```

**Quality recommendations:**
- `95-100`: Maximum quality (larger files)
- `85-90`: High quality (good balance)
- `75-80`: Medium quality (smaller files)
- `60-70`: Lower quality (very small files)

### Example: Preview PNGs

```bash
python generate_cards_from_csv.py Updated_Cards.csv \
    --png-output ./output_png_preview \
    --image-width 398 \
    --image-height 541
```

### Example: Print-Ready JPGs

```bash
python generate_cards_from_csv.py Updated_Cards.csv \
    --jpg-output ./output_jpg_print \
    --jpg-quality 95
```

## Output Information

When you run the script, it will display:
```
Generated 257 cards in .../output
Generated PNG cards (1592x2164, 400 DPI, top/bottom margin=60px, left/right margin=60px) in .../output_png
Generated JPG cards (1592x2164, quality=90) in .../output_jpg
```

Cards whose `path to image` is empty or points to a missing file are still generated, without illustration, and reported with a warning.

## Rendering Quality

The script uses multiple rendering engines in order of preference:

1. **Playwright (Chromium)** - Best font rendering; one browser is started and reused for every card
   ```bash
   pip install playwright
   python -m playwright install chromium
   ```

2. **Inkscape** - High-quality SVG rendering, requires Inkscape installation
   - Install from: https://inkscape.org/

3. **librsvg (rsvg-convert)** - Fast rendering, cross-platform
   ```bash
   # Windows: https://github.com/linuxmint/librsvg/releases
   # Or via package managers
   ```

4. **svglib + reportlab** - Python fallback; recent reportlab versions also need the Cairo library
   ```bash
   pip install svglib reportlab rlPyCairo
   ```

## File Naming Convention

All output files follow this naming pattern:
```
{NUMBER:03d}_{SLUG_NAME}.{FORMAT}
```

Examples:
- `001_Grimlock.png`
- `002_Manteleur.jpg`
- `003_Rats_Cr_nes.svg`

Where `{NUMBER}` is the card's row index in the CSV (001-257) and `{SLUG_NAME}` is the card name with each run of characters other than A-Z, a-z and 0-9 replaced by a single `_`.

## PNG vs JPG

### Use PNG when:
- ✅ You want maximum quality (lossless)
- ✅ File size is not a concern
- ✅ The images will be edited or resized again

### Use JPG when:
- ✅ You need smaller file sizes (about 6x smaller than PNG here)
- ✅ Distributing digitally

## Batch Processing

Create a Windows batch file `render_all.bat`:

```batch
@echo off
python generate_cards_from_csv.py Updated_Cards.csv ^
    --png-output ./output_png ^
    --jpg-output ./output_jpg ^
    --pdf-output ./cardsa4.pdf ^
    --jpg-quality 90

echo Done! Check the output directories.
pause
```

Then run it:
```bash
render_all.bat
```

## Troubleshooting

### "Warning: Could not generate PNG for [card name]"
No rendering engine could convert the card. Solution:
1. Install Playwright with Chromium (recommended):
   ```bash
   pip install playwright
   python -m playwright install chromium
   ```
2. Or install Inkscape or librsvg

### "Warning: Playwright could not start Edge, Chrome or Chromium"
Playwright is installed but no browser is available, so the fallback renderers are used. Run `python -m playwright install chromium`.

### "Warning: [card name]: image not found: ..."
The card's `path to image` does not exist. Paths are resolved relative to the CSV's folder, then to the repository root.

### JPG files are very large
- Reduce `--jpg-quality` value (e.g., 75-80)
- Reduce image dimensions (e.g., 796x1082 instead of the default 1592x2164)

### PNG files are large
- This is normal for high-resolution images
- Use JPG for smaller file sizes
- Or reduce dimensions

### Quality issues (blurry text)
- Increase `--image-width` and `--image-height`
- Make sure a proper rendering engine is installed (prefer Playwright/Inkscape)

## Storage Estimates

Measured for the 257 cards with the default settings:

| Format | Resolution | File Size | Total |
|--------|-----------|-----------|-------|
| SVG | 796x1082 (illustration and fonts embedded) | ~4 MB each | ~1 GB |
| PNG | 1712x2284 (with border) | ~2.6 MB each | ~680 MB |
| JPG | 1712x2284 (with border, q=90) | ~0.45 MB each | ~110 MB |
| PDF | A4, 71 pages (633 cards) | - | ~270 MB |

Rendering all 257 cards to PNG takes a few minutes with Playwright.

## Command Reference

```
usage: generate_cards_from_csv.py [-h] [--output-dir OUTPUT_DIR]
                                  [--pdf-output PDF_OUTPUT]
                                  [--pdf-brightness PDF_BRIGHTNESS]
                                  [--png-output PNG_OUTPUT]
                                  [--jpg-output JPG_OUTPUT]
                                  [--image-width IMAGE_WIDTH]
                                  [--image-height IMAGE_HEIGHT]
                                  [--jpg-quality JPG_QUALITY]
                                  [--png-dpi PNG_DPI]
                                  [--png-vertical-margin PNG_VERTICAL_MARGIN]
                                  [--png-horizontal-margin PNG_HORIZONTAL_MARGIN]
                                  csv_path

positional arguments:
  csv_path              CSV file with columns like
                        name,count,cost,vp1,vp2,set,benefit,type1,type2,path
                        to image

options:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR
                        Directory where SVG files will be created
  --pdf-output PDF_OUTPUT
                        If provided, generate an A4 PDF with all cards
                        (respecting count field)
  --pdf-brightness PDF_BRIGHTNESS
                        Brightness multiplier applied only to PDF
                        rasterization (1.0=unchanged, 1.1=brighter)
  --png-output PNG_OUTPUT
                        If provided, save individual PNG files in this
                        directory
  --jpg-output JPG_OUTPUT
                        If provided, save individual JPG files in this
                        directory
  --image-width IMAGE_WIDTH
                        Card width in pixels for PNG/JPG output, before
                        margins (default: 1592, i.e. 2x the SVG)
  --image-height IMAGE_HEIGHT
                        Card height in pixels for PNG/JPG output, before
                        margins (default: 2164, i.e. 2x the SVG)
  --jpg-quality JPG_QUALITY
                        Quality setting for JPG output (1-100, default: 90)
  --png-dpi PNG_DPI     DPI metadata for generated PNG files (default: 400)
  --png-vertical-margin PNG_VERTICAL_MARGIN
                        Extra margin in pixels added above and below PNG/JPG
                        outputs, in the card's top and bottom border colours
                        (default: 60)
  --png-horizontal-margin PNG_HORIZONTAL_MARGIN
                        Extra margin in pixels added left and right of PNG/JPG
                        outputs, filled with the Margins.png border strip
                        (default: 60)
```

## Next Steps

1. **Test with a small subset**: Run on a few cards to verify quality
2. **Choose your resolution**: Decide if you need full or preview resolution
3. **Batch processing**: Use the batch file for regular renders
4. **Distribution**: Share PNG/JPG versions with players

Enjoy your rendered cards! 🎴

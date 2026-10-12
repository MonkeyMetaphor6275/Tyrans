# PNG/JPG Rendering Guide

Your Tyrants card generation script now supports rendering SVG cards to PNG and JPG formats! This guide explains how to use these features.

## Overview

The script can now generate three output formats:
- **SVG**: Vector format (always generated)
- **PNG**: Raster format with full transparency support
- **JPG**: Raster format optimized for file size
- **PDF**: A4 printable format (existing feature)

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
This creates PNG files (796x1082px by default) in the `output_png/` directory.

### Generate JPG Cards
```bash
python generate_cards_from_csv.py Updated_Cards.csv --jpg-output ./output_jpg
```
This creates JPG files in the `output_jpg/` directory.

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

Change the output resolution for PNG/JPG:

```bash
python generate_cards_from_csv.py Updated_Cards.csv \
    --png-output ./output_png \
    --image-width 1192 \
    --image-height 1623
```

**Common resolutions:**
- Default: `796 x 1082` (0.67 scale of 1192 x 1623)
- Full resolution: `1192 x 1623` (same as SVG viewBox)
- Small (preview): `400 x 545` (half resolution)
- Mobile: `600 x 815`

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

### Example: High-Quality Preview PNGs

```bash
python generate_cards_from_csv.py Updated_Cards.csv \
    --png-output ./output_png_preview \
    --image-width 400 \
    --image-height 545
```

### Example: Print-Ready JPGs

```bash
python generate_cards_from_csv.py Updated_Cards.csv \
    --jpg-output ./output_jpg_print \
    --image-width 1192 \
    --image-height 1623 \
    --jpg-quality 95
```

## Output Information

When you run the script, it will display:
```
Generated 277 cards in c:\...\output
Generated PNG cards (796x1082) in c:\...\output_png
Generated JPG cards (796x1082, quality=90) in c:\...\output_jpg
```

## Rendering Quality

The script uses multiple rendering engines in order of preference:

1. **Playwright (Chromium)** - Best font rendering, requires browser installation
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

4. **svglib + reportlab** - Pure Python fallback (already installed)
   ```bash
   pip install svglib reportlab
   ```

## File Naming Convention

All output files follow this naming pattern:
```
{NUMBER:03d}_{SLUG_NAME}.{FORMAT}
```

Examples:
- `001_Grimlock.png`
- `002_Manteleur.jpg`
- `003_Rats_Cranes.svg`

Where `{NUMBER}` is the card index (001-277) and `{SLUG_NAME}` is the card name normalized to URL-safe format.

## PNG vs JPG

### Use PNG when:
- ✅ You need transparency
- ✅ You want maximum quality
- ✅ File size is not a concern
- ✅ Creating web previews
- ✅ Cards will be scaled down

### Use JPG when:
- ✅ You need smaller file sizes
- ✅ Distributing digitally
- ✅ You don't need transparency
- ✅ File size matters (typically 60-70% smaller than PNG)

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
This means no rendering engine is available. Solution:
1. Try installing Playwright with Chromium (recommended):
   ```bash
   pip install playwright
   python -m playwright install chromium
   ```
2. Or install Inkscape or librsvg

### JPG files are very large
- Reduce `--jpg-quality` value (e.g., 75-80)
- Reduce image dimensions (e.g., 400x545 instead of 796x1082)

### PNG files are large
- This is normal for high-resolution images
- Use JPG for smaller file sizes
- Or reduce dimensions

### Quality issues (blurry text)
- Increase `--image-width` and `--image-height`
- Make sure a proper rendering engine is installed (prefer Playwright/Inkscape)

## Storage Estimates

For all 277 cards:

| Format | Resolution | File Size | Total |
|--------|-----------|-----------|-------|
| SVG | - | ~30-50 KB each | ~10-15 MB |
| PNG | 400x545 | ~80-150 KB each | ~22-41 MB |
| PNG | 796x1082 | ~300-500 KB each | ~83-138 MB |
| JPG | 796x1082 (q=90) | ~100-150 KB each | ~28-41 MB |
| JPG | 796x1082 (q=75) | ~60-100 KB each | ~17-28 MB |
| PDF | A4 print | - | ~8-12 MB |

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
                                  csv_path

positional arguments:
  csv_path              CSV file with card data

optional arguments:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR
                        Directory where SVG files will be created
                        (default: ./output)
  --pdf-output PDF_OUTPUT
                        If provided, generate an A4 PDF
  --pdf-brightness PDF_BRIGHTNESS
                        Brightness multiplier for PDF (default: 1.0)
  --png-output PNG_OUTPUT
                        If provided, save PNG files in this directory
  --jpg-output JPG_OUTPUT
                        If provided, save JPG files in this directory
  --image-width IMAGE_WIDTH
                        Width in pixels for PNG/JPG (default: 796)
  --image-height IMAGE_HEIGHT
                        Height in pixels for PNG/JPG (default: 1082)
  --jpg-quality JPG_QUALITY
                        Quality for JPG (1-100, default: 90)
```

## Next Steps

1. **Test with a small subset**: Run on a few cards to verify quality
2. **Choose your resolution**: Decide if you need full or preview resolution
3. **Batch processing**: Use the batch file for regular renders
4. **Distribution**: Share PNG/JPG versions with players

Enjoy your rendered cards! 🎴

# Tyrans card pipeline

Generates cards for *Tyrants of the Underdark* from a single CSV file, in French or English: SVG cards, PNG/JPG images and A4 print sheets. The card illustrations were generated with OpenAI's `gpt-image-1`, and the scripts used for that are included.

> **Disclaimer:** unofficial fan content. *Tyrants of the Underdark*, *Dungeons & Dragons* and all related names and card texts are the property of Wizards of the Coast and Gale Force Nine. This project is not affiliated with, endorsed, sponsored or approved by Wizards of the Coast or Gale Force Nine.

## Repository layout

| Path | Content |
|------|---------|
| `Updated_Cards.csv` | Source of truth for card content, in French (one row per card) |
| `Updated_Cards_en.csv` | The same cards in English, with English column names and the official game vocabulary |
| `generate_cards_from_csv.py` | Card generator (SVG, PNG, JPG, PDF) |
| `art_pipeline/` | OpenAI illustration generator, prompt list and dark-image fixer |
| `ressources/card_assets/` | Card template, icons, set logos and fonts |
| `ressources/generated_images/card_illustrations/` | Card illustrations |
| `build_git_tracked_zip.py` | Zips the Git-tracked files |
| `PNG_JPG_RENDERING_GUIDE.md` | Details on PNG/JPG output options |

All commands below run from the repository root.

## Installation

```bash
pip install -r requirements.txt
```

Install Chromium for Playwright (best SVG-to-PNG rendering, with correct fonts):

```bash
python -m playwright install chromium
```

If Playwright is unavailable, the generator falls back to other SVG renderers:
- Inkscape: https://inkscape.org/
- librsvg (`rsvg-convert`): https://librsvg.2f30.org/ or via a package manager (apt, brew…)
- svglib (installed by `requirements.txt`): recent reportlab versions also need the Cairo library (`pip install rlPyCairo`)

## Generating cards

```bash
# SVGs only, into the default output/ folder
python generate_cards_from_csv.py Updated_Cards.csv

# English cards: same options, English CSV
python generate_cards_from_csv.py Updated_Cards_en.csv --output-dir output/en

# SVGs + A4 print PDF (3×3 grid per page, each card repeated "Nombre" / "count" times)
python generate_cards_from_csv.py Updated_Cards.csv --pdf-output output/cardsa4.pdf

# Optional: brighten the PDF raster slightly (1.0 = unchanged)
python generate_cards_from_csv.py Updated_Cards.csv --pdf-output output/cardsa4.pdf --pdf-brightness 1.1

# Individual PNG files with extra print margins (two size variants)
python generate_cards_from_csv.py Updated_Cards.csv --png-output output/.pdf_temp --image-width 800 --image-height 1125 --png-vertical-margin 30 --png-horizontal-margin 20
python generate_cards_from_csv.py Updated_Cards.csv --png-output output/.pdf_temp --image-width 800 --image-height 1087 --png-vertical-margin 30 --png-horizontal-margin 58
```

See [PNG_JPG_RENDERING_GUIDE.md](PNG_JPG_RENDERING_GUIDE.md) for all PNG/JPG options.

## Generating illustrations (OpenAI)

`art_pipeline/generate_batch_openai.py` generates the next batch of illustrations with `gpt-image-1`. It reads prompts from `art_pipeline/card_prompts_fandom_all.csv`, skips cards that already have an image path in `Updated_Cards.csv`, saves PNGs to `ressources/generated_images/card_illustrations/` and writes the paths back to the CSV after each card.

The API key is read from the `OPENAI_API_KEY` environment variable, or else from `art_pipeline/openai_key` (plain text, single line; this file is gitignored).

```bash
# Next 20 cards
python art_pipeline/generate_batch_openai.py

# Dry-run: print what would be generated, without calling the API (no key needed)
python art_pipeline/generate_batch_openai.py --dry-run

# Custom batch size
python art_pipeline/generate_batch_openai.py --batch-size 10

# Work from the English CSV instead
python art_pipeline/generate_batch_openai.py --cards-csv Updated_Cards_en.csv
```

## Brightening dark illustrations

`art_pipeline/fix_dark_illustrations.py` detects illustrations that are too dark for print and can brighten them. By default it is a dry-run that only writes a CSV report.

```bash
# Dry-run: report dark images, no files written
python art_pipeline/fix_dark_illustrations.py

# Apply brightening, output to ressources/generated_images/card_illustrations_brightened/
python art_pipeline/fix_dark_illustrations.py --apply

# Apply in place (originals are backed up first)
python art_pipeline/fix_dark_illustrations.py --apply --in-place --backup-dir ressources/generated_images/card_illustrations_dark_backup

# Tune thresholds / brightness target (defaults shown)
python art_pipeline/fix_dark_illustrations.py --apply \
  --mean-threshold 108 --median-threshold 98 --p90-threshold 176 \
  --target-mean 132 --max-brightness-factor 1.30

# Custom input / output dirs
python art_pipeline/fix_dark_illustrations.py --apply \
  --input-dir ressources/generated_images/card_illustrations \
  --output-dir ressources/generated_images/card_illustrations_brightened \
  --report-csv art_pipeline/dark_illustrations_report.csv
```

## Zipping the repository

`build_git_tracked_zip.py` builds a ZIP of all Git-tracked files, excluding any path matching the current `.gitignore` rules.

```bash
# Default output: output/git_tracked_files.zip
python build_git_tracked_zip.py

# Custom output path
python build_git_tracked_zip.py --output output/repo_snapshot.zip

# Another repository
python build_git_tracked_zip.py --repo path/to/other/repo --output output/repo_snapshot.zip
```

## Licence

The code and the project's own data are released under the [MIT licence](LICENSE). This does not cover third-party material, which remains the property of its owners: the game's names, rules and card texts (Wizards of the Coast / Gale Force Nine), and the card template, icons and fonts in `ressources/card_assets/template/`, which come from a community card-making kit.

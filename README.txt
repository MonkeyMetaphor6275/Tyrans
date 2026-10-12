===============================================================
  TYRANS CARD PIPELINE - COMMAND REFERENCE
===============================================================

── SETUP ──────────────────────────────────────────────────────

# Navigate to project root (all commands below run from there)
cd path/to/Tyrans


── INSTALLATION ───────────────────────────────────────────────

# Install all required Python packages from requirements.txt
pip install -r requirements.txt

# Install Chromium browser for Playwright (used for best SVG-to-PNG rendering with proper font support)
python -m playwright install chromium

# Optional: If Playwright is unavailable, install system SVG renderers as fallback:
#   - Inkscape: https://inkscape.org/
#   - librsvg (rsvg-convert): https://librsvg.2f30.org/ or via package manager (e.g., apt, brew)
#   - svglib (Python library): already included in requirements.txt

# For AI image generation via OpenAI (art_pipeline), also ensure:
#   - requests package: included in requirements.txt (the script calls the OpenAI REST API directly)
#   - API key file: place your key in art_pipeline/openai_key (plain text, single line)


── EXECUTION ──────────────────────────────────────────────────

── generate_cards_from_csv.py ─────────────────────────────────
# Generate SVGs only from Updated_Cards.csv into the default output/ folder
python generate_cards_from_csv.py Updated_Cards.csv

# Generate SVGs + A4 print PDF (3×3 grid per page)
python generate_cards_from_csv.py Updated_Cards.csv --pdf-output output/cardsa4.pdf

# Optional: brighten the PDF raster slightly (1.0 = unchanged)
python generate_cards_from_csv.py Updated_Cards.csv --pdf-output output/cardsa4.pdf --pdf-brightness 1.1

# Individual PNG files with extra print margins (two size variants)
python generate_cards_from_csv.py Updated_Cards.csv --png-output output/.pdf_temp --image-width 800 --image-height 1125 --png-vertical-margin 30 --png-horizontal-margin 20
python generate_cards_from_csv.py Updated_Cards.csv --png-output output/.pdf_temp --image-width 800 --image-height 1087 --png-vertical-margin 30 --png-horizontal-margin 58
 

── art_pipeline/generate_batch_openai.py ──────────────────────
# Generate the next 20 card illustrations via OpenAI gpt-image-1.
# Reads prompts from art_pipeline/card_prompts_fandom_all.csv,
# skips cards that already have an image path in Updated_Cards.csv,
# saves PNGs to ressources/generated_images/card_illustrations/ and writes paths back to CSV.
# API key must be stored as plain text in art_pipeline/openai_key.
python art_pipeline/generate_batch_openai.py

# Dry-run: print what would be generated without calling the API
python art_pipeline/generate_batch_openai.py --dry-run

# Custom batch size
python art_pipeline/generate_batch_openai.py --batch-size 10


── art_pipeline/fix_dark_illustrations.py ─────────────────────
# Detect and (optionally) brighten dark illustrations for print.
# By default runs as a dry-run and only writes a CSV report.

# Dry-run: report dark images, no files written
python art_pipeline/fix_dark_illustrations.py

# Apply brightening → output to ressources/generated_images/card_illustrations_brightened/
python art_pipeline/fix_dark_illustrations.py --apply

# Apply in-place (overwrites originals, backs up originals first)
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


── build_git_tracked_zip.py ───────────────────────────────────
# Build a ZIP archive from all files tracked by Git,
# while excluding any path matching current .gitignore rules.
# Default output: output/git_tracked_files.zip
python build_git_tracked_zip.py

# Custom output path
python build_git_tracked_zip.py --output output/repo_snapshot.zip

# Optional: run against another repository path
python build_git_tracked_zip.py --repo path/to/other/repo --output output/repo_snapshot.zip

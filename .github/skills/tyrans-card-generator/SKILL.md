---
name: tyrans-card-generator
description: 'Tyrants card pipeline for CSV-driven generation. Use when editing Updated_Cards.csv, setting image paths, generating card art, tuning artwork placement in build_artwork, regenerating SVG cards, and producing A4 print PDFs.'
argument-hint: 'Describe the card-data edit, image workflow, or render issue to handle'
---

# Tyrans Card Generator

## Use This Skill For
- Updating card data in `Updated_Cards.csv`
- Setting `path to image` for cards
- Tuning artwork fit/alignment in `generate_cards_from_csv.py`
- Running full card regeneration and checking output
- Generating A4 print PDFs (3x3 cards per page) from CSV counts
- Generating or refining prompt descriptions for card art
- Updating the Fandom-backed prompt dataset
- Building a repository snapshot ZIP from Git-tracked files while excluding `.gitignore` matches

## Key Files
- `Updated_Cards.csv`: Source of truth for card content (French)
- `Updated_Cards_en.csv`: The same cards in English (same row order, English column names)
- `generate_cards_from_csv.py`: Main SVG generator
- `build_git_tracked_zip.py`: Creates `output/git_tracked_files.zip` from Git-tracked files, filtered by `.gitignore`
- `ressources/generated_images/card_illustrations/`: Card illustrations referenced by `path to image`
- `output/`: Default card SVG output directory
- `art_pipeline/generate_batch_openai.py`: OpenAI card-art generator
- `art_pipeline/fix_dark_illustrations.py`: Detects and brightens dark illustrations for print
- `art_pipeline/card_prompts_fandom_all.csv`: Fandom-backed prompt per card (title/type first, 80-word max)

## Current Artwork Behavior
In `build_svg`:
- The illustration box takes x, y and width from `IMAGE_BOX`; its height is computed per card from the estimated text height (more text, shorter image), clamped between `IMAGE_MIN_HEIGHT` and `IMAGE_MAX_HEIGHT`
- The separator is centred on the image's bottom edge and the text box starts just below it

In `build_artwork`:
- Draws the image with `preserveAspectRatio="xMidYMid slice"` inside a clip path: it fills the box and is cropped around its centre, never stretched

If artwork is cropped too much or too little, adjust `IMAGE_MIN_HEIGHT` / `IMAGE_MAX_HEIGHT` or the text-height estimate in `estimate_text_area_height`.

## Current IMAGE_BOX
- Defined in `generate_cards_from_csv.py` as:
- `IMAGE_BOX = (60, 172, 678, 550)` (the height is replaced by the per-card value above)

## CSV Override Columns (Current)
When override columns are non-empty, they are prioritized over base values:
- `Coût Modif` / `cost override` overrides `Coût` / `cost`
- `PV deck Modif` / `deck vp override` overrides `Point de victoire deck` / `deck vp`
- `PV cénacle modif` / `inner circle vp override` overrides `Point de victoire cénacle` / `inner circle vp`
- `Texte modif` / `text override` overrides `Texte` / `text`

## English CSV
`Updated_Cards_en.csv` mirrors `Updated_Cards.csv` row for row; when a card changes in one, update the other. Columns: `name, set, type1, type2, count, print count, cost, deck vp, inner circle vp, text, flavor text, card numbers, proposed change, cost override, deck vp override, inner circle vp override, text override, path to image` (no `Nom`).

Use the official rulebook vocabulary:
- Aspects (`type1`): Ambition, Conquête → Conquest, Malice, Ruse → Guile, Obéissance → Obedience
- Resources: `N attaque(s)` → `N Power`, `N monnaie(s)` → `N Influence` (both become inline icons, so keep the number in front)
- Actions: Déployez une unité → Deploy a troop; Assassinez → Assassinate; Supplantez → Supplant; Posez/Placez/Déployez un espion → Place a spy; Renvoyez un de vos espions ► → Return one of your spies ►; Dévorez → Devour; Promouvez → Promote; Recrutez → Recruit; Déplacez → Move; Piochez → Draw
- Places: cénacle → inner circle; salle des trophées → trophy hall; défausse → discard pile; pioche → deck; réserve → supply; garnison → barracks; marché → market; unité blanche → white troop; contrôle total → total control; n'importe où sur le plateau → anywhere on the board
- Phrases: Choisissez entre : → Choose one:; À la fin du tour, promouvez une autre carte jouée ce tour-ci → At end of turn, promote another card played this turn; Focus de Malice ► → Focus Malice ►
- Cards and fan-set terms: Paria dément → Insane Outcast; Sbire empoisonné → Poisoned Minion; Toile → Web (Spiderkin); Fléau → Scourge, site Touché par le Fléau → Scourge-touched site, Cœur du Fléau → Heart of the Scourge, jeton Fléau → Scourge token (Juiblex); carte persistante / zone de jeu → persisting card / play area (Kuo-Toa)
- Keep the French text's structure: same `•` bullets, `►` arrows and line breaks; avoid ` - ` after "Choose …:" (it would be turned into a bullet)

## Image Paths In CSV
`path to image` holds a repo-relative path with forward slashes, normally written by `art_pipeline/generate_batch_openai.py` as:
- `ressources/generated_images/card_illustrations/<english_name>.png`

The generator resolves it relative to the CSV's folder, then to the repository root, and prints a warning for every card whose image is missing.

Rules:
- Do not overwrite existing non-empty `path to image` unless requested
- Keep UTF-8 with BOM for CSV reads/writes (`encoding="utf-8-sig"`)

## Generate Cards
Run from repo root:
```bash
python generate_cards_from_csv.py Updated_Cards.csv
```

## Generate A4 Print PDF (Current)
The generator can also produce a print-ready A4 PDF:
- Card physical size: `2.5 x 3.5` inches
- Layout: `3 x 3` cards per page (`9` cards/page)
- Repetition: each card appears `count` times from CSV

Run:
```bash
python generate_cards_from_csv.py Updated_Cards.csv --pdf-output output/cards_a4.pdf
```

Renderer behavior (important):
- Preferred rasterizer is browser-based Playwright (best match with VS Code/Firefox SVG rendering); one browser is started on first use and reused for every card (`BrowserRenderer`)
- Fallbacks are `inkscape`, then `rsvg-convert`, then `svglib` (which needs the Cairo library with recent reportlab versions); a warning is printed when the browser cannot start
- Current raster DPI is `300`

If Inkscape output looks wrong while browser output is correct:
- Root cause is often limited support for embedded data-URI `@font-face` rules in Inkscape
- Use Playwright renderer path for faithful text/layout rendering

## CSV Editing Notes
- Prefer programmatic CSV updates (`csv.DictReader`/`csv.DictWriter`, `encoding="utf-8-sig"`) over manual patching for multiline fields.
- Avoid line-based patch edits on multiline CSV text blocks; they can duplicate or corrupt rows when quoting/newlines are present.
- After updates, validate row count and filled flavor count with a small script before continuing.

## Validation Checklist
- Script runs without syntax/runtime errors
- Output card count matches expected rows
- Artwork visually aligned in frame after any `build_artwork` change
- CSV integrity preserved (header/order/encoding)

## Git Snapshot ZIP Workflow
When the user asks for a portable repository archive that follows Git rules:
1. Run `build_git_tracked_zip.py` from the repository root
2. Keep default output unless a custom output path is requested
3. The script includes files from `git ls-files` and excludes paths matching `.gitignore` via `git check-ignore --no-index`

Run:
```bash
python build_git_tracked_zip.py
```

Custom output:
```bash
python build_git_tracked_zip.py --output output/repo_snapshot.zip
```

## Local Illustration Prompt Workflow
When generating card-art prompts from the CSV:
1. Use `art_pipeline/card_prompts_fandom_all.csv` as the prompt source
2. Keep prompts compact: title first, type first, then ambiance/details, then style keywords
3. Keep each prompt at 80 words or less
4. If a Fandom page match is noisy or ambiguous, fall back to a short name-based prompt instead of forcing a bad page

## OpenAI Image Generation Workflow (Current)
- Primary generator: `art_pipeline/generate_batch_openai.py`
- Model: `gpt-image-1`
- Current image size: `1536x1024` (closest supported size to the requested 4:3 look)
- Current quality: `medium`
- Prompt source: `art_pipeline/card_prompts_fandom_all.csv`
- Batch behavior: reads `Updated_Cards.csv`, skips rows where `path to image` is already filled, generates only pending cards, writes back image paths
- The CSV and the log are saved after every card, so an interrupted batch keeps the images already generated
- API key: `OPENAI_API_KEY` environment variable, or else `art_pipeline/openai_key` (gitignored); `--dry-run` needs no key
- Output directory: `ressources/generated_images/card_illustrations/`
- Log file: `ressources/generated_images/card_illustrations/generation_log.json`

Run:
```bash
python art_pipeline/generate_batch_openai.py --batch-size 20
```

## Prompt Style Guidance (Current)
- To avoid overly dark outputs, prefer:
- `Fantasy ambiance, dramatic composition, luminous cinematic lighting, rich textures, vibrant colors, strong contrast, high-detail digital art, ultra-detailed, full-bleed illustration, no text, no border.`
- Avoid explicit darkening keywords such as:
- `Dark fantasy ambiance`, `Underdark mood`, and excessive darkness cues in the descriptive sentence.
- Keep creature/type disambiguation clear near the start of the prompt; avoid ambiguous placement of set labels in natural-language prompt text.

## 400 Bad Request Troubleshooting For OpenAI Images
If `generate_batch_openai.py` shows `FAILED : 400 Bad Request: <message>`, read the message (it is also stored in `generation_log.json`):
- many 400s are moderation rejections mentioning `safety_violations=[sexual]`.
- Do not assume it is encoding or size first.

Field-tested fix pattern:
1. Identify the exact failing card name in `generation_log.json`.
2. Read its prompt in `art_pipeline/card_prompts_fandom_all.csv`.
3. Remove or neutralize sexualized phrasing (for example: `nude`, `stunningly beautiful`, `perfect figure`, seductive framing).
4. Rewrite toward neutral monster language (for example: horned fiend, armored demon, intimidating pose).
5. Re-test that one prompt directly via API before resuming full batches.

Notes:
- This issue can affect isolated cards while most other cards in the same batch succeed.
- Character encoding/apostrophes were not the root cause in the recent failures (`Succubus`, `Blibdoolpoolp Priest`); moderation category was the blocker.

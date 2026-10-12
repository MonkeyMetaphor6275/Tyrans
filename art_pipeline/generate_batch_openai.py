"""
Batch OpenAI image generator for Tyrans card illustrations.

Usage:
    python art_pipeline/generate_batch_openai.py

Each run generates the next BATCH_SIZE cards that have no image path yet in
Updated_Cards.csv, saves PNGs to ressources/generated_images/card_illustrations/, and writes
the new paths back to the CSV.

Run again after inspecting images to generate the next batch.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import time
from pathlib import Path

import requests

# ── Configuration ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
KEY_FILE = ROOT / "art_pipeline/openai_key"
PROMPTS_CSV = ROOT / "art_pipeline/card_prompts_fandom_all.csv"
CARDS_CSV = ROOT / "Updated_Cards.csv"
OUT_DIR = ROOT / "ressources/generated_images/card_illustrations"
LOG_FILE = ROOT / "ressources/generated_images/card_illustrations/generation_log.json"

API_URL = "https://api.openai.com/v1/images/generations"
MODEL = "gpt-image-1"
IMAGE_SIZE = "1536x1024"  # Wider than 4:3, closest available to that ratio
IMAGE_QUALITY = "medium"
BATCH_SIZE = 20
PAUSE_BETWEEN_REQUESTS = 2  # seconds, to stay within rate limits
# ──────────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate next batch of card illustrations via OpenAI.")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Number of images to generate this run.")
    parser.add_argument("--key-file", default=str(KEY_FILE), help="Path to file containing the OpenAI API key.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned prompts without generating.")
    return parser.parse_args()


def read_csv(path: Path) -> tuple[list[dict], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or rows[0].keys())
    return rows, fieldnames


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def safe_filename(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "").replace("/", "_")


def load_log() -> list[dict]:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return []


def save_log(entries: list[dict]) -> None:
    LOG_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_image(prompt: str, headers: dict) -> bytes:
    body = {
        "model": MODEL,
        "prompt": prompt,
        "n": 1,
        "size": IMAGE_SIZE,
        "quality": IMAGE_QUALITY,
    }
    r = requests.post(API_URL, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    img_data = r.json().get("data", [{}])[0]
    if img_data.get("b64_json"):
        return base64.b64decode(img_data["b64_json"])
    if img_data.get("url"):
        img_r = requests.get(img_data["url"], timeout=120)
        img_r.raise_for_status()
        return img_r.content
    raise RuntimeError(f"No image data in response: {list(img_data.keys())}")


def main() -> None:
    args = parse_args()

    api_key = Path(args.key_file).read_text().strip()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build lookup of already-done card names from CSV (has non-empty path to image)
    cards_rows, cards_fieldnames = read_csv(CARDS_CSV)
    done_names = {
        row["name"]
        for row in cards_rows
        if (row.get("path to image") or "").strip()
    }
    print(f"Cards already with images: {len(done_names)}")

    # Build lookup from prompts CSV
    prompt_rows, _ = read_csv(PROMPTS_CSV)
    prompt_map = {row["name"]: row["prompt"] for row in prompt_rows if row.get("name")}

    # Select next batch: cards in CSV order that have no image yet AND have a prompt
    pending = [
        row for row in cards_rows
        if row.get("name") and row["name"] not in done_names and row["name"] in prompt_map
    ]

    batch = pending[: args.batch_size]

    if not batch:
        print("No pending cards — all cards already have images.")
        return

    print(f"Pending cards: {len(pending)} | Generating this batch: {len(batch)}")
    if args.dry_run:
        for i, row in enumerate(batch, start=1):
            name = row["name"]
            print(f"  [{i}/{len(batch)}] {name}: {prompt_map[name][:100]}...")
        return

    log = load_log()
    name_to_row = {row["name"]: row for row in cards_rows}
    generated = 0
    failed = 0

    for i, row in enumerate(batch, start=1):
        name = row["name"]
        prompt = prompt_map[name]
        out_path = OUT_DIR / f"{safe_filename(name)}.png"

        print(f"\n[{i}/{len(batch)}] {name}")
        print(f"  Prompt: {prompt[:110]}...")

        try:
            img_bytes = generate_image(prompt, headers)
            out_path.write_bytes(img_bytes)
            rel_path = out_path.relative_to(ROOT).as_posix()
            name_to_row[name]["path to image"] = str(out_path.relative_to(ROOT))
            log.append({"name": name, "file": rel_path, "status": "ok"})
            print(f"  Saved  -> {rel_path}")
            generated += 1
        except Exception as exc:
            print(f"  FAILED : {exc}")
            log.append({"name": name, "status": "error", "error": str(exc)})
            failed += 1

        if i < len(batch):
            time.sleep(PAUSE_BETWEEN_REQUESTS)

    # Write updated CSV
    write_csv(CARDS_CSV, list(name_to_row.values()), cards_fieldnames)
    save_log(log)

    print(f"\n{'='*60}")
    print(f"Batch complete: {generated} generated, {failed} failed")
    print(f"Images saved to : {OUT_DIR}")
    print(f"CSV updated     : {CARDS_CSV.name}")
    print(f"Log             : {LOG_FILE}")
    print(f"{'='*60}")
    remaining = len(pending) - len(batch)
    if remaining > 0:
        print(f"Remaining cards without images: {remaining} — run again for next batch.")


if __name__ == "__main__":
    main()

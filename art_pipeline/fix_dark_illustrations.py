from __future__ import annotations

import argparse
import csv
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageStat

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass
class ImageMetrics:
    mean: float
    median: int
    p90: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect overly dark illustrations and brighten them adaptively for print. "
            "By default this runs as dry-run and only writes a report."
        )
    )
    parser.add_argument(
        "--input-dir",
        default="ressources/generated_images/card_illustrations",
        help="Directory containing illustration images.",
    )
    parser.add_argument(
        "--output-dir",
        default="ressources/generated_images/card_illustrations_brightened",
        help="Destination directory when not using --in-place.",
    )
    parser.add_argument(
        "--report-csv",
        default="art_pipeline/dark_illustrations_report.csv",
        help="CSV report path.",
    )
    parser.add_argument(
        "--mean-threshold",
        type=float,
        default=108.0,
        help="Flag candidate when grayscale mean is below this value.",
    )
    parser.add_argument(
        "--median-threshold",
        type=float,
        default=98.0,
        help="Flag candidate when grayscale median is below this value.",
    )
    parser.add_argument(
        "--p90-threshold",
        type=float,
        default=176.0,
        help="Flag candidate when 90th percentile is below this value.",
    )
    parser.add_argument(
        "--hard-mean-threshold",
        type=float,
        default=86.0,
        help="Always flag as dark when mean is below this value.",
    )
    parser.add_argument(
        "--min-fail-count",
        type=int,
        default=2,
        help="Number of failed soft thresholds required to classify as dark.",
    )
    parser.add_argument(
        "--target-mean",
        type=float,
        default=132.0,
        help="Target grayscale mean used for adaptive brightening.",
    )
    parser.add_argument(
        "--max-brightness-factor",
        type=float,
        default=1.30,
        help="Upper bound for final brightness enhancement factor.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write corrected images (otherwise dry-run).",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite original files in input-dir (recommended with --backup-dir).",
    )
    parser.add_argument(
        "--backup-dir",
        default="ressources/generated_images/card_illustrations_dark_backup",
        help="Backup directory used with --in-place.",
    )
    return parser.parse_args()


def list_images(folder: Path) -> list[Path]:
    files: list[Path] = []
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return sorted(files)


def percentile_from_histogram(hist: list[int], percentile: float) -> int:
    total = sum(hist)
    if total == 0:
        return 0
    target = total * percentile
    cumulative = 0
    for value, count in enumerate(hist):
        cumulative += count
        if cumulative >= target:
            return value
    return 255


def compute_metrics(image: Image.Image) -> ImageMetrics:
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    hist = gray.histogram()
    return ImageMetrics(
        mean=stat.mean[0],
        median=percentile_from_histogram(hist, 0.50),
        p90=percentile_from_histogram(hist, 0.90),
    )


def classify_dark(metrics: ImageMetrics, args: argparse.Namespace) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if metrics.mean < args.mean_threshold:
        failures.append("mean")
    if metrics.median < args.median_threshold:
        failures.append("median")
    if metrics.p90 < args.p90_threshold:
        failures.append("p90")

    if metrics.mean < args.hard_mean_threshold:
        return True, failures + ["hard_mean"]
    return len(failures) >= args.min_fail_count, failures


def gamma_correct(image: Image.Image, gamma: float) -> Image.Image:
    if abs(gamma - 1.0) < 1e-6:
        return image
    lut = [int(max(0, min(255, round(((i / 255.0) ** gamma) * 255.0)))) for i in range(256)]
    if image.mode in {"RGBA", "LA"}:
        base = image.convert("RGBA")
        rgb = base.convert("RGB").point(lut * 3)
        r, g, b = rgb.split()
        _, _, _, alpha = base.split()
        return Image.merge("RGBA", (r, g, b, alpha))
    if image.mode == "RGB":
        return image.point(lut * 3)
    if image.mode == "L":
        return image.point(lut)
    return image.convert("RGB").point(lut * 3)


def brighten_image(image: Image.Image, metrics: ImageMetrics, args: argparse.Namespace) -> tuple[Image.Image, float, float]:
    mean = max(metrics.mean, 1.0)
    mean_norm = max(1.0 / 255.0, min(mean / 255.0, 0.9999))
    target_norm = max(1.0 / 255.0, min(args.target_mean / 255.0, 0.9999))

    # Gamma < 1 lifts shadows and midtones without clipping highlights too aggressively.
    gamma = math.log(target_norm) / math.log(mean_norm)
    gamma = max(0.78, min(0.98, gamma))

    corrected = gamma_correct(image, gamma)
    post_gamma_metrics = compute_metrics(corrected)

    brightness_factor = args.target_mean / max(post_gamma_metrics.mean, 1.0)
    brightness_factor = max(1.0, min(args.max_brightness_factor, brightness_factor))

    if abs(brightness_factor - 1.0) > 1e-6:
        corrected = ImageEnhance.Brightness(corrected).enhance(brightness_factor)

    return corrected, gamma, brightness_factor


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    report_csv = Path(args.report_csv).expanduser().resolve()
    backup_dir = Path(args.backup_dir).expanduser().resolve()

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    image_paths = list_images(input_dir)
    if not image_paths:
        print(f"No images found in: {input_dir}")
        return

    if args.apply and (not args.in_place):
        output_dir.mkdir(parents=True, exist_ok=True)

    if args.apply and args.in_place:
        backup_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    dark_count = 0
    changed_count = 0

    for image_path in image_paths:
        with Image.open(image_path) as img:
            metrics = compute_metrics(img)
            is_dark, reasons = classify_dark(metrics, args)

            row: dict[str, str] = {
                "file": str(image_path.relative_to(input_dir)).replace("\\", "/"),
                "mean": f"{metrics.mean:.2f}",
                "median": str(metrics.median),
                "p90": str(metrics.p90),
                "is_dark": "yes" if is_dark else "no",
                "reasons": ",".join(reasons),
                "gamma": "",
                "brightness_factor": "",
                "output": "",
            }

            if not is_dark:
                rows.append(row)
                continue

            dark_count += 1

            corrected, gamma, brightness_factor = brighten_image(img, metrics, args)
            row["gamma"] = f"{gamma:.4f}"
            row["brightness_factor"] = f"{brightness_factor:.4f}"

            if args.apply:
                if args.in_place:
                    rel = image_path.relative_to(input_dir)
                    backup_path = backup_dir / rel
                    ensure_parent(backup_path)
                    if not backup_path.exists():
                        shutil.copy2(image_path, backup_path)
                    target_path = image_path
                else:
                    rel = image_path.relative_to(input_dir)
                    target_path = output_dir / rel
                    ensure_parent(target_path)

                save_kwargs = {}
                if target_path.suffix.lower() in {".jpg", ".jpeg"}:
                    save_kwargs = {"quality": 95}

                corrected.save(target_path, **save_kwargs)
                row["output"] = str(target_path)
                changed_count += 1

            rows.append(row)

    ensure_parent(report_csv)
    with report_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "mean",
                "median",
                "p90",
                "is_dark",
                "reasons",
                "gamma",
                "brightness_factor",
                "output",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("=" * 72)
    print(f"Analysed images : {len(image_paths)}")
    print(f"Dark images     : {dark_count}")
    if args.apply:
        print(f"Brightened      : {changed_count}")
        if args.in_place:
            print(f"Backup folder   : {backup_dir}")
        else:
            print(f"Output folder   : {output_dir}")
    else:
        print("Apply mode      : dry-run (no files modified)")
    print(f"Report CSV      : {report_csv}")
    print("=" * 72)


if __name__ == "__main__":
    main()

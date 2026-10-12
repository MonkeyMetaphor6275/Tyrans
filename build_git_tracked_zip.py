#!/usr/bin/env python3
"""Create a ZIP archive containing all files tracked by Git."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a ZIP archive from all files tracked by Git."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the Git repository (default: current directory).",
    )
    parser.add_argument(
        "--output",
        default="output/git_tracked_files.zip",
        help="Output ZIP file path (default: output/git_tracked_files.zip).",
    )
    return parser.parse_args()


def run_checked(cmd: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def get_git_tracked_files(repo_root: Path) -> list[Path]:
    result = run_checked(["git", "-C", str(repo_root), "ls-files", "-z"])
    files: list[Path] = []

    for raw in result.stdout.split(b"\x00"):
        if not raw:
            continue
        rel_path = Path(raw.decode("utf-8", errors="surrogateescape"))
        abs_path = repo_root / rel_path
        if abs_path.is_file():
            files.append(rel_path)

    files.sort()
    return files


def get_git_ignored_paths(repo_root: Path, paths: list[Path]) -> set[Path]:
    if not paths:
        return set()

    input_data = b"\x00".join(
        p.as_posix().encode("utf-8", errors="surrogateescape") for p in paths
    ) + b"\x00"

    # --no-index makes check-ignore evaluate patterns even for tracked files.
    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "--no-index", "-z", "--stdin"],
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=result.args,
            output=result.stdout,
            stderr=result.stderr,
        )

    ignored: set[Path] = set()
    for raw in result.stdout.split(b"\x00"):
        if not raw:
            continue
        ignored.add(Path(raw.decode("utf-8", errors="surrogateescape")))
    return ignored


def build_zip(repo_root: Path, output_file: Path) -> tuple[int, int]:
    tracked_files = get_git_tracked_files(repo_root)
    if not tracked_files:
        raise RuntimeError("No Git-tracked files found.")

    ignored_paths = get_git_ignored_paths(repo_root, tracked_files)
    included_files = [p for p in tracked_files if p not in ignored_paths]
    if not included_files:
        raise RuntimeError("All tracked files are excluded by gitignore rules.")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with ZipFile(output_file, mode="w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for rel_path in included_files:
            abs_path = repo_root / rel_path
            archive.write(abs_path, arcname=rel_path.as_posix())
            count += 1

    return count, output_file.stat().st_size


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo).resolve()
    output_file = Path(args.output).resolve()

    try:
        run_checked(["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"])
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.decode("utf-8", errors="replace").strip()
        print(f"Error: '{repo_root}' is not a Git repository. {message}", file=sys.stderr)
        return 2

    try:
        file_count, size_bytes = build_zip(repo_root, output_file)
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Created ZIP: {output_file}")
    print(f"Included tracked files: {file_count}")
    print(f"Archive size: {size_bytes} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

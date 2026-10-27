"""Download taxonomy-matched India-coded SnakeCLEF2022 images from Kaggle.

The script uses the existing train metadata and the project's YAML taxonomy. It
requests only matched image paths from the small-size directory, validates each
image, preserves existing files, supports resuming, and writes the training
manifest expected by ml/scripts/train_taxonomy_classifier.py.

Example:
  python ml/scripts/download_india_subset_from_kaggle.py --dry-run
  python ml/scripts/download_india_subset_from_kaggle.py --limit 10 --manifest data/manifests/india_taxonomy_kaggle_pilot.csv
  python ml/scripts/download_india_subset_from_kaggle.py --workers 3
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METADATA = ROOT / "data/external/snakeclef2022/SnakeCLEF2022-TrainMetadata.csv"
DEFAULT_TAXONOMY = ROOT / "data/taxonomy/india_snakes_taxonomy_v1.yaml"
DEFAULT_IMAGE_ROOT = ROOT / "data/external/snakeclef2022/india_kaggle_images"
DEFAULT_MANIFEST = ROOT / "data/manifests/india_taxonomy_kaggle_images.csv"
REMOTE_PREFIX = "SnakeCLEF2022-small_size/SnakeCLEF2022-small_size"


def norm(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def clean_relative_path(value: str) -> str | None:
    text = str(value or "").strip().replace("\\", "/").lstrip("/")
    if not text:
        return None
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        return None
    return path.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_image(path: Path) -> tuple[bool, str]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.width < 16 or image.height < 16:
                return False, "image_too_small"
            image_format = str(image.format or "unknown")
        return True, image_format
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        return False, f"invalid_image:{type(exc).__name__}"


def load_targets(metadata_path: Path, taxonomy_path: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    with taxonomy_path.open("r", encoding="utf-8-sig") as handle:
        taxonomy = yaml.safe_load(handle) or {}

    targets: dict[str, dict[str, Any]] = {}
    for item in taxonomy.get("species", []):
        if item.get("india_present") is not True:
            continue
        canonical = (item.get("accepted_name") or item.get("snakeclef_binomial") or item.get("species") or "").strip()
        genus = (item.get("genus") or "").strip()
        family = (item.get("family") or "").strip()
        if not canonical or not genus or not family:
            continue
        aliases = {
            norm(item.get(key))
            for key in ("accepted_name", "snakeclef_binomial", "species")
            if norm(item.get(key))
        }
        targets[norm(canonical)] = {
            "species": canonical,
            "genus": genus,
            "family": family,
            "aliases": aliases,
        }

    alias_candidates: dict[str, set[str]] = {}
    for canonical, item in targets.items():
        for alias in item["aliases"]:
            alias_candidates.setdefault(alias, set()).add(canonical)
    alias_map = {
        alias: next(iter(canonicals))
        for alias, canonicals in alias_candidates.items()
        if len(canonicals) == 1
    }

    with metadata_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"binomial_name", "code", "file_path"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Metadata is missing required columns: {sorted(missing)}")
        field_lookup = {field.casefold(): field for field in (reader.fieldnames or [])}
        # Only use a metadata identifier if its name explicitly indicates an observation/occurrence.
        observation_fields = (
            "observation_id", "observationid", "observation_uuid",
            "occurrence_id", "occurrenceid", "inat_observation_id", "gbif_id", "gbifid",
        )
        observation_field = next((field_lookup[name] for name in observation_fields if name in field_lookup), None)
        rows_by_path: dict[str, dict[str, str]] = {}
        conflicting_paths: set[str] = set()
        eligible_records = 0
        taxonomy_records = 0

        for row in reader:
            if norm(row.get("code")) != "in":
                continue
            eligible_records += 1
            canonical = alias_map.get(norm(row.get("binomial_name")))
            if canonical is None:
                continue
            taxon = targets[canonical]
            source_path = clean_relative_path(row.get("file_path", ""))
            if source_path is None:
                continue
            taxonomy_records += 1
            previous = rows_by_path.get(source_path)
            if previous and (
                previous["species_label"] != taxon["species"]
                or previous["genus_label"] != taxon["genus"]
                or previous["family_label"] != taxon["family"]
            ):
                conflicting_paths.add(source_path)
                continue

            observation_id = str(row.get(observation_field, "")).strip() if observation_field else ""
            row_out = {
                "source_file_path": source_path,
                "remote_path": f"{REMOTE_PREFIX}/{source_path}",
                "species_label": taxon["species"],
                "genus_label": taxon["genus"],
                "family_label": taxon["family"],
                "observation_group": f"observation:{observation_id}" if observation_id else f"path:{source_path.casefold()}",
                "metadata_binomial": str(row.get("binomial_name", "")).strip(),
                "region": str(row.get("country", "")).strip(),
                "class_id": str(row.get("class_id", "")).strip(),
                "source_country_code": str(row.get("code", "")).strip(),
            }
            rows_by_path[source_path] = row_out

    for path in conflicting_paths:
        rows_by_path.pop(path, None)

    rows = [rows_by_path[path] for path in sorted(rows_by_path)]
    stats = {
        "india_coded_metadata_records": eligible_records,
        "india_coded_taxonomy_matched_records_before_path_dedup": taxonomy_records,
        "unique_safe_paths": len(rows),
        "conflicting_paths_excluded": len(conflicting_paths),
        "target_species": len({row["species_label"] for row in rows}),
        "target_genera": len({row["genus_label"] for row in rows}),
        "target_families": len({row["family_label"] for row in rows}),
    }
    return rows, stats


def write_csv_atomic(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    # Replace only the output file explicitly selected by this script; image files are never replaced.
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--image-root", type=Path, default=DEFAULT_IMAGE_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--limit", type=int, default=0, help="Limit records for a pilot test; 0 means all")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent single-file Kaggle CLI downloads (1-4 recommended)")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true", help="Plan only; do not download or write a manifest")
    parser.add_argument("--resume", action="store_true", help="Allow rebuilding an existing manifest from verified local files")
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be 0 or a positive integer")
    if not 1 <= args.workers <= 4:
        parser.error("--workers must be between 1 and 4 to avoid excessive parallel requests")
    if args.retries < 1 or args.retries > 6:
        parser.error("--retries must be between 1 and 6")
    if not args.metadata.is_file():
        raise SystemExit(f"Metadata not found: {args.metadata}")
    if not args.taxonomy.is_file():
        raise SystemExit(f"Taxonomy not found: {args.taxonomy}")
    if args.manifest.exists() and not args.dry_run and not args.resume:
        raise SystemExit(
            f"Manifest already exists and was preserved: {args.manifest}\n"
            "Choose a new --manifest path or pass --resume to explicitly rebuild it from verified local files."
        )

    rows, stats = load_targets(args.metadata, args.taxonomy)
    print("========== TAXONOMY-MATCHED KAGGLE DOWNLOAD PLAN ==========")
    for key, value in stats.items():
        print(f"{key}: {value:,}")
    print(f"Remote image root: {REMOTE_PREFIX}/")
    print(f"Local image root:  {args.image_root}")
    print(f"Output manifest:   {args.manifest}")

    if args.limit:
        rows = rows[:args.limit]
        print(f"Pilot limit:       {len(rows):,}")
    else:
        print(f"Planned records:   {len(rows):,}")
    if rows:
        print("First 5 records:")
        for row in rows[:5]:
            print(f"  {row['species_label']} | {row['genus_label']} | {row['family_label']} | {row['remote_path']}")
    if args.dry_run:
        print("DRY RUN ONLY — no downloads or files modified.")
        return 0

    kaggle_exe = shutil.which("kaggle")
    if not kaggle_exe:
        raise SystemExit("Kaggle CLI was not found on PATH. In PowerShell, run: kaggle competitions files snakeclef2022")

    # Validate the chosen final manifest's existing state before making network requests.
    if args.manifest.exists() and args.resume:
        print("Resume enabled: existing manifest may be rebuilt from the verified local image cache.")

    args.image_root.mkdir(parents=True, exist_ok=True)
    successes: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    total = len(rows)

    def effective_group(row: dict[str, str], digest: str) -> str:
        # Prefer a dataset-provided observation identifier. Otherwise exact duplicates
        # are grouped by content hash so they cannot be split across train/test.
        existing_group = row.get("observation_group", "")
        if existing_group.startswith("observation:"):
            return existing_group
        return f"sha256:{digest}"

    def process_one(row: dict[str, str], stage_root: Path) -> tuple[dict[str, str] | None, dict[str, str] | None, str]:
        rel = PurePosixPath(row["source_file_path"])
        target = args.image_root.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.is_file():
            valid, detail = validate_image(target)
            if valid:
                digest = sha256_file(target)
                out = {**row, "local_path": str(target.resolve()), "sha256": digest, "image_format": detail,
                       "observation_group": effective_group(row, digest), "image_source": "existing_verified_cache"}
                return out, None, "cached"
            return None, {**row, "reason": f"existing_file_not_overwritten:{detail}"}, "failed-existing"

        remote = row["remote_path"]
        staged = stage_root.joinpath(*PurePosixPath(remote).parts)
        last_error = "download_failed"
        for attempt in range(1, args.retries + 1):
            try:
                result = subprocess.run(
                    [kaggle_exe, "competitions", "download", "snakeclef2022",
                     "--file", remote, "--path", str(stage_root), "--quiet"],
                    capture_output=True, text=True, timeout=180, check=False,
                )
                if result.returncode != 0:
                    last_error = ((result.stderr or result.stdout or f"exit_code={result.returncode}").strip())[-1000:]
                elif not staged.is_file():
                    last_error = "kaggle_cli_succeeded_but_expected_file_not_found"
                else:
                    valid, detail = validate_image(staged)
                    if not valid:
                        last_error = f"downloaded_file_invalid:{detail}"
                    else:
                        # Stage, validate, then create the destination without replacing an existing file.
                        partial = target.with_name(target.name + f".{os.getpid()}.{time.time_ns()}.partial")
                        try:
                            shutil.copy2(staged, partial)
                            if target.exists():
                                partial.unlink(missing_ok=True)
                                valid_target, target_detail = validate_image(target)
                                if valid_target:
                                    digest = sha256_file(target)
                                    out = {**row, "local_path": str(target.resolve()), "sha256": digest,
                                           "image_format": target_detail,
                                           "observation_group": effective_group(row, digest),
                                           "image_source": "existing_verified_cache"}
                                    return out, None, "cached-race"
                                return None, {**row, "reason": f"destination_appeared_and_is_invalid:{target_detail}"}, "failed-race"
                            partial.rename(target)
                        except Exception:
                            partial.unlink(missing_ok=True)
                            raise
                        digest = sha256_file(target)
                        out = {**row, "local_path": str(target.resolve()), "sha256": digest,
                               "image_format": detail, "observation_group": effective_group(row, digest),
                               "image_source": "kaggle_small_size"}
                        return out, None, "downloaded"
            except subprocess.TimeoutExpired:
                last_error = "kaggle_cli_timeout_after_180_seconds"
            except OSError as exc:
                last_error = f"local_io_error:{type(exc).__name__}:{exc}"
            if attempt < args.retries:
                time.sleep(min(2 ** attempt, 12))
        return None, {**row, "reason": last_error}, "failed"

    try:
        # One temporary staging tree keeps partially downloaded items away from the permanent cache.
        with tempfile.TemporaryDirectory(prefix="snakeclef_kaggle_stage_") as temp_dir:
            stage_root = Path(temp_dir)
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                future_map = {pool.submit(process_one, row, stage_root): row for row in rows}
                for index, future in enumerate(as_completed(future_map), start=1):
                    row = future_map[future]
                    try:
                        success, failure, status = future.result()
                    except Exception as exc:  # keep the batch moving; record unexpected per-file errors
                        success, failure, status = None, {**row, "reason": f"unexpected:{type(exc).__name__}:{exc}"}, "failed"
                    if success:
                        successes.append(success)
                    if failure:
                        failures.append(failure)
                    if index % 25 == 0 or index == total:
                        print(f"Progress {index:,}/{total:,} | verified={len(successes):,} | failed={len(failures):,} | latest={status}")
    except KeyboardInterrupt:
        print("\nInterrupted. Verified images already placed in the cache are preserved.")
        print("Rerun the same command with --resume if an output manifest was already created.")
        return 130

    # Exact-content duplicates with conflicting taxonomic labels are excluded rather than
    # teaching the model contradictory labels for identical pixels.
    labels_by_digest: dict[str, set[tuple[str, str, str]]] = {}
    for item in successes:
        labels_by_digest.setdefault(item["sha256"], set()).add(
            (item["species_label"], item["genus_label"], item["family_label"])
        )
    conflicting_digests = {digest for digest, labels in labels_by_digest.items() if len(labels) > 1}
    if conflicting_digests:
        for item in successes:
            if item["sha256"] in conflicting_digests:
                failures.append({**item, "reason": "identical_image_has_conflicting_taxonomy_labels"})
        successes = [item for item in successes if item["sha256"] not in conflicting_digests]
        print(f"Excluded {sum(1 for item in failures if item.get('reason') == 'identical_image_has_conflicting_taxonomy_labels'):,} records with conflicting labels for identical image content.")

    manifest_fields = [
        "local_path", "source_file_path", "species_label", "genus_label", "family_label",
        "observation_group", "metadata_binomial", "region", "class_id", "source_country_code",
        "remote_path", "sha256", "image_format", "image_source",
    ]
    # Only promote the model-training manifest when not a limited pilot, unless an alternate manifest is explicit.
    if args.limit and args.manifest.resolve() == DEFAULT_MANIFEST.resolve():
        print("ERROR: refusing to write a limited pilot into the full training manifest.", file=sys.stderr)
        print("Rerun with --manifest data/manifests/india_taxonomy_kaggle_pilot.csv", file=sys.stderr)
        return 2

    successes.sort(key=lambda item: item["source_file_path"])
    write_csv_atomic(args.manifest, successes, manifest_fields)

    if failures:
        failure_fields = [
            "source_file_path", "remote_path", "species_label", "genus_label", "family_label", "reason"
        ]
        failure_path = args.manifest.with_name(
            f"{args.manifest.stem}_failures_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        write_csv_atomic(failure_path, failures, failure_fields)
    else:
        failure_path = None

    print("\n========== DOWNLOAD SUMMARY ==========")
    print(f"Requested paths:  {len(rows):,}")
    print(f"Verified images:  {len(successes):,}")
    print(f"Failed paths:     {len(failures):,}")
    print(f"Training manifest:{args.manifest}")
    if failure_path:
        print(f"Failure report:   {failure_path}")
    print("Image files that already existed and validated were reused, not overwritten.")
    print("Evaluation caveat: exact duplicate content is hash-identifiable; same-observation multi-photo leakage can only be ruled out if metadata supplies a true observation ID.")
    return 0 if successes and not failures else (2 if failures else 3)


if __name__ == "__main__":
    raise SystemExit(main())

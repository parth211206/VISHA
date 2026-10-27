"""Extract only taxonomy-matched India records from a SnakeCLEF image ZIP.

No web requests are made. The user must first obtain the official SnakeCLEF2022
small-image training archive and place it in data/external/snakeclef2022/archives/.
The script never extracts the full archive.
"""
from __future__ import annotations

import argparse
import csv
import sys
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METADATA = ROOT / "data/external/snakeclef2022/SnakeCLEF2022-TrainMetadata.csv"
DEFAULT_TAXONOMY = ROOT / "data/taxonomy/india_snakes_taxonomy_v1.yaml"
DEFAULT_OUTPUT = ROOT / "data/external/snakeclef2022/india_images"
DEFAULT_MANIFEST = ROOT / "data/manifests/india_taxonomy_images.csv"
DEFAULT_MISSING = ROOT / "data/manifests/india_taxonomy_missing.csv"


def norm_name(value: Any) -> str:
    return " ".join(str(value or "").replace("_", " ").strip().casefold().split())


def norm_path(value: Any) -> str:
    parts = [part for part in str(value or "").replace("\\", "/").split("/") if part]
    return "/".join(parts).casefold()


def load_india_targets(taxonomy_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    with taxonomy_path.open("r", encoding="utf-8-sig") as handle:
        taxonomy = yaml.safe_load(handle) or {}

    by_canonical: dict[str, dict[str, Any]] = {}
    alias_candidates: dict[str, set[str]] = defaultdict(set)
    for item in taxonomy.get("species", []):
        if item.get("india_present") is not True:
            continue
        canonical = str(item.get("accepted_name") or item.get("species") or "").strip()
        if not canonical:
            continue
        key = norm_name(canonical)
        aliases = {
            norm_name(item.get(field))
            for field in ("accepted_name", "species", "snakeclef_binomial")
            if norm_name(item.get(field))
        }
        by_canonical[key] = {
            "species": canonical,
            "genus": str(item.get("genus") or "").strip(),
            "family": str(item.get("family") or "").strip(),
            "aliases": aliases,
        }
        for alias in aliases:
            alias_candidates[alias].add(key)

    alias_map = {
        alias: next(iter(canonicals))
        for alias, canonicals in alias_candidates.items()
        if len(canonicals) == 1
    }
    return by_canonical, alias_map


def safe_relative_path(value: str) -> PurePosixPath | None:
    text = str(value or "").replace("\\", "/").strip().lstrip("/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path


def build_rows(metadata_path: Path, by_canonical: dict[str, dict[str, Any]], alias_map: dict[str, str]):
    required = {"binomial_name", "code", "file_path"}
    rows_by_path: dict[str, dict[str, Any]] = {}
    with metadata_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Metadata is missing required columns: {sorted(missing)}")
        for row in reader:
            if norm_name(row.get("code")) != "in":
                continue
            canonical_key = alias_map.get(norm_name(row.get("binomial_name")))
            if canonical_key is None:
                continue
            relative = safe_relative_path(row.get("file_path", ""))
            if relative is None:
                continue
            target = by_canonical[canonical_key]
            key = relative.as_posix().casefold()
            rows_by_path.setdefault(key, {
                "source_file_path": relative.as_posix(),
                "species_label": target["species"],
                "genus_label": target["genus"],
                "family_label": target["family"],
                # SnakeCLEF2022 groups images by observation directory; keep all
                # photographs from the same top-level observation together.
                "observation_group": relative.parts[0],
                "metadata_binomial": str(row.get("binomial_name") or "").strip(),
                "region": str(row.get("country") or "").strip(),
            })
    return list(rows_by_path.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Path to official small-image ZIP")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--missing-report", type=Path, default=DEFAULT_MISSING)
    args = parser.parse_args()

    for required_path in (args.archive, args.metadata, args.taxonomy):
        if not required_path.is_file():
            print(f"ERROR: Required file not found: {required_path}", file=sys.stderr)
            return 2

    by_canonical, alias_map = load_india_targets(args.taxonomy)
    rows = build_rows(args.metadata, by_canonical, alias_map)
    if not rows:
        print("ERROR: No India-coded metadata rows matched the approved taxonomy.", file=sys.stderr)
        return 2

    wanted_by_basename: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        wanted_by_basename[PurePosixPath(row["source_file_path"]).name.casefold()].append(row)

    matched: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
    print(f"Taxonomy-matched India image paths to seek: {len(rows):,}")
    print("Scanning archive index; image payloads will be extracted only when matched...")
    try:
        with zipfile.ZipFile(args.archive, "r") as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                member = norm_path(info.filename)
                basename = PurePosixPath(member).name
                candidates = wanted_by_basename.get(basename, [])
                for row in candidates:
                    wanted = norm_path(row["source_file_path"])
                    if member == wanted or member.endswith("/" + wanted):
                        matched[wanted].append(info)
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"ERROR: Could not read archive: {exc}", file=sys.stderr)
        return 2

    args.output.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.missing_report.parent.mkdir(parents=True, exist_ok=True)
    extracted_rows = []
    missing_rows = []

    with zipfile.ZipFile(args.archive, "r") as archive:
        for index, row in enumerate(rows, start=1):
            wanted = norm_path(row["source_file_path"])
            choices = matched.get(wanted, [])
            if not choices:
                missing_rows.append({**row, "reason": "not_found_in_archive"})
                continue
            # Exact suffix matches are preferred; multiple equivalent matches are
            # ambiguous and are not silently guessed.
            shortest_prefix = min(len(norm_path(item.filename)) - len(wanted) for item in choices)
            best = [item for item in choices if len(norm_path(item.filename)) - len(wanted) == shortest_prefix]
            if len(best) != 1:
                missing_rows.append({**row, "reason": "ambiguous_archive_member"})
                continue

            relative = safe_relative_path(row["source_file_path"])
            if relative is None:
                missing_rows.append({**row, "reason": "unsafe_relative_path"})
                continue
            destination = args.output.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                if destination.exists():
                    # Preserve existing files. Reuse a non-empty file rather than
                    # overwriting it when the extraction script is run again.
                    if not destination.is_file() or destination.stat().st_size == 0:
                        missing_rows.append({**row, "reason": "destination_exists_but_is_not_a_nonempty_file"})
                        continue
                else:
                    # Exclusive creation protects against accidental overwrites.
                    with archive.open(best[0], "r") as source, destination.open("xb") as target:
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            target.write(chunk)
            except (OSError, zipfile.BadZipFile) as exc:
                missing_rows.append({**row, "reason": f"extraction_error:{type(exc).__name__}"})
                continue

            extracted_rows.append({
                **row,
                "local_path": str(destination.resolve()),
                "archive_member": best[0].filename,
                "source_archive": str(args.archive.resolve()),
            })
            if index % 250 == 0:
                print(f"Processed {index:,}/{len(rows):,} target paths; extracted {len(extracted_rows):,}")

    manifest_fields = [
        "local_path", "source_file_path", "species_label", "genus_label", "family_label",
        "observation_group", "metadata_binomial", "region", "archive_member", "source_archive"
    ]
    missing_fields = [
        "source_file_path", "species_label", "genus_label", "family_label",
        "observation_group", "metadata_binomial", "region", "reason"
    ]
    with args.manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=manifest_fields)
        writer.writeheader()
        writer.writerows(extracted_rows)
    with args.missing_report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=missing_fields)
        writer.writeheader()
        writer.writerows(missing_rows)

    print("\n========== INDIA TAXONOMY EXTRACTION SUMMARY ==========")
    print(f"Taxonomy-matched paths: {len(rows):,}")
    print(f"Extracted images:       {len(extracted_rows):,}")
    print(f"Missing/ambiguous:      {len(missing_rows):,}")
    print(f"Manifest:               {args.manifest}")
    print(f"Missing report:         {args.missing_report}")
    print("Only matched target images were extracted; the full archive was not extracted.")
    return 0 if extracted_rows else 3


if __name__ == "__main__":
    raise SystemExit(main())

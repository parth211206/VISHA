#!/usr/bin/env python3
"""
Snake Dataset Inspector
-----------------------
Scans the ORIGINAL snake image dataset without modifying it.

Default dataset:
    C:\AI_ML_Project\Snake Images

Output:
    <dataset_root>\dataset_documentation\
        dataset_manifest.csv
        dataset_report.json
        validation_report.json
        class_distribution.csv
        duplicate_report.csv
        sample_images\
            <split>_<label>_contact_sheet.jpg

Usage:
    python dataset_inspector.py
    python dataset_inspector.py "C:\AI_ML_Project\Snake Images"
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageOps, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required.")
    print("Install it with: python -m pip install Pillow")
    raise SystemExit(1)

DEFAULT_ROOT = Path(r"C:\AI_ML_Project\Snake Images")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
SAMPLE_PER_GROUP = 25
RANDOM_SEED = 42
THUMBNAIL_SIZE = (220, 170)
COLUMNS = 5


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def safe_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def classify_path(path: Path, root: Path):
    rel_parts = path.relative_to(root).parts
    split = rel_parts[0] if len(rel_parts) >= 1 else "UNKNOWN"
    label = rel_parts[1] if len(rel_parts) >= 2 else "UNKNOWN"
    return split, label


def make_contact_sheet(records, output_path: Path, title: str):
    if not records:
        return

    records = sorted(records, key=lambda x: x["relative_path"])
    rows = math.ceil(len(records) / COLUMNS)
    title_h = 50
    cell_w, cell_h = THUMBNAIL_SIZE[0], THUMBNAIL_SIZE[1] + 42
    sheet = Image.new("RGB", (COLUMNS * cell_w, title_h + rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    draw.text((10, 10), title, fill="black", font=font)

    for i, rec in enumerate(records):
        x = (i % COLUMNS) * cell_w
        y = title_h + (i // COLUMNS) * cell_h
        path = Path(rec["absolute_path"])

        try:
            img = Image.open(path).convert("RGB")
            img = ImageOps.contain(img, THUMBNAIL_SIZE)
            px = x + (cell_w - img.width) // 2
            py = y + (THUMBNAIL_SIZE[1] - img.height) // 2
            sheet.paste(img, (px, py))
            caption = f'{rec["image_id"]} | {rec["filename"][:24]}'
            draw.text((x + 3, y + THUMBNAIL_SIZE[1] + 4), caption, fill="black", font=font)
        except Exception:
            draw.text((x + 10, y + 50), "UNREADABLE", fill="black", font=font)

    sheet.save(output_path, quality=92)


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ROOT
    root = root.expanduser().resolve()

    if not root.exists() or not root.is_dir():
        print(f"ERROR: Dataset folder does not exist:\n{root}")
        print("Run the script again with the correct dataset path.")
        raise SystemExit(2)

    out = root / "dataset_documentation"
    samples_dir = out / "sample_images"
    out.mkdir(exist_ok=True)
    samples_dir.mkdir(exist_ok=True)

    image_paths = sorted(
        p for p in root.rglob("*")
        if p.is_file()
        and "dataset_documentation" not in p.parts
        and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    manifest = []
    validation = []
    hash_groups = defaultdict(list)
    group_records = defaultdict(list)
    class_counts = Counter()
    split_counts = Counter()
    split_label_counts = Counter()

    for idx, path in enumerate(image_paths, start=1):
        image_id = f"IMG_{idx:06d}"
        split, label = classify_path(path, root)
        relative_path = safe_rel(path, root)

        record = {
            "image_id": image_id,
            "split": split,
            "folder_label": label,
            "relative_path": relative_path,
            "absolute_path": str(path),
            "filename": path.name,
            "extension": path.suffix.lower().lstrip("."),
            "width": "",
            "height": "",
            "file_size_bytes": path.stat().st_size,
            "sha256": "",
        }

        errors = []
        try:
            with Image.open(path) as img:
                img.verify()

            with Image.open(path) as img:
                width, height = img.size
                record["width"] = width
                record["height"] = height

            if width < 100 or height < 100:
                errors.append("very_small_image")

        except Exception as e:
            errors.append(f"unreadable_or_corrupt: {type(e).__name__}")

        try:
            digest = sha256_file(path)
            record["sha256"] = digest
            hash_groups[digest].append(relative_path)
        except Exception as e:
            errors.append(f"hash_failed: {type(e).__name__}")

        validation.append({
            "image_id": image_id,
            "relative_path": relative_path,
            "status": "ERROR" if errors else "OK",
            "errors": "; ".join(errors),
        })

        manifest.append(record)
        class_counts[label] += 1
        split_counts[split] += 1
        split_label_counts[(split, label)] += 1
        group_records[(split, label)].append(record)

    # Exact duplicates
    duplicate_rows = []
    duplicate_groups = 0
    duplicate_files = 0
    for digest, paths in hash_groups.items():
        if len(paths) > 1:
            duplicate_groups += 1
            duplicate_files += len(paths)
            for p in paths:
                duplicate_rows.append({
                    "sha256": digest,
                    "duplicate_group_size": len(paths),
                    "relative_path": p,
                })

    # Leakage check: exact same hash appearing across train/test
    hash_to_splits = defaultdict(set)
    for rec in manifest:
        if rec["sha256"]:
            hash_to_splits[rec["sha256"]].add(rec["split"])

    leakage_hashes = {
        h: splits for h, splits in hash_to_splits.items()
        if len(splits) > 1
    }

    # Write manifest
    manifest_fields = [
        "image_id", "split", "folder_label", "relative_path",
        "absolute_path", "filename", "extension", "width",
        "height", "file_size_bytes", "sha256"
    ]
    with (out / "dataset_manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=manifest_fields)
        writer.writeheader()
        writer.writerows(manifest)

    # Validation report
    with (out / "validation_report.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["image_id", "relative_path", "status", "errors"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(validation)

    # Class distribution
    with (out / "class_distribution.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["split", "folder_label", "image_count"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for (split, label), count in sorted(split_label_counts.items()):
            writer.writerow({
                "split": split,
                "folder_label": label,
                "image_count": count
            })

    # Duplicate report
    with (out / "duplicate_report.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["sha256", "duplicate_group_size", "relative_path"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(duplicate_rows)

    # Deterministic representative samples
    rng = random.Random(RANDOM_SEED)
    for (split, label), records in group_records.items():
        selected = list(records)
        rng.shuffle(selected)
        selected = selected[:SAMPLE_PER_GROUP]
        filename = (
            f"{split}_{label.lower().replace(' ', '_')}_contact_sheet.jpg"
        )
        make_contact_sheet(
            selected,
            samples_dir / filename,
            f"{split} / {label} | {len(selected)} representative images"
        )

    readable = sum(1 for x in validation if x["status"] == "OK")
    errors = len(validation) - readable
    dimensions = Counter(
        (r["width"], r["height"])
        for r in manifest
        if r["width"] != "" and r["height"] != ""
    )

    report = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "dataset_root": str(root),
        "documentation_root": str(out),
        "total_images": len(manifest),
        "readable_images": readable,
        "images_with_validation_errors": errors,
        "supported_extensions": sorted(IMAGE_EXTENSIONS),
        "extensions_found": dict(Counter(r["extension"] for r in manifest)),
        "split_counts": dict(split_counts),
        "folder_label_counts": dict(class_counts),
        "split_label_counts": {
            f"{split} / {label}": count
            for (split, label), count in sorted(split_label_counts.items())
        },
        "duplicate_groups_exact_sha256": duplicate_groups,
        "files_in_exact_duplicate_groups": duplicate_files,
        "possible_train_test_exact_hash_leakage_groups": len(leakage_hashes),
        "common_image_dimensions_top_20": [
            {"width": w, "height": h, "count": c}
            for (w, h), c in dimensions.most_common(20)
        ],
        "notes": [
            "Folder labels are recorded as dataset-provided labels.",
            "Species/genus/taxonomy are NOT inferred from filenames.",
            "No original image files were modified.",
            "Exact duplicate detection uses SHA-256.",
            "The train/test leakage check detects exact duplicate files by SHA-256 only; it does not detect visually similar near-duplicates."
        ]
    }

    with (out / "dataset_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Claude-facing contract is copied if absent.
    print("\nSCAN COMPLETE")
    print(f"Dataset: {root}")
    print(f"Images:  {len(manifest)}")
    print(f"Valid:   {readable}")
    print(f"Errors:  {errors}")
    print(f"Output:  {out}")
    print("\nIMPORTANT:")
    print("- Folder labels are recorded, not independently re-labeled.")
    print("- Species information is NOT inferred.")
    print("- Original images were not modified.")
    print("- Review dataset_report.json and validation_report.csv before training.")


if __name__ == "__main__":
    main()

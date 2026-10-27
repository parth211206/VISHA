"""Train a multi-head Indian snake taxonomy classifier from an extracted manifest.

The model produces species, genus, and family logits. It is experimental and is
not suitable for autonomous clinical treatment decisions.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from PIL import Image, UnidentifiedImageError
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ml.models.taxonomy_classifier import TaxonomyMultiHeadClassifier  # noqa: E402

DEFAULT_MANIFEST = ROOT / "data/manifests/india_taxonomy_images.csv"
DEFAULT_BINARY = ROOT / "ml/artifacts/binary_classifier_latest.pt"


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def read_rows(manifest: Path) -> list[dict[str, str]]:
    required = {"local_path", "species_label", "genus_label", "family_label", "observation_group"}
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manifest is missing columns: {sorted(missing)}")
        rows = []
        for row in reader:
            path = Path(row["local_path"])
            if path.is_file() and row["species_label"] and row["genus_label"] and row["family_label"]:
                rows.append(row)
    if not rows:
        raise ValueError(
            f"No usable labeled images in {manifest}. Run extract_india_subset_from_zip.py first."
        )
    return rows


def split_by_observation_group(rows: list[dict[str, str]], seed: int) -> dict[str, str]:
    """Create deterministic group splits so photos from one observation do not cross splits."""
    groups_by_species: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        group = row.get("observation_group") or row["source_file_path"]
        groups_by_species[row["species_label"]].add(group)

    rng = random.Random(seed)
    assignment: dict[str, str] = {}
    split_order = ("train", "validation", "test")
    for species, groups_set in sorted(groups_by_species.items()):
        groups = sorted(groups_set)
        rng.shuffle(groups)
        count = len(groups)
        if count >= 3:
            train_count = max(1, int(round(count * 0.70)))
            val_count = max(1, int(round(count * 0.15)))
            if train_count + val_count >= count:
                train_count = max(1, count - 2)
                val_count = 1
            allocations = ["train"] * train_count + ["validation"] * val_count
            allocations += ["test"] * (count - len(allocations))
        elif count == 2:
            allocations = ["train", "test"]
        else:
            allocations = ["train"]
        for group, split in zip(groups, allocations):
            previous = assignment.get(group)
            if previous and previous != split:
                # A group spanning labels is kept in train to prevent data leakage.
                assignment[group] = "train"
            else:
                assignment[group] = split
    return assignment


class SnakeTaxonomyDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], transform, species_to_idx, genus_to_idx, family_to_idx):
        self.rows = rows
        self.transform = transform
        self.species_to_idx = species_to_idx
        self.genus_to_idx = genus_to_idx
        self.family_to_idx = family_to_idx

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        try:
            with Image.open(row["local_path"]) as source:
                image = source.convert("RGB")
        except (OSError, UnidentifiedImageError) as exc:
            raise RuntimeError(f"Invalid image in manifest: {row['local_path']}") from exc
        return (
            self.transform(image),
            self.species_to_idx.get(row["species_label"], -100),
            self.genus_to_idx.get(row["genus_label"], -100),
            self.family_to_idx.get(row["family_label"], -100),
        )


def class_weights(rows, field: str, class_to_idx: dict[str, int], device):
    counts = Counter(class_to_idx[row[field]] for row in rows if row[field] in class_to_idx)
    weights = torch.ones(len(class_to_idx), dtype=torch.float32)
    for label, idx in class_to_idx.items():
        count = counts.get(idx, 0)
        weights[idx] = 0.0 if count == 0 else len(rows) / (len(class_to_idx) * count)
    positive = weights > 0
    if positive.any():
        weights[positive] = weights[positive] / weights[positive].mean()
    return weights.to(device)


def run_epoch(model, loader, optimizer, device, weights, training: bool):
    model.train(training)
    totals = {"loss": 0.0, "n": 0}
    correct = {"species": 0, "genus": 0, "family": 0}
    seen = {"species": 0, "genus": 0, "family": 0}
    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for images, species, genus, family in loader:
            images = images.to(device)
            targets = {
                "species": species.to(device),
                "genus": genus.to(device),
                "family": family.to(device),
            }
            logits = model(images)
            losses = []
            for head in ("species", "genus", "family"):
                target = targets[head]
                if (target != -100).any():
                    losses.append(F.cross_entropy(
                        logits[head], target, weight=weights[head], ignore_index=-100
                    ))
            if not losses:
                continue
            loss = sum(losses) / len(losses)
            if training:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
            batch_size = images.size(0)
            totals["loss"] += float(loss.detach().cpu()) * batch_size
            totals["n"] += batch_size
            for head in ("species", "genus", "family"):
                target = targets[head]
                mask = target != -100
                if mask.any():
                    pred = logits[head].argmax(dim=1)
                    correct[head] += int((pred[mask] == target[mask]).sum().item())
                    seen[head] += int(mask.sum().item())
    result = {"loss": totals["loss"] / max(1, totals["n"])}
    for head in ("species", "genus", "family"):
        result[f"{head}_accuracy"] = correct[head] / seen[head] if seen[head] else None
        result[f"{head}_n"] = seen[head]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--binary-checkpoint", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=0.0003)
    parser.add_argument("--min-species-images", type=int, default=8)
    parser.add_argument("--min-genus-images", type=int, default=20)
    parser.add_argument("--min-family-images", type=int, default=30)
    parser.add_argument("--seed", type=int, default=37)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    args = parser.parse_args()

    seed_everything(args.seed)
    rows = read_rows(args.manifest)
    species_counts = Counter(row["species_label"] for row in rows)
    genus_counts = Counter(row["genus_label"] for row in rows)
    family_counts = Counter(row["family_label"] for row in rows)
    species_classes = sorted(name for name, count in species_counts.items() if count >= args.min_species_images)
    genus_classes = sorted(name for name, count in genus_counts.items() if count >= args.min_genus_images)
    family_classes = sorted(name for name, count in family_counts.items() if count >= args.min_family_images)
    if min(len(species_classes), len(genus_classes), len(family_classes)) < 2:
        raise ValueError(
            "Insufficient class coverage to train all heads. Review extracted data and class thresholds: "
            f"species={len(species_classes)}, genera={len(genus_classes)}, families={len(family_classes)}"
        )

    species_to_idx = {name: idx for idx, name in enumerate(species_classes)}
    genus_to_idx = {name: idx for idx, name in enumerate(genus_classes)}
    family_to_idx = {name: idx for idx, name in enumerate(family_classes)}
    split_assignment = split_by_observation_group(rows, args.seed)
    for row in rows:
        row["split"] = split_assignment.get(row.get("observation_group") or row["source_file_path"], "train")

    train_rows = [r for r in rows if r["split"] == "train"]
    val_rows = [r for r in rows if r["split"] == "validation"]
    test_rows = [r for r in rows if r["split"] == "test"]
    if len(train_rows) < 2 or not val_rows:
        raise ValueError(
            "The group-aware split did not produce enough train/validation data. "
            "Check observation_group values and the number of extracted observations."
        )

    output_dir = ROOT / "ml/runs" / f"india_taxonomy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=False)
    image_size = 300
    train_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=8),
        transforms.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.10),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    eval_transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    train_ds = SnakeTaxonomyDataset(train_rows, train_transform, species_to_idx, genus_to_idx, family_to_idx)
    val_ds = SnakeTaxonomyDataset(val_rows, eval_transform, species_to_idx, genus_to_idx, family_to_idx)
    test_ds = SnakeTaxonomyDataset(test_rows, eval_transform, species_to_idx, genus_to_idx, family_to_idx)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0) if test_rows else None

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested, but CUDA is not available in this Python environment.")
    device = torch.device(
        "cuda" if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available()) else "cpu"
    )
    model = TaxonomyMultiHeadClassifier(
        num_species=len(species_classes),
        num_genera=len(genus_classes),
        num_families=len(family_classes),
        pretrained_binary_checkpoint=(str(args.binary_checkpoint) if args.binary_checkpoint.is_file() else None),
    ).to(device)
    if args.binary_checkpoint.is_file():
        print(f"Initialized compatible feature weights from {args.binary_checkpoint}")
    else:
        print("WARNING: existing binary checkpoint not found; starting with untrained EfficientNet features.")

    weights = {
        "species": class_weights(train_rows, "species_label", species_to_idx, device),
        "genus": class_weights(train_rows, "genus_label", genus_to_idx, device),
        "family": class_weights(train_rows, "family_label", family_to_idx, device),
    }
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.01)
    best_score = -1.0
    best_path = output_dir / "best_model.pt"
    history = []
    print(f"Device: {device}; images: {len(rows):,}; train/validation/test: "
          f"{len(train_rows):,}/{len(val_rows):,}/{len(test_rows):,}")
    print(f"Supported heads: {len(species_classes)} species, {len(genus_classes)} genera, {len(family_classes)} families")
    print("Note: classes below the image-count thresholds are excluded from that prediction head.")

    for epoch in range(1, args.epochs + 1):
        train_metrics = run_epoch(model, train_loader, optimizer, device, weights, training=True)
        val_metrics = run_epoch(model, val_loader, None, device, weights, training=False)
        ga = val_metrics.get("genus_accuracy") or 0.0
        fa = val_metrics.get("family_accuracy") or 0.0
        score = 0.55 * ga + 0.45 * fa
        row = {"epoch": epoch, "train": train_metrics, "validation": val_metrics, "selection_score": score}
        history.append(row)
        print(
            f"Epoch {epoch:02d}/{args.epochs} | train loss={train_metrics['loss']:.4f} "
            f"| val genus={val_metrics.get('genus_accuracy')} "
            f"| val family={val_metrics.get('family_accuracy')}"
        )
        if score > best_score:
            best_score = score
            torch.save({
                "state_dict": model.state_dict(),
                "model_config": {
                    "architecture": "EfficientNet-B3 multi-head",
                    "image_size": image_size,
                    "dropout": 0.30,
                },
                "classes": {
                    "species": species_classes,
                    "genus": genus_classes,
                    "family": family_classes,
                },
                "species_taxonomy": {
                    row["species_label"]: {
                        "genus": row["genus_label"],
                        "family": row["family_label"],
                    }
                    for row in rows
                    if row["species_label"] in species_to_idx
                },
                "metadata": {
                    "trained_at": datetime.now().isoformat(timespec="seconds"),
                    "training_images": len(train_rows),
                    "validation_images": len(val_rows),
                    "test_images": len(test_rows),
                    "seed": args.seed,
                    "source_manifest": str(args.manifest.resolve()),
                    "binary_checkpoint_used_for_feature_initialization": args.binary_checkpoint.is_file(),
                    "score_type": "uncalibrated_softmax",
                    "clinical_use": "not validated; clinician review required",
                },
            }, best_path)

    # Re-evaluate only the best validation-selected checkpoint on the held-out test split.
    checkpoint = torch.load(best_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["state_dict"])
    test_metrics = run_epoch(model, test_loader, None, device, weights, training=False) if test_loader else None
    (output_dir / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    (output_dir / "test_metrics.json").write_text(json.dumps(test_metrics, indent=2), encoding="utf-8")
    (output_dir / "classes.json").write_text(json.dumps(checkpoint["classes"], indent=2), encoding="utf-8")
    print("\nTraining finished.")
    print(f"Best checkpoint: {best_path}")
    print(f"Held-out test metrics: {json.dumps(test_metrics, sort_keys=True)}")
    print("Scores are not calibrated probabilities, and this model is not clinically validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

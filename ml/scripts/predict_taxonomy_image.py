"""Run local species/genus/family inference using a trained phase-1 checkpoint."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ml.models.taxonomy_classifier import TaxonomyMultiHeadClassifier  # noqa: E402


def topk(logits: torch.Tensor, labels: list[str], k: int = 3) -> list[dict[str, object]]:
    scores = torch.softmax(logits, dim=1)[0]
    values, indices = torch.topk(scores, k=min(k, len(labels)))
    return [
        {"label": labels[int(index)], "score": round(float(score), 4), "score_type": "uncalibrated_softmax"}
        for score, index in zip(values.cpu(), indices.cpu())
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    if not args.image.is_file() or not args.checkpoint.is_file():
        parser.error("Both the image and checkpoint must exist.")
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA was requested but is not available.")
    device = torch.device("cuda" if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available()) else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=True)
    classes = checkpoint["classes"]
    config = checkpoint.get("model_config", {})
    model = TaxonomyMultiHeadClassifier(
        num_species=len(classes["species"]),
        num_genera=len(classes["genus"]),
        num_families=len(classes["family"]),
        dropout=float(config.get("dropout", 0.30)),
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.to(device).eval()
    image_size = int(config.get("image_size", 300))
    transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    with Image.open(args.image) as source:
        tensor = transform(source.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(tensor)
    result = {
        "image": str(args.image.resolve()),
        "species_candidates": topk(logits["species"], classes["species"], args.top_k),
        "genus_candidates": topk(logits["genus"], classes["genus"], args.top_k),
        "family_candidates": topk(logits["family"], classes["family"], args.top_k),
        "species_taxonomy": checkpoint.get("species_taxonomy", {}),
        "model": checkpoint.get("model_config", {}).get("architecture", "unknown"),
        "score_type": "uncalibrated_softmax",
        "limitations": [
            "Experimental model; not clinically validated.",
            "Classes below the training coverage thresholds are not predicted.",
            "Softmax scores are not calibrated real-world probabilities.",
            "Do not use this result to decide whether antivenom is needed or which dose to give.",
        ],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

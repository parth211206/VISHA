from pathlib import Path

import pandas as pd

try:
    import torch
except ImportError:
    pass


class ManifestLoader:
    def __init__(self, manifest_path: Path, image_root: Path):
        self.manifest_path = manifest_path
        self.image_root = image_root

    def load(self) -> pd.DataFrame:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        return pd.read_csv(self.manifest_path)

    def get_train_manifest(
        self, exclude_leakage: bool = True, exclude_intra_duplicates: bool = True
    ) -> pd.DataFrame:
        df = self.load()
        mask = df["split"] == "train"
        if exclude_intra_duplicates:
            mask &= df["use_in_training"] == True
        return df[mask].copy()

    def get_eval_manifest(self, split: str = "test") -> pd.DataFrame:
        df = self.load()
        mask = (df["split"] == split) & (df["use_in_evaluation"] == True)
        return df[mask].copy()

    def get_class_weights(
        self, manifest: pd.DataFrame, label_column: str = "binary_label"
    ) -> "torch.Tensor":
        counts = manifest[label_column].value_counts()
        total = sum(counts)
        # Weight = total / (num_classes * count)
        num_classes = len(counts)
        # We need them ordered consistently, e.g. venomous = 1, non_venomous = 0
        w_non = total / (num_classes * counts.get("non_venomous", 1))
        w_venomous = total / (num_classes * counts.get("venomous", 1))
        return torch.tensor([w_non, w_venomous], dtype=torch.float32)

    def report_split_statistics(self, manifest: pd.DataFrame) -> dict:
        return {
            "total": len(manifest),
            "venomous": int((manifest["binary_label"] == "venomous").sum()),
            "non_venomous": int((manifest["binary_label"] == "non_venomous").sum()),
        }

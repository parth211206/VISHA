from pathlib import Path
from typing import Callable
import pandas as pd
from PIL import Image, UnidentifiedImageError
try:
    import torch
    from torch.utils.data import Dataset
except ImportError:
    Dataset = object

from ml.data.manifest_loader import ManifestLoader

class SnakeImageDataset(Dataset):
    def __init__(
        self,
        manifest: pd.DataFrame,
        image_root: Path,
        transform: Callable,
        label_column: str = "binary_label",
        label_map: dict | None = None,
    ):
        self.manifest = manifest.reset_index(drop=True)
        self.image_root = image_root
        self.transform = transform
        self.label_column = label_column
        self.label_map = label_map or {"non_venomous": 0, "venomous": 1}

    def __len__(self) -> int:
        return len(self.manifest)

    def __getitem__(self, idx: int):
        row = self.manifest.iloc[idx]
        rel_path = str(row["relative_path"])
        # Ensure correct separator
        rel_path = rel_path.replace("\\", "/")
        img_path = self.image_root / rel_path
        
        label_str = row[self.label_column]
        label = self.label_map.get(label_str, -1)

        metadata = {
            "image_id": str(row.get("image_id", idx)),
            "relative_path": rel_path,
            "binary_label": label_str,
            "quality_flag": str(row.get("quality_flag", "OK"))
        }

        try:
            image = Image.open(img_path).convert("RGB")
            tensor = self.transform(image)
            return tensor, label, metadata
        except (UnidentifiedImageError, FileNotFoundError, OSError):
            # Return sentinel for corrupted
            if hasattr(self.transform, "transform") and hasattr(self.transform.transform, "transforms"):
                # roughly guess shape from config, or return dummy 3x300x300
                pass
            dummy_tensor = torch.zeros((3, 300, 300), dtype=torch.float32)
            return dummy_tensor, -1, metadata

    @classmethod
    def from_manifest_loader(
        cls, 
        loader: ManifestLoader, 
        split: str, 
        transform: Callable, 
        label_column: str = "binary_label"
    ) -> "SnakeImageDataset":
        if split == "train":
            manifest = loader.get_train_manifest()
        else:
            manifest = loader.get_eval_manifest(split=split)
            
        return cls(manifest, loader.image_root, transform, label_column=label_column)

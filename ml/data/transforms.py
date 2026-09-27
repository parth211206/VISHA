import yaml
from pathlib import Path
try:
    import torch
    from torchvision.transforms import v2 as transforms
except ImportError:
    pass  # Allow tests to skip

class SnakeTransforms:
    def __init__(self, config: dict, split: str):
        self.split = split
        if split == "train":
            aug_cfg = config.get("augmentation", {}).get("train", {})
            self.transform = transforms.Compose([
                transforms.ToImage(),
                transforms.RandomResizedCrop(aug_cfg.get("random_resized_crop", 300), antialias=True),
                transforms.RandomHorizontalFlip(p=aug_cfg.get("horizontal_flip", 0.5)),
                transforms.RandomVerticalFlip(p=aug_cfg.get("vertical_flip", 0.2)),
                transforms.RandomRotation(degrees=aug_cfg.get("random_rotation", 15)),
                transforms.ColorJitter(
                    brightness=aug_cfg.get("color_jitter", {}).get("brightness", 0.2),
                    contrast=aug_cfg.get("color_jitter", {}).get("contrast", 0.2),
                    saturation=aug_cfg.get("color_jitter", {}).get("saturation", 0.1)
                ),
                transforms.ToDtype(torch.float32, scale=True),
                transforms.Normalize(
                    mean=aug_cfg.get("normalize", {}).get("mean", [0.485, 0.456, 0.406]),
                    std=aug_cfg.get("normalize", {}).get("std", [0.229, 0.224, 0.225])
                )
            ])
        else:
            aug_cfg = config.get("augmentation", {}).get("val", {})
            self.transform = transforms.Compose([
                transforms.ToImage(),
                transforms.Resize(aug_cfg.get("resize", 320), antialias=True),
                transforms.CenterCrop(aug_cfg.get("center_crop", 300)),
                transforms.ToDtype(torch.float32, scale=True),
                transforms.Normalize(
                    mean=aug_cfg.get("normalize", {}).get("mean", [0.485, 0.456, 0.406]),
                    std=aug_cfg.get("normalize", {}).get("std", [0.229, 0.224, 0.225])
                )
            ])

    def __call__(self, image) -> "torch.Tensor":
        return self.transform(image)

    @classmethod
    def from_config(cls, config_path: Path, split: str) -> "SnakeTransforms":
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return cls(config, split)

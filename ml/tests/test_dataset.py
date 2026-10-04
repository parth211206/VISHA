import pandas as pd
import pytest
from PIL import Image

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from ml.data.dataset import SnakeImageDataset
from ml.data.manifest_loader import ManifestLoader


@pytest.fixture
def dummy_manifest(tmp_path):
    df = pd.DataFrame(
        {
            "image_id": ["img1", "img2"],
            "relative_path": ["img1.jpg", "img2.jpg"],
            "binary_label": ["venomous", "non_venomous"],
            "split": ["train", "train"],
            "use_in_training": [True, True],
            "use_in_evaluation": [True, True],
        }
    )
    manifest_path = tmp_path / "manifest.csv"
    df.to_csv(manifest_path, index=False)

    # create dummy images
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    Image.new("RGB", (300, 300)).save(img_dir / "img1.jpg")
    Image.new("RGB", (300, 300)).save(img_dir / "img2.jpg")

    return manifest_path, img_dir


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_dataset_loads_from_manifest(dummy_manifest):
    manifest_path, img_dir = dummy_manifest
    loader = ManifestLoader(manifest_path, img_dir)

    def dummy_transform(img):
        import torchvision.transforms.v2 as transforms

        return transforms.ToTensor()(img)

    ds = SnakeImageDataset.from_manifest_loader(loader, "train", dummy_transform)
    assert len(ds) == 2


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_dataset_returns_correct_shape(dummy_manifest):
    manifest_path, img_dir = dummy_manifest
    loader = ManifestLoader(manifest_path, img_dir)

    def dummy_transform(img):
        import torchvision.transforms.v2 as transforms

        return transforms.ToTensor()(img)

    ds = SnakeImageDataset.from_manifest_loader(loader, "train", dummy_transform)
    tensor, label, meta = ds[0]
    assert tensor.shape == (3, 300, 300)


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_dataset_labels_are_valid(dummy_manifest):
    manifest_path, img_dir = dummy_manifest
    loader = ManifestLoader(manifest_path, img_dir)

    def dummy_transform(img):
        return torch.zeros((3, 300, 300))

    ds = SnakeImageDataset.from_manifest_loader(loader, "train", dummy_transform)
    _, label1, _ = ds[0]
    _, label2, _ = ds[1]

    assert label1 in [0, 1]
    assert label2 in [0, 1]

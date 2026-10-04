import pytest
from PIL import Image

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from ml.data.transforms import SnakeTransforms


@pytest.fixture
def dummy_config():
    return {
        "augmentation": {
            "train": {"random_resized_crop": 300},
            "val": {"resize": 320, "center_crop": 300},
        }
    }


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_train_transforms_output_shape(dummy_config):
    transform = SnakeTransforms(dummy_config, "train")
    img = Image.new("RGB", (400, 400))
    out = transform(img)
    assert out.shape == (3, 300, 300)


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_val_transforms_output_shape(dummy_config):
    transform = SnakeTransforms(dummy_config, "val")
    img = Image.new("RGB", (400, 400))
    out = transform(img)
    assert out.shape == (3, 300, 300)


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_transforms_normalize(dummy_config):
    transform = SnakeTransforms(dummy_config, "val")
    img = Image.new("RGB", (400, 400), color=(0, 0, 0))
    out = transform(img)
    # Output should not be in [0, 255] anymore, and possibly negative due to normalization
    assert torch.min(out) < 0
    assert torch.max(out) < 5

import pytest

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from ml.models.binary_classifier import BinarySnakeClassifier
from ml.models.species_interface import ModelNotLoadedError, NotAvailableSpeciesClassifier


@pytest.fixture
def dummy_config():
    return {"model": {"architecture": "efficientnet_b3", "pretrained": False, "dropout": 0.3}}


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_binary_classifier_instantiates(dummy_config):
    model = BinarySnakeClassifier(dummy_config)
    assert model is not None


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_binary_classifier_forward_shape(dummy_config):
    model = BinarySnakeClassifier(dummy_config)
    model.eval()
    x = torch.randn(1, 3, 300, 300)
    with torch.no_grad():
        out = model(x)
    assert out.shape == (1, 2)


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_binary_classifier_probabilities_sum_to_one(dummy_config):
    model = BinarySnakeClassifier(dummy_config)
    model.eval()
    x = torch.randn(1, 3, 300, 300)
    with torch.no_grad():
        probs = model.get_probabilities(x)
    assert torch.allclose(torch.sum(probs, dim=1), torch.ones(1))


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_freeze_backbone(dummy_config):
    model = BinarySnakeClassifier(dummy_config)
    model.freeze_backbone()
    for param in model.backbone.features.parameters():
        assert not param.requires_grad


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_unfreeze_backbone(dummy_config):
    model = BinarySnakeClassifier(dummy_config)
    model.freeze_backbone()
    model.unfreeze_backbone()
    for param in model.backbone.features.parameters():
        assert param.requires_grad


def test_species_interface_not_available():
    classifier = NotAvailableSpeciesClassifier()
    assert not classifier.is_loaded()


def test_species_interface_raises_on_predict():
    classifier = NotAvailableSpeciesClassifier()
    with pytest.raises(ModelNotLoadedError):
        classifier.predict_species(None)

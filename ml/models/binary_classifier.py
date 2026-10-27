from pathlib import Path

import yaml

try:
    import torch
    from torch import nn
    from torchvision.models import EfficientNet_B3_Weights, efficientnet_b3
except ImportError:
    nn = object


class BinarySnakeClassifier(nn.Module if nn is not object else object):
    """
    Binary classifier: Venomous vs Non-Venomous.
    Architecture: EfficientNet-B3 backbone.
    This model does NOT perform species identification.
    """

    def __init__(self, config: dict, num_classes: int = 2):
        super().__init__()
        self.config = config
        self.num_classes = num_classes

        pretrained = config.get("model", {}).get("pretrained", True)
        weights = EfficientNet_B3_Weights.DEFAULT if pretrained else None

        self.backbone = efficientnet_b3(weights=weights)

        # Replace classifier head
        in_features = self.backbone.classifier[1].in_features
        dropout_p = config.get("model", {}).get("dropout", 0.3)

        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=dropout_p, inplace=False),
            nn.Linear(in_features, 512),
            nn.ReLU(inplace=False),
            nn.Dropout(p=dropout_p, inplace=False),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        return self.backbone(x)

    def get_probabilities(self, x):
        logits = self.forward(x)
        return torch.softmax(logits, dim=1)

    def freeze_backbone(self):
        for param in self.backbone.features.parameters():
            param.requires_grad = False

    def unfreeze_backbone(self):
        for param in self.backbone.features.parameters():
            param.requires_grad = True

    @classmethod
    def from_config(cls, config_path: Path) -> "BinarySnakeClassifier":
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return cls(config)

    @classmethod
    def load_checkpoint(cls, checkpoint_path: Path, config: dict) -> "BinarySnakeClassifier":
        model = cls(config)
        state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        return model

    def save_checkpoint(self, path: Path, metadata: dict):
        torch.save(self.state_dict(), path)

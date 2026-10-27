"""Multi-head image classifier for Indian snake taxonomy.

This is a separate model from BinarySnakeClassifier; do not load the binary
checkpoint as if it were already a species classifier.
"""
from __future__ import annotations

from typing import Any

import torch
from torch import nn
from torchvision.models import efficientnet_b3


class TaxonomyMultiHeadClassifier(nn.Module):
    """Predict species, genus, and family from an image with separate heads."""

    def __init__(
        self,
        num_species: int,
        num_genera: int,
        num_families: int,
        dropout: float = 0.30,
        pretrained_binary_checkpoint: str | None = None,
    ) -> None:
        super().__init__()
        if min(num_species, num_genera, num_families) < 2:
            raise ValueError("Each prediction head must contain at least two classes.")

        self.backbone = efficientnet_b3(weights=None)
        feature_count = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Identity()
        self.species_head = self._head(feature_count, num_species, dropout)
        self.genus_head = self._head(feature_count, num_genera, dropout)
        self.family_head = self._head(feature_count, num_families, dropout)

        if pretrained_binary_checkpoint:
            self.initialize_from_binary_checkpoint(pretrained_binary_checkpoint)

    @staticmethod
    def _head(feature_count: int, class_count: int, dropout: float) -> nn.Sequential:
        return nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(feature_count, 512),
            nn.ReLU(inplace=False),
            nn.Dropout(p=dropout),
            nn.Linear(512, class_count),
        )

    def initialize_from_binary_checkpoint(self, checkpoint_path: str) -> dict[str, Any]:
        """Reuse compatible feature-extractor weights from the existing binary model.

        Only backbone feature weights are copied. The binary classifier head is
        deliberately discarded and is never treated as taxonomic output.
        """
        state = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        own = self.state_dict()
        compatible = {
            key: value
            for key, value in state.items()
            if key.startswith(("backbone.features.", "backbone.avgpool."))
            and key in own
            and own[key].shape == value.shape
        }
        if not compatible:
            raise ValueError(
                "No compatible EfficientNet feature weights were found in "
                f"{checkpoint_path!r}. Verify that it is the existing binary checkpoint."
            )
        result = self.load_state_dict(compatible, strict=False)
        return {
            "source_checkpoint": checkpoint_path,
            "feature_tensors_loaded": len(compatible),
            "missing_keys": len(result.missing_keys),
            "unexpected_keys": len(result.unexpected_keys),
            "binary_head_reused": False,
        }

    def forward(self, images: torch.Tensor) -> dict[str, torch.Tensor]:
        features = self.backbone(images)
        return {
            "species": self.species_head(features),
            "genus": self.genus_head(features),
            "family": self.family_head(features),
        }

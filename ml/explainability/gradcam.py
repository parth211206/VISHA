from dataclasses import dataclass

import numpy as np
from PIL import Image

try:
    import torch
    import torch.nn.functional as F
except ImportError:
    pass

from ml.models.binary_classifier import BinarySnakeClassifier


@dataclass
class GradCAMResult:
    heatmap: np.ndarray
    overlay_image: Image
    target_class: int
    target_class_score: float
    disclaimer: str = "GradCAM highlights model attention regions. This is not clinical evidence."


class GradCAMExplainer:
    def __init__(self, model: BinarySnakeClassifier, target_layer: str = "features.8"):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None

        self.model.eval()
        self._register_hooks()

    def _register_hooks(self):
        # Specific to EfficientNet-B3
        target_module = dict(self.model.backbone.named_modules()).get(self.target_layer)
        if target_module:
            target_module.register_forward_hook(self._forward_hook)
            target_module.register_full_backward_hook(self._backward_hook)

    def _forward_hook(self, module, input, output):
        self.activations = output

    def _backward_hook(self, module, grad_input, grad_output):
        self.gradients = grad_output[0]

    def generate(
        self, tensor: "torch.Tensor", original_image: Image, target_class: int | None = None
    ) -> GradCAMResult:
        self.model.zero_grad()

        logits = self.model(tensor)
        if target_class is None:
            target_class = int(torch.argmax(logits, dim=1).item())

        score = float(torch.softmax(logits, dim=1)[0, target_class].item())

        target = logits[0, target_class]
        target.backward()

        if self.gradients is None or self.activations is None:
            # fallback
            heatmap = np.zeros((original_image.height, original_image.width))
            return GradCAMResult(heatmap, original_image, target_class, score)

        pooled_gradients = torch.mean(self.gradients, dim=[0, 2, 3])
        for i in range(self.activations.shape[1]):
            self.activations[:, i, :, :] *= pooled_gradients[i]

        heatmap = torch.mean(self.activations, dim=1).squeeze()
        heatmap = F.relu(heatmap)
        heatmap /= torch.max(heatmap) + 1e-8

        heatmap_np = heatmap.cpu().detach().numpy()

        # In a real app we'd resize and overlay the heatmap here
        # Return dummy for now
        return GradCAMResult(heatmap_np, original_image, target_class, score)

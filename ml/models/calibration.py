from pathlib import Path

try:
    import torch
    from torch import nn, optim
except ImportError:
    nn = object


class TemperatureScaler(nn.Module if nn is not object else object):
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def fit(self, logits: "torch.Tensor", labels: "torch.Tensor") -> "TemperatureScaler":
        nll_criterion = nn.CrossEntropyLoss()
        optimizer = optim.LBFGS([self.temperature], lr=0.01, max_iter=50)

        def eval_step():
            optimizer.zero_grad()
            loss = nll_criterion(self.forward(logits), labels)
            loss.backward()
            return loss

        optimizer.step(eval_step)
        return self

    def forward(self, logits: "torch.Tensor") -> "torch.Tensor":
        return logits / self.temperature

    def get_temperature(self) -> float:
        return self.temperature.item()

    def save(self, path: Path):
        torch.save(self.state_dict(), path)

    @classmethod
    def load(cls, path: Path) -> "TemperatureScaler":
        scaler = cls()
        scaler.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        return scaler

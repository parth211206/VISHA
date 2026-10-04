import json
from pathlib import Path

import numpy as np


class MahalanobisOODDetector:
    def __init__(self, threshold_percentile: float = 95.0):
        self.threshold_percentile = threshold_percentile
        self.mean = None
        self.cov_inv = None
        self.threshold = None

    def fit(self, features: np.ndarray, labels: np.ndarray = None):
        self.mean = np.mean(features, axis=0)
        cov = np.cov(features, rowvar=False)
        self.cov_inv = np.linalg.pinv(cov)

        scores = self.score(features)
        self.threshold = np.percentile(scores, self.threshold_percentile)

    def score(self, features: np.ndarray) -> np.ndarray:
        if self.mean is None or self.cov_inv is None:
            raise ValueError("OOD Detector is not fitted.")

        diff = features - self.mean
        # Mahalanobis distance squared
        m_dist_sq = np.sum(np.dot(diff, self.cov_inv) * diff, axis=1)
        return m_dist_sq

    def is_ood(self, features: np.ndarray) -> np.ndarray:
        scores = self.score(features)
        return scores > self.threshold

    def save(self, path: Path):
        data = {
            "threshold_percentile": self.threshold_percentile,
            "threshold": float(self.threshold),
            "mean": self.mean.tolist(),
            "cov_inv": self.cov_inv.tolist(),
        }
        with open(path, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: Path) -> "MahalanobisOODDetector":
        with open(path, "r") as f:
            data = json.load(f)
        detector = cls(data["threshold_percentile"])
        detector.threshold = data["threshold"]
        detector.mean = np.array(data["mean"])
        detector.cov_inv = np.array(data["cov_inv"])
        return detector

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from PIL import Image
try:
    import torch
    import numpy as np
except ImportError:
    pass

from ml.models.binary_classifier import BinarySnakeClassifier
from ml.models.species_interface import SpeciesClassifierInterface, SpeciesPrediction
from ml.models.calibration import TemperatureScaler
from ml.evaluation.ood_detector import MahalanobisOODDetector

@dataclass
class InferencePrediction:
    binary_label: str
    binary_confidence: float
    venomous_probability: float
    non_venomous_probability: float
    is_calibrated: bool
    is_ood: bool
    ood_score: float
    ood_threshold: float
    species_available: bool
    species_prediction: SpeciesPrediction | None
    model_version: str
    timestamp: datetime
    processing_time_ms: float
    low_confidence_warning: bool
    clinical_disclaimer: str

class SnakeVisionEngine:
    def __init__(
        self,
        binary_classifier: BinarySnakeClassifier,
        calibrator: TemperatureScaler | None,
        ood_detector: MahalanobisOODDetector | None,
        species_classifier: SpeciesClassifierInterface | None,
        device: "torch.device",
        min_confidence: float = 0.60,
    ):
        self.binary_classifier = binary_classifier
        self.calibrator = calibrator
        self.ood_detector = ood_detector
        self.species_classifier = species_classifier
        self.device = device
        self.min_confidence = min_confidence
        
        self.binary_classifier.to(self.device)
        self.binary_classifier.eval()
        if self.calibrator:
            self.calibrator.to(self.device)
            self.calibrator.eval()

    def predict(self, image: Image, transform=None) -> InferencePrediction:
        start_time = datetime.now()
        
        if transform is None:
            # dummy transform for fallback if not provided
            pass
            
        tensor = transform(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            # Features for OOD
            features = self.binary_classifier.backbone.features(tensor)
            features = self.binary_classifier.backbone.avgpool(features)
            features_flat = torch.flatten(features, 1).cpu().numpy()
            
            logits = self.binary_classifier(tensor)
            
            if self.calibrator:
                logits = self.calibrator(logits)
                is_calibrated = True
            else:
                is_calibrated = False
                
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            
        venomous_prob = float(probs[1])
        non_venomous_prob = float(probs[0])
        
        if venomous_prob >= non_venomous_prob:
            label = "venomous"
            conf = venomous_prob
        else:
            label = "non_venomous"
            conf = non_venomous_prob

        # OOD
        is_ood = False
        ood_score = 0.0
        ood_thresh = 0.0
        if self.ood_detector:
            ood_score = float(self.ood_detector.score(features_flat)[0])
            ood_thresh = float(self.ood_detector.threshold)
            is_ood = ood_score > ood_thresh

        # Species
        species_pred = None
        species_avail = False
        if self.species_classifier and self.species_classifier.is_loaded():
            species_avail = True
            species_pred = self.species_classifier.predict_species(tensor)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds() * 1000

        return InferencePrediction(
            binary_label=label,
            binary_confidence=conf,
            venomous_probability=venomous_prob,
            non_venomous_probability=non_venomous_prob,
            is_calibrated=is_calibrated,
            is_ood=is_ood,
            ood_score=ood_score,
            ood_threshold=ood_thresh,
            species_available=species_avail,
            species_prediction=species_pred,
            model_version="v1.0.0",
            timestamp=end_time,
            processing_time_ms=processing_time,
            low_confidence_warning=conf < self.min_confidence,
            clinical_disclaimer="CLINICAL DECISION SUPPORT ONLY. Not a diagnosis."
        )

    def predict_batch(self, images: list[Image]) -> list[InferencePrediction]:
        pass

    @classmethod
    def load(cls, model_dir: Path, config: dict) -> "SnakeVisionEngine":
        pass
    
    def get_engine_status(self) -> dict:
        return {}

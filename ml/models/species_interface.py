from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
try:
    import torch
except ImportError:
    pass

@dataclass
class SpeciesPrediction:
    species_probabilities: Dict[str, float]
    genus_probabilities: Dict[str, float]
    top_species: str
    top_genus: str
    confidence: float
    is_ood: bool
    ood_score: float
    model_version: str
    timestamp: datetime

@dataclass
class ModelMetadata:
    model_version: str
    architecture: str
    num_classes: int
    taxonomy_version: str
    training_dataset: str
    training_date: str
    val_metrics: Dict[str, float]
    is_calibrated: bool
    calibration_method: Optional[str]

class SpeciesClassifierInterface(ABC):
    @abstractmethod
    def predict_species(self, image: "torch.Tensor") -> SpeciesPrediction:
        pass
    
    @abstractmethod
    def get_supported_species(self) -> List[str]:
        pass
    
    @abstractmethod
    def get_model_metadata(self) -> ModelMetadata:
        pass
    
    @abstractmethod
    def is_loaded(self) -> bool:
        pass

class ModelNotLoadedError(Exception):
    pass

class NotAvailableSpeciesClassifier(SpeciesClassifierInterface):
    def predict_species(self, image: "torch.Tensor") -> SpeciesPrediction:
        raise ModelNotLoadedError("Species classifier not available. Binary classifier only.")
        
    def get_supported_species(self) -> List[str]:
        return []
        
    def get_model_metadata(self) -> ModelMetadata:
        return ModelMetadata(
            model_version="N/A",
            architecture="N/A",
            num_classes=0,
            taxonomy_version="N/A",
            training_dataset="N/A",
            training_date="N/A",
            val_metrics={},
            is_calibrated=False,
            calibration_method=None
        )
        
    def is_loaded(self) -> bool:
        return False

def aggregate_genus_probabilities(species_probs: Dict[str, float], taxonomy_mapper) -> Dict[str, float]:
    genus_probs = {}
    for sp, prob in species_probs.items():
        species_info = taxonomy_mapper.get_species(sp)
        genus = species_info["genus"] if species_info else "Unknown"
        genus_probs[genus] = genus_probs.get(genus, 0.0) + prob
        
    # Normalize
    total = sum(genus_probs.values())
    if total > 0:
        genus_probs = {g: p/total for g, p in genus_probs.items()}
    return genus_probs

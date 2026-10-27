"""Lazy loader for the existing binary classifier and taxonomy image classifier.

The binary classifier remains the source of the legacy venomous/non-venomous
fields. A separately trained multi-head checkpoint supplies experimental
species/genus/family candidates. Taxonomy-model failures do not fabricate labels
and do not prevent an otherwise successful binary prediction.
"""
from __future__ import annotations

import copy
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ModelUnavailableError(RuntimeError):
    """Raised when a required model cannot be loaded for inference."""


class MLModelService:
    """Lazy singleton wrapper around binary and taxonomy EfficientNet-B3 models."""

    _instance: "MLModelService | None" = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "MLModelService":
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._model = None
                instance._transform = None
                instance._device = None
                instance._torch = None
                instance._load_error = None
                instance._load_attempted = False
                instance._load_lock = threading.Lock()
                instance._predict_lock = threading.Lock()

                instance._taxonomy_model = None
                instance._taxonomy_transform = None
                instance._taxonomy_device = None
                instance._taxonomy_torch = None
                instance._taxonomy_classes = None
                instance._taxonomy_species_map = {}
                instance._taxonomy_model_config = {}
                instance._taxonomy_checkpoint = None
                instance._taxonomy_load_error = None
                instance._taxonomy_load_lock = threading.Lock()
                instance._taxonomy_predict_lock = threading.Lock()
                cls._instance = instance
            return cls._instance

    @staticmethod
    def _project_root() -> Path:
        # ml_service.py lives at <project>/backend/app/services/ml_service.py
        return Path(__file__).resolve().parents[3]

    def _paths(self) -> tuple[Path, Path]:
        root = self._project_root()
        return (
            root / "ml" / "config" / "training_config_prototype.yaml",
            root / "ml" / "artifacts" / "binary_classifier_latest.pt",
        )

    def _taxonomy_checkpoint_path(self) -> Path:
        """Return configured taxonomy checkpoint or newest Phase-1 training checkpoint.

        Set SNAKE_TAXONOMY_CHECKPOINT to pin a specific checkpoint. Otherwise, the
        most recently modified ml/runs/india_taxonomy_*/best_model.pt is selected.
        """
        root = self._project_root()
        configured = os.getenv("SNAKE_TAXONOMY_CHECKPOINT", "").strip()
        if configured:
            candidate = Path(configured).expanduser()
            return candidate if candidate.is_absolute() else (root / candidate).resolve()

        runs_dir = root / "ml" / "runs"
        candidates = list(runs_dir.glob("india_taxonomy_*/best_model.pt"))
        if candidates:
            try:
                return max(candidates, key=lambda path: path.stat().st_mtime_ns)
            except OSError:
                # Fall through to a stable conventional path if a run was removed
                # between discovery and stat.
                pass
        return root / "ml" / "artifacts" / "taxonomy_classifier_latest.pt"

    @staticmethod
    def _display_path(path: Path, root: Path) -> str:
        try:
            return str(path.resolve().relative_to(root.resolve()))
        except (OSError, ValueError):
            return str(path)

    def status(self) -> dict[str, Any]:
        """Return status of both models without forcing heavyweight model loading."""
        config_path, checkpoint_path = self._paths()
        config_exists = config_path.is_file()
        checkpoint_exists = checkpoint_path.is_file()
        if self._model is not None:
            state = "loaded"
        elif self._load_error:
            state = "failed"
        elif config_exists and checkpoint_exists:
            state = "configured_not_loaded"
        else:
            state = "missing_artifacts"

        taxonomy_path = self._taxonomy_checkpoint_path()
        taxonomy_checkpoint_exists = taxonomy_path.is_file()
        if self._taxonomy_model is not None:
            taxonomy_state = "loaded"
        elif self._taxonomy_load_error:
            taxonomy_state = "failed"
        elif taxonomy_checkpoint_exists:
            taxonomy_state = "configured_not_loaded"
        else:
            taxonomy_state = "missing_artifacts"

        result: dict[str, Any] = {
            # Preserve the legacy status contract: status/model_loaded describe
            # the existing binary model.
            "status": state,
            "model_loaded": self._model is not None,
            "config_exists": config_exists,
            "checkpoint_exists": checkpoint_exists,
            "architecture": "EfficientNet-B3",
            "classes": ["non_venomous", "venomous"],
            "taxonomy_identification_available": (
                taxonomy_checkpoint_exists and self._taxonomy_load_error is None
            ),
            "calibrated_scores_available": False,
            "taxonomy_status": taxonomy_state,
            "taxonomy_model_loaded": self._taxonomy_model is not None,
            "taxonomy_checkpoint_exists": taxonomy_checkpoint_exists,
            "taxonomy_checkpoint": self._display_path(taxonomy_path, self._project_root()),
            "taxonomy_class_counts": (
                {key: len(value) for key, value in self._taxonomy_classes.items()}
                if isinstance(self._taxonomy_classes, dict)
                else None
            ),
        }
        if self._load_error:
            result["reason"] = self._load_error
        if self._taxonomy_load_error:
            result["taxonomy_reason"] = self._taxonomy_load_error
        return result

    def _ensure_loaded(self) -> None:
        """Load the legacy binary classifier only when binary inference is requested."""
        if self._model is not None:
            return

        with self._load_lock:
            if self._model is not None:
                return
            if self._load_error:
                raise ModelUnavailableError(self._load_error)

            self._load_attempted = True
            config_path, checkpoint_path = self._paths()
            try:
                if not config_path.is_file():
                    raise FileNotFoundError(f"Model configuration not found: {config_path}")
                if not checkpoint_path.is_file():
                    raise FileNotFoundError(f"Model checkpoint not found: {checkpoint_path}")

                project_root_text = str(self._project_root())
                if project_root_text not in sys.path:
                    sys.path.insert(0, project_root_text)

                # Import heavy ML dependencies only when inference is first requested.
                import torch
                import yaml

                from ml.data.transforms import SnakeTransforms
                from ml.models.binary_classifier import BinarySnakeClassifier

                with config_path.open("r", encoding="utf-8") as handle:
                    config = yaml.safe_load(handle) or {}

                model_config = copy.deepcopy(config)
                model_section = model_config.setdefault("model", {})
                num_classes = int(model_section.get("num_classes", 2))
                if num_classes != 2:
                    raise ValueError(
                        f"The current binary endpoint expects 2 classes; config specifies {num_classes}."
                    )

                # The checkpoint has trained weights. Avoid downloading pretrained weights.
                model_section["pretrained"] = False
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                model = BinarySnakeClassifier(model_config, num_classes=num_classes)

                try:
                    state_dict = torch.load(
                        checkpoint_path, map_location=device, weights_only=True
                    )
                except TypeError:
                    state_dict = torch.load(checkpoint_path, map_location=device)

                if isinstance(state_dict, dict):
                    if "state_dict" in state_dict and isinstance(state_dict["state_dict"], dict):
                        state_dict = state_dict["state_dict"]
                    elif "model_state_dict" in state_dict and isinstance(
                        state_dict["model_state_dict"], dict
                    ):
                        state_dict = state_dict["model_state_dict"]

                if not isinstance(state_dict, dict):
                    raise ValueError("Binary checkpoint does not contain a model state dictionary.")
                model.load_state_dict(state_dict, strict=True)
                model.to(device)
                model.eval()
                transform = SnakeTransforms.from_config(config_path, split="val")

                self._torch = torch
                self._device = device
                self._model = model
                self._transform = transform
                logger.info(
                    "Binary snake classifier loaded: architecture=EfficientNet-B3 device=%s checkpoint=%s",
                    device,
                    checkpoint_path,
                )
            except Exception as exc:
                self._load_error = f"Model load failed: {type(exc).__name__}: {exc}"
                logger.exception("Failed to load Snakebite CDS binary model")
                raise ModelUnavailableError(
                    "The binary image model could not be loaded. Check /api/v1/ml-inference/status "
                    "and the backend terminal for the exact cause."
                ) from exc

    def _ensure_taxonomy_loaded(self) -> None:
        """Load a trained multi-head checkpoint without reusing the binary head."""
        if self._taxonomy_model is not None:
            return

        with self._taxonomy_load_lock:
            if self._taxonomy_model is not None:
                return
            if self._taxonomy_load_error:
                raise ModelUnavailableError(
                    "The taxonomy image model previously failed to load. Check "
                    "/api/v1/ml-inference/status and the backend terminal."
                )

            checkpoint_path = self._taxonomy_checkpoint_path()
            if not checkpoint_path.is_file():
                raise ModelUnavailableError(
                    "No taxonomy checkpoint was found. Expected ml/runs/india_taxonomy_*/best_model.pt "
                    "or set SNAKE_TAXONOMY_CHECKPOINT to a trained checkpoint."
                )

            try:
                project_root_text = str(self._project_root())
                if project_root_text not in sys.path:
                    sys.path.insert(0, project_root_text)

                import torch
                from torchvision import transforms
                from ml.models.taxonomy_classifier import TaxonomyMultiHeadClassifier

                try:
                    checkpoint = torch.load(
                        checkpoint_path, map_location="cpu", weights_only=True
                    )
                except TypeError:
                    # Backward compatibility for local trusted checkpoints on older PyTorch.
                    checkpoint = torch.load(checkpoint_path, map_location="cpu")

                if not isinstance(checkpoint, dict):
                    raise ValueError("Taxonomy checkpoint is not a dictionary.")
                classes = checkpoint.get("classes")
                state_dict = checkpoint.get("state_dict")
                if not isinstance(classes, dict) or not isinstance(state_dict, dict):
                    raise ValueError("Taxonomy checkpoint must contain classes and state_dict.")
                for head in ("species", "genus", "family"):
                    if not isinstance(classes.get(head), list) or len(classes[head]) < 2:
                        raise ValueError(f"Taxonomy checkpoint has invalid {head} class metadata.")

                model_config = checkpoint.get("model_config") or {}
                model = TaxonomyMultiHeadClassifier(
                    num_species=len(classes["species"]),
                    num_genera=len(classes["genus"]),
                    num_families=len(classes["family"]),
                    dropout=float(model_config.get("dropout", 0.30)),
                )
                model.load_state_dict(state_dict, strict=True)
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                model.to(device)
                model.eval()

                image_size = int(model_config.get("image_size", 300))
                transform = transforms.Compose([
                    transforms.Resize((image_size, image_size)),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=(0.485, 0.456, 0.406),
                        std=(0.229, 0.224, 0.225),
                    ),
                ])

                self._taxonomy_torch = torch
                self._taxonomy_device = device
                self._taxonomy_model = model
                self._taxonomy_transform = transform
                self._taxonomy_classes = {
                    key: list(value) for key, value in classes.items()
                    if key in ("species", "genus", "family")
                }
                self._taxonomy_species_map = checkpoint.get("species_taxonomy", {})
                self._taxonomy_model_config = dict(model_config)
                self._taxonomy_checkpoint = checkpoint_path
                logger.info(
                    "Taxonomy model loaded: architecture=%s device=%s checkpoint=%s classes=%s",
                    model_config.get("architecture", "EfficientNet-B3 multi-head"),
                    device,
                    checkpoint_path,
                    {key: len(value) for key, value in self._taxonomy_classes.items()},
                )
            except Exception as exc:
                self._taxonomy_load_error = f"Taxonomy model load failed: {type(exc).__name__}: {exc}"
                logger.exception("Failed to load Snakebite CDS taxonomy model")
                raise ModelUnavailableError(
                    "The taxonomy image model could not be loaded. Check /api/v1/ml-inference/status "
                    "and the backend terminal for the exact cause."
                ) from exc

    @staticmethod
    def _top_candidates(logits: Any, labels: list[str], top_k: int = 3) -> list[dict[str, Any]]:
        torch = __import__("torch")
        scores = torch.softmax(logits, dim=1)[0]
        values, indices = torch.topk(scores, k=min(top_k, len(labels)))
        return [
            {
                "label": labels[int(index.item())],
                "score": round(float(score.item()), 4),
                "score_type": "uncalibrated_softmax",
            }
            for score, index in zip(values, indices)
        ]

    def _predict_taxonomy(self, image: Any) -> dict[str, Any]:
        self._ensure_taxonomy_loaded()
        torch = self._taxonomy_torch
        model = self._taxonomy_model
        transform = self._taxonomy_transform
        if torch is None or model is None or transform is None:
            raise ModelUnavailableError("The taxonomy model is not ready for inference.")

        tensor = transform(image.convert("RGB")).unsqueeze(0).to(self._taxonomy_device)
        with self._taxonomy_predict_lock, torch.inference_mode():
            logits = model(tensor)
            species_candidates = self._top_candidates(
                logits["species"], self._taxonomy_classes["species"], top_k=3
            )
            genus_candidates = self._top_candidates(
                logits["genus"], self._taxonomy_classes["genus"], top_k=3
            )
            family_candidates = self._top_candidates(
                logits["family"], self._taxonomy_classes["family"], top_k=3
            )

        species = species_candidates[0]["label"]
        genus = genus_candidates[0]["label"]
        family = family_candidates[0]["label"]
        mapped = self._taxonomy_species_map.get(species, {})
        mapped_genus = mapped.get("genus") if isinstance(mapped, dict) else None
        mapped_family = mapped.get("family") if isinstance(mapped, dict) else None
        hierarchy_consistent = bool(
            mapped_genus and mapped_family and mapped_genus == genus and mapped_family == family
        )

        return {
            "available": True,
            "species": species,
            "genus": genus,
            "family": family,
            "species_candidates": species_candidates,
            "genus_candidates": genus_candidates,
            "family_candidates": family_candidates,
            "predicted_species_taxonomy": mapped if isinstance(mapped, dict) else {},
            "hierarchy_consistent": hierarchy_consistent,
            "score_type": "uncalibrated_softmax",
            "model_info": {
                "architecture": self._taxonomy_model_config.get(
                    "architecture", "EfficientNet-B3 multi-head"
                ),
                "checkpoint": self._display_path(
                    self._taxonomy_checkpoint or self._taxonomy_checkpoint_path(),
                    self._project_root(),
                ),
                "class_counts": {
                    key: len(value) for key, value in self._taxonomy_classes.items()
                },
            },
            "limitations": [
                "Experimental model trained on a small, imbalanced image subset; not clinically validated.",
                "Classes below the training coverage thresholds are not predicted.",
                "Softmax scores are uncalibrated model scores, not real-world probabilities.",
                "Species, genus and family use separate prediction heads and may disagree.",
                "Do not use image predictions to decide whether antivenom is needed or which dose to give.",
            ],
        }

    def predict(self, image: Any) -> dict[str, Any]:
        """Return legacy binary output plus taxonomic candidates when available."""
        self._ensure_loaded()
        torch = self._torch
        if torch is None or self._model is None or self._transform is None:
            raise ModelUnavailableError("The binary model is not ready for inference.")

        try:
            rgb_image = image.convert("RGB")
            tensor = self._transform(rgb_image).unsqueeze(0).to(self._device)
            with self._predict_lock, torch.inference_mode():
                logits = self._model(tensor)
                if logits.ndim != 2 or logits.shape[0] != 1 or logits.shape[1] != 2:
                    raise ValueError(
                        f"Expected binary model output shape (1, 2), received {tuple(logits.shape)}."
                    )
                scores = torch.softmax(logits, dim=1).squeeze(0).detach().cpu().tolist()

            # Existing training uses non_venomous -> 0 and venomous -> 1.
            non_venomous_score = float(scores[0])
            venomous_score = float(scores[1])
            predicted_class = "venomous" if venomous_score >= non_venomous_score else "non_venomous"
            class_scores = {
                "non_venomous": non_venomous_score,
                "venomous": venomous_score,
            }
            result: dict[str, Any] = {
                "predicted_class": predicted_class,
                "probabilities": class_scores,
                "class_scores": class_scores,
                "score_type": "uncalibrated_softmax",
                "is_calibrated": False,
                "model_info": {
                    "architecture": "EfficientNet-B3",
                    "checkpoint": "binary_classifier_latest.pt",
                    "class_count": 2,
                },
                "taxonomy": {
                    "available": False,
                    "family": None,
                    "genus": None,
                    "species": None,
                    "reason": "Taxonomy predictions are unavailable until the trained taxonomy model loads.",
                },
                "disclaimer": (
                    "Experimental image classification only. Scores are uncalibrated model outputs, not "
                    "real-world probabilities. Image classification must not determine clinical treatment "
                    "or delay emergency care."
                ),
            }

            # Taxonomy inference is independent: a taxonomy checkpoint failure must not
            # fabricate taxonomy or discard the existing binary prediction.
            try:
                result["taxonomy"] = self._predict_taxonomy(rgb_image)
            except ModelUnavailableError as exc:
                result["taxonomy"]["reason"] = str(exc)
                logger.warning("Taxonomy prediction unavailable: %s", exc)
            except Exception as exc:
                result["taxonomy"]["reason"] = "Taxonomy inference failed; check backend logs and model status."
                logger.exception("Taxonomy inference failed")

            return result
        except ModelUnavailableError:
            raise
        except Exception as exc:
            logger.exception("Binary snake image inference failed")
            raise RuntimeError(f"Image inference failed: {type(exc).__name__}: {exc}") from exc

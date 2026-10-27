"""Fast, deterministic contract tests that do not load the real model checkpoint."""
from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.v1 import ml_inference
from app.services.ml_service import ModelUnavailableError


@pytest.fixture()
def client() -> TestClient:
    api = FastAPI()
    api.include_router(ml_inference.router, prefix="/api/v1")
    return TestClient(api)


def png_bytes() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (32, 32), (80, 120, 80)).save(stream, format="PNG")
    return stream.getvalue()


def mock_prediction() -> dict:
    scores = {"non_venomous": 0.35, "venomous": 0.65}
    return {
        "predicted_class": "venomous",
        "probabilities": scores,
        "class_scores": scores,
        "score_type": "uncalibrated_softmax",
        "is_calibrated": False,
        "model_info": {"architecture": "EfficientNet-B3", "class_count": 2},
        "taxonomy": {
            "available": False,
            "family": None,
            "genus": None,
            "species": None,
            "reason": "The loaded checkpoint has binary classes only.",
        },
        "disclaimer": "Experimental binary classification only.",
    }


def test_predict_returns_binary_contract_and_no_fake_taxonomy(client, monkeypatch):
    monkeypatch.setattr(ml_inference.ml_service, "predict", lambda image: mock_prediction())
    response = client.post(
        "/api/v1/ml-inference/predict",
        files={"file": ("sample.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["predicted_class"] == "venomous"
    assert set(payload["probabilities"]) == {"venomous", "non_venomous"}
    assert payload["score_type"] == "uncalibrated_softmax"
    assert payload["taxonomy"]["available"] is False
    assert payload["taxonomy"]["genus"] is None
    assert payload["taxonomy"]["family"] is None


def test_predict_rejects_invalid_image(client, monkeypatch):
    monkeypatch.setattr(ml_inference.ml_service, "predict", lambda image: mock_prediction())
    response = client.post(
        "/api/v1/ml-inference/predict",
        files={"file": ("not-image.png", b"not a real image", "image/png")},
    )
    assert response.status_code == 400
    assert "valid supported image" in response.json()["detail"]


def test_predict_returns_503_when_model_is_unavailable(client, monkeypatch):
    def fail(image):
        raise ModelUnavailableError("The model checkpoint could not be loaded.")

    monkeypatch.setattr(ml_inference.ml_service, "predict", fail)
    response = client.post(
        "/api/v1/ml-inference/predict",
        files={"file": ("sample.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 503
    assert "checkpoint could not be loaded" in response.json()["detail"]


def test_status_endpoint_reports_service_status(client, monkeypatch):
    monkeypatch.setattr(
        ml_inference.ml_service,
        "status",
        lambda: {
            "status": "configured_not_loaded",
            "model_loaded": False,
            "config_exists": True,
            "checkpoint_exists": True,
            "taxonomy_identification_available": False,
        },
    )
    response = client.get("/api/v1/ml-inference/status")
    assert response.status_code == 200
    assert response.json()["status"] == "configured_not_loaded"

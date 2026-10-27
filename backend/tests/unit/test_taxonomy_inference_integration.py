"""Contract tests for taxonomy predictions exposed by the existing image endpoint.

These tests mock the ML service so they stay fast and do not load 44 MB/45 MB
local model checkpoints. They test API contract integration, not model accuracy.
"""
from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.v1 import ml_inference


@pytest.fixture()
def client() -> TestClient:
    api = FastAPI()
    api.include_router(ml_inference.router, prefix="/api/v1")
    return TestClient(api)


def png_bytes() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (32, 32), (80, 120, 80)).save(stream, format="PNG")
    return stream.getvalue()


def mock_taxonomy_prediction() -> dict:
    return {
        "predicted_class": "venomous",
        "probabilities": {"non_venomous": 0.12, "venomous": 0.88},
        "class_scores": {"non_venomous": 0.12, "venomous": 0.88},
        "score_type": "uncalibrated_softmax",
        "is_calibrated": False,
        "model_info": {"architecture": "EfficientNet-B3", "class_count": 2},
        "taxonomy": {
            "available": True,
            "species": "Naja naja",
            "genus": "Naja",
            "family": "Elapidae",
            "species_candidates": [
                {"label": "Naja naja", "score": 0.82, "score_type": "uncalibrated_softmax"}
            ],
            "genus_candidates": [
                {"label": "Naja", "score": 0.91, "score_type": "uncalibrated_softmax"}
            ],
            "family_candidates": [
                {"label": "Elapidae", "score": 0.89, "score_type": "uncalibrated_softmax"}
            ],
            "hierarchy_consistent": True,
            "score_type": "uncalibrated_softmax",
            "limitations": ["Experimental model; not clinically validated."],
        },
        "disclaimer": "Experimental image predictions only; not for treatment decisions.",
    }


def test_predict_returns_taxonomy_candidates_when_service_has_them(client, monkeypatch):
    expected = mock_taxonomy_prediction()
    monkeypatch.setattr(ml_inference.ml_service, "predict", lambda image: expected)

    response = client.post(
        "/api/v1/ml-inference/predict",
        files={"file": ("sample.png", png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["predicted_class"] == "venomous"
    assert payload["taxonomy"]["available"] is True
    assert payload["taxonomy"]["species"] == "Naja naja"
    assert payload["taxonomy"]["genus"] == "Naja"
    assert payload["taxonomy"]["family"] == "Elapidae"
    assert payload["taxonomy"]["species_candidates"][0]["label"] == "Naja naja"
    assert payload["taxonomy"]["score_type"] == "uncalibrated_softmax"


def test_predict_preserves_explicit_taxonomy_unavailable_state(client, monkeypatch):
    result = mock_taxonomy_prediction()
    result["taxonomy"] = {
        "available": False,
        "species": None,
        "genus": None,
        "family": None,
        "reason": "No taxonomy checkpoint found.",
    }
    monkeypatch.setattr(ml_inference.ml_service, "predict", lambda image: result)

    response = client.post(
        "/api/v1/ml-inference/predict",
        files={"file": ("sample.png", png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    taxonomy = response.json()["taxonomy"]
    assert taxonomy["available"] is False
    assert taxonomy["genus"] is None
    assert taxonomy["family"] is None
    assert "reason" in taxonomy

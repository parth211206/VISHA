import pytest

from app.core.exceptions import (
    ClinicalSafetyError,
    DataNotFoundError,
    ModelNotLoadedError,
)


def test_data_not_found_error():
    exc = DataNotFoundError("Record not found")
    assert exc.message == "Record not found"
    assert str(exc) == "Record not found"


def test_clinical_safety_error():
    exc = ClinicalSafetyError("Low confidence prediction", constraint="confidence >= 0.60")
    assert exc.message == "Low confidence prediction"
    assert exc.constraint == "confidence >= 0.60"


def test_exception_catching():
    with pytest.raises(ModelNotLoadedError) as exc_info:
        raise ModelNotLoadedError("Model is currently loading")

    assert exc_info.value.message == "Model is currently loading"

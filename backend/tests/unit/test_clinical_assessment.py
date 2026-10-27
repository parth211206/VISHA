
from app.schemas.assessment import ClinicalAssessmentRequest
from app.services.clinical_assessment_service import build_assessment


def test_difficulty_breathing_triggers_urgent_review():
    result = build_assessment(
        ClinicalAssessmentRequest(symptoms=["Difficulty breathing"])
    )
    assert result["priority"] == "URGENT_REVIEW"
    assert result["antivenom_assessment"]["status"] == "PROMPT_CLINICIAN_REVIEW"
    assert result["alerts"]


def test_abnormal_20wbct_triggers_urgent_review():
    result = build_assessment(
        ClinicalAssessmentRequest(
            twenty_wbct="Reported abnormal by clinical team"
        )
    )
    assert result["priority"] == "URGENT_REVIEW"
    assert "20WBCT" in result["alerts"][0]["title"]


def test_swelling_alone_does_not_auto_determine_asv():
    result = build_assessment(
        ClinicalAssessmentRequest(symptoms=["Swelling"])
    )
    assert result["priority"] == "INCOMPLETE_OR_NO_RULE_TRIGGER"
    assert result["antivenom_assessment"]["status"] == "NO_AUTOMATED_ASV_DECISION"
    assert result["antivenom_assessment"]["reference_matches"] == []


def test_non_venomous_model_result_does_not_lower_priority():
    result = build_assessment(
        ClinicalAssessmentRequest(
            symptoms=["Difficulty breathing"],
            image_prediction={
                "predicted_class": "non_venomous",
                "probabilities": {
                    "venomous": 0.1,
                    "non_venomous": 0.9,
                },
            },
        )
    )
    assert result["priority"] == "URGENT_REVIEW"
    assert any(
        item["category"] == "Model limitation"
        for item in result["findings"]
    )


def test_missing_labs_remain_missing():
    result = build_assessment(ClinicalAssessmentRequest())
    assert "20WBCT" in result["missing_laboratory_information"]
    assert "PT / INR" in result["missing_laboratory_information"]
    assert result["priority"] == "INCOMPLETE_OR_NO_RULE_TRIGGER"


def test_verified_taxonomy_requires_a_source():
    result = build_assessment(
        ClinicalAssessmentRequest(
            taxonomy={
                "verified": True,
                "genus": "Naja",
                "source": "",
            }
        )
    )
    assert (
        result["antivenom_assessment"]["reference_lookup_status"]
        == "NOT_RUN_REQUIRES_REVIEWER_VERIFIED_TAXONOMY_AND_SOURCE"
    )


def test_normal_20wbct_is_not_a_negative_diagnosis():
    result = build_assessment(
        ClinicalAssessmentRequest(
            twenty_wbct="Reported normal by clinical team"
        )
    )
    assert any(
        "does not, by itself, exclude evolving envenomation"
        in item["detail"]
        for item in result["findings"]
    )


from datetime import datetime, timezone

from app.schemas.assessment import ClinicalAssessmentRequest


ENGINE_VERSION = "IND-SNAKEBITE-CDS-RULES-0.1.0"

GUIDELINE_TITLE = (
    "Standard Treatment Guidelines: Snakebite"
)

GUIDELINE_VERSION = "Government of India / DGHS, June 2016"

GUIDELINE_URL = (
    "https://www.clinicalestablishments.mohfw.gov.in/"
    "sites/default/files/standard-treatment-guidelines/3941.pdf"
)

NAPSE_URL = (
    "https://www.ncdc.mohfw.gov.in/includes/About/"
    "CentresAndDivision/NPPCSE.php"
)


def _normal(value):
    return str(value or "").strip().casefold()


def _present(value):
    return bool(str(value or "").strip())


def _lab_status(value):
    value = _normal(value)

    if not value or value in {
        "not recorded",
        "pending / not available",
        "not available",
        "pending",
        "unknown",
    }:
        return "MISSING_OR_PENDING"

    if "abnormal" in value or "non-clotting" in value or "non clotting" in value:
        return "REPORTED_ABNORMAL"

    if "normal" in value or "within reference range" in value:
        return "REPORTED_WITHIN_REFERENCE_RANGE"

    return "UNCLASSIFIED"


def build_assessment(payload: ClinicalAssessmentRequest) -> dict:
    """
    Explainable prototype assessment. This is not a validated diagnostic
    model and does not determine whether antivenom should be administered.
    """

    symptoms = [
        str(item).strip()
        for item in payload.symptoms
        if str(item).strip()
    ]
    normalized_symptoms = [_normal(item) for item in symptoms]

    def recorded_symptoms(*terms):
        return [
            original
            for original, normalized in zip(symptoms, normalized_symptoms)
            if any(term in normalized for term in terms)
        ]

    emergency_symptoms = recorded_symptoms(
        "difficulty breathing",
        "respiratory distress",
        "respiratory arrest",
        "difficulty swallowing",
        "drooping eyelids",
        "ptosis",
        "persistent bleeding",
        "unusual or persistent bleeding",
    )

    prompt_review_symptoms = recorded_symptoms(
        "weakness",
        "dark urine",
        "blistering",
        "tissue damage",
        "local bleeding",
    )

    labs = {
        "20WBCT": payload.twenty_wbct,
        "PT / INR": payload.pt_inr,
        "aPTT": payload.aptt,
        "Platelets": payload.platelets,
        "Fibrinogen": payload.fibrinogen,
    }

    lab_results = {
        name: {
            "reported_value": value,
            "status": _lab_status(value),
        }
        for name, value in labs.items()
    }

    abnormal_labs = [
        name
        for name, item in lab_results.items()
        if item["status"] == "REPORTED_ABNORMAL"
    ]

    missing_labs = [
        name
        for name, item in lab_results.items()
        if item["status"] in {"MISSING_OR_PENDING", "UNCLASSIFIED"}
    ]

    alerts = []
    findings = []

    for symptom in emergency_symptoms:
        alerts.append({
            "level": "URGENT",
            "title": "Urgent clinical review finding",
            "detail": (
                f"The recorded symptom is: {symptom}. "
                "The treating clinical team must assess this promptly "
                "under its emergency snakebite protocol."
            ),
            "evidence": "Clinician-entered symptom",
        })

    for lab_name in abnormal_labs:
        alerts.append({
            "level": "URGENT",
            "title": f"Abnormal laboratory result reported: {lab_name}",
            "detail": (
                "The interface records this test as abnormal. Confirm "
                "the actual result, units, timing and clinical context. "
                "Do not infer a diagnosis from the status label alone."
            ),
            "evidence": f"Recorded laboratory status: {labs[lab_name]}",
        })

    if prompt_review_symptoms:
        findings.append({
            "category": "Clinical finding",
            "title": "Additional findings require clinician assessment",
            "detail": (
                "Recorded findings: "
                + ", ".join(prompt_review_symptoms)
                + ". Interpret these with the examination and other results."
            ),
        })

    if _normal(payload.symptom_progression) == "worsening":
        alerts.append({
            "level": "PROMPT_REVIEW",
            "title": "Worsening symptom progression reported",
            "detail": (
                "The selected progression is worsening. Reassess the "
                "patient promptly according to the treating team's protocol."
            ),
            "evidence": "Clinician-entered progression",
        })

    if symptoms:
        findings.append({
            "category": "Symptoms",
            "title": f"{len(symptoms)} symptom(s) recorded",
            "detail": ", ".join(symptoms),
        })
    else:
        findings.append({
            "category": "Information gap",
            "title": "No symptoms selected",
            "detail": (
                "No symptom selection was supplied. This is not evidence "
                "that symptoms or envenomation are absent."
            ),
        })

    if _present(payload.symptom_onset):
        findings.append({
            "category": "Timeline",
            "title": "Recorded symptom onset",
            "detail": payload.symptom_onset,
        })

    if _normal(payload.symptom_progression) == "worsening":
        findings.append({
            "category": "Timeline",
            "title": "Recorded progression",
            "detail": "Worsening ? clinician reassessment is important.",
        })
    elif _present(payload.symptom_progression):
        findings.append({
            "category": "Timeline",
            "title": "Recorded progression",
            "detail": payload.symptom_progression,
        })

    # Swelling alone is documented but is not treated as an automatic
    # indication for antivenom by this prototype.
    local_findings = recorded_symptoms(
        "local pain",
        "swelling",
        "redness",
        "bruising",
    )
    if local_findings:
        findings.append({
            "category": "Local findings",
            "title": "Local symptoms recorded",
            "detail": (
                ", ".join(local_findings)
                + ". Local findings require clinical interpretation; "
                "this engine does not turn them alone into an ASV decision."
            ),
        })

    if not _present(payload.twenty_wbct) or _lab_status(
        payload.twenty_wbct
    ) == "MISSING_OR_PENDING":
        findings.append({
            "category": "Information gap",
            "title": "20WBCT status is missing or pending",
            "detail": (
                "Obtain and interpret investigations as clinically "
                "appropriate under the current local protocol."
            ),
        })
    elif _lab_status(payload.twenty_wbct) == "REPORTED_WITHIN_REFERENCE_RANGE":
        findings.append({
            "category": "Laboratory context",
            "title": "20WBCT reported within the expected category",
            "detail": (
                "A single reported normal test does not, by itself, exclude "
                "evolving envenomation. Repeat assessment/testing should "
                "follow the treating team's approved protocol when indicated."
            ),
        })

    if payload.clinical_notes:
        findings.append({
            "category": "Clinician notes",
            "title": "Free-text notes supplied",
            "detail": (
                "Clinical notes were received but are not interpreted by "
                "the rule engine in this version. Review them directly."
            ),
        })

    prediction = payload.image_prediction or {}
    model_class = prediction.get("predicted_class")
    probabilities = prediction.get("probabilities")

    model_context = {
        "available": bool(prediction),
        "predicted_class": model_class,
        "probabilities": probabilities if isinstance(probabilities, dict) else None,
        "taxonomy_output_present": bool(prediction.get("taxonomy")),
        "interpretation": (
            "Image-model outputs are supporting observations only. "
            "They do not establish envenomation, determine whether ASV "
            "is indicated, or select a product. Raw model scores must not "
            "be described as calibrated clinical probabilities unless "
            "calibration has been independently established."
        ),
    }

    if _normal(model_class) == "non_venomous":
        findings.append({
            "category": "Model limitation",
            "title": "The image classifier selected the non-venomous class",
            "detail": (
                "This result must not be used to rule out envenomation "
                "or override the clinical history, examination, "
                "laboratory findings or clinician judgment."
            ),
        })
    elif _normal(model_class) == "venomous":
        findings.append({
            "category": "Model context",
            "title": "The image classifier selected the venomous class",
            "detail": (
                "This is an image-model output, not a clinical diagnosis "
                "or a decision to administer antivenom."
            ),
        })

    if payload.taxonomy.verified and (
        not _present(payload.taxonomy.source)
        or not (
            _present(payload.taxonomy.species)
            or _present(payload.taxonomy.genus)
        )
    ):
        findings.append({
            "category": "Identification review",
            "title": "Taxonomy verification details are incomplete",
            "detail": (
                "A reviewer-marked verification requires a documented "
                "source and at least a genus or species label before "
                "a reference catalogue search can be attempted."
            ),
        })

    location = {
        "state": payload.state,
        "district": payload.district,
        "locality": payload.locality,
        "location_type": payload.location_type,
        "habitat": payload.habitat,
        "encounter_time": payload.encounter_time,
    }

    if any(_present(value) for value in location.values()):
        findings.append({
            "category": "Geographic context",
            "title": "Encounter context recorded",
            "detail": (
                "Geographic and habitat information is included for "
                "context. This rules engine does not infer snake identity "
                "or treatment from location alone."
            ),
        })

    # Missing values remain missing. They are never silently converted
    # into normal results.
    if emergency_symptoms or abnormal_labs:
        priority = "URGENT_REVIEW"
        headline = (
            "Urgent clinical review is required for the recorded findings."
        )
    elif prompt_review_symptoms or (
        _normal(payload.symptom_progression) == "worsening"
    ):
        priority = "PROMPT_REVIEW"
        headline = (
            "Prompt clinical reassessment is warranted from the "
            "recorded findings."
        )
    else:
        priority = "INCOMPLETE_OR_NO_RULE_TRIGGER"
        headline = (
            "No urgent trigger was identified by these limited structured "
            "rules. This is not a low-risk result or a negative diagnosis."
        )

    reference_taxonomy_complete = bool(
        payload.taxonomy.verified
        and _present(payload.taxonomy.source)
        and (
            _present(payload.taxonomy.species)
            or _present(payload.taxonomy.genus)
        )
    )

    antivenom_status = (
        "PROMPT_CLINICIAN_REVIEW"
        if priority in {"URGENT_REVIEW", "PROMPT_REVIEW"}
        else "NO_AUTOMATED_ASV_DECISION"
    )

    if antivenom_status == "PROMPT_CLINICIAN_REVIEW":
        antivenom_message = (
            "The recorded findings warrant clinician review for possible "
            "envenomation and consideration of the applicable, currently "
            "approved snakebite protocol, including its antivenom criteria. "
            "This tool does not decide whether ASV should be administered."
        )
    else:
        antivenom_message = (
            "The submitted structured fields did not trigger the limited "
            "review rules. This does not mean ASV is unnecessary, does not "
            "exclude envenomation, and must never be used to delay evaluation "
            "or override clinical judgment."
        )

    if reference_taxonomy_complete:
        reference_lookup_status = "READY_FOR_REVIEWER_VERIFIED_TAXONOMY_LOOKUP"
    else:
        reference_lookup_status = (
            "NOT_RUN_REQUIRES_REVIEWER_VERIFIED_TAXONOMY_AND_SOURCE"
        )

    next_steps = [
        "Review the actual history, examination and vital signs.",
        "Confirm the laboratory results, units, timing and clinical context.",
        "Apply the currently approved institutional and national protocol.",
        "Review the evidence, limitations and source version before relying on any antivenom reference.",
        "Document the treating clinician's assessment independently of image-model output.",
    ]

    if missing_labs:
        next_steps.insert(
            1,
            "Review missing or pending recorded tests: " + ", ".join(missing_labs) + ".",
        )

    if emergency_symptoms or abnormal_labs:
        next_steps.insert(
            0,
            "Arrange prompt clinical/emergency assessment in accordance with the treating team's protocol; do not wait for this software.",
        )

    return {
        "engine_version": ENGINE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "priority": priority,
        "headline": headline,
        "case_context": {
            "case_reference": payload.case_reference,
            "facility_name": payload.facility_name,
            "patient_age_group": payload.patient_age_group,
            "patient_sex": payload.patient_sex,
            "bite_site": payload.bite_site,
            "location": location,
        },
        "alerts": alerts,
        "findings": findings,
        "laboratory_summary": lab_results,
        "missing_laboratory_information": missing_labs,
        "model_context": model_context,
        "taxonomy_review": {
            "family": payload.taxonomy.family,
            "genus": payload.taxonomy.genus,
            "species": payload.taxonomy.species,
            "source": payload.taxonomy.source,
            "reviewer_marked_verified": payload.taxonomy.verified,
            "notes": payload.taxonomy.notes,
        },
        "antivenom_assessment": {
            "status": antivenom_status,
            "message": antivenom_message,
            "reference_lookup_status": reference_lookup_status,
            "reference_matches": [],
            "reference_lookup_note": (
                "A reference match is not a patient-specific treatment "
                "recommendation and does not establish that a product "
                "is currently stocked or appropriate."
            ),
        },
        "recommended_review_steps": next_steps,
        "source_basis": [
            {
                "title": GUIDELINE_TITLE,
                "version": GUIDELINE_VERSION,
                "url": GUIDELINE_URL,
                "note": (
                    "Historical reference used to seed this prototype. "
                    "The rules require review and approval against current "
                    "institutional protocols before clinical use."
                ),
            },
            {
                "title": "National Programme for Prevention and Control of Snakebite Envenoming",
                "version": "NCDC programme web page",
                "url": NAPSE_URL,
                "note": (
                    "Programme context for healthcare access, surveillance "
                    "and facility/antivenom availability mapping."
                ),
            },
        ],
        "limitations": [
            "This is an experimental, versioned rule engine, not a validated medical device.",
            "The rule engine does not read or interpret the free-text clinical notes.",
            "The image classifier does not determine whether antivenom is indicated or which product to use.",
            "Geographic context does not establish snake species.",
            "A missing or normal recorded test does not independently exclude evolving envenomation.",
            "The reference guideline is from June 2016 and requires current clinical review.",
            "The facility inventory is facility-reported data, not independent confirmation of physical stock.",
            "This endpoint does not prescribe treatment or calculate antivenom doses.",
        ],
    }

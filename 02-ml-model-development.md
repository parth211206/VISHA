# Part 3 of 5 — ML Model Development, Calibration & Evaluation

**India Snakebite Clinical Decision-Support + Epidemiological Surveillance System**

> Maps to Phases 6–7 in the Master Priority Order (see `00-foundation-and-status.md`, Appendix A). Do not start this part until Part 2's data pipeline and taxonomy work is at least `IMPLEMENTED` and ideally `UNIT TESTED`.

---

## Starting Point: What Already Exists (but is unverified)

The following ML components were written in a previous session but were **only syntax-checked**, because PyTorch was unavailable at the time:

- `transforms.py`
- `model.py`
- `calibration.py`
- `ood.py`
- `explainability.py`
- `dataset.py`
- `inference.py`
- `train.py`
- `calibrate.py`
- `evaluate.py`
- `export_model.py`

**Do NOT claim the actual ML model is working until it has been executed with PyTorch and real data.** Passing a syntax check is not evidence of correctness — inspect each of these files before assuming what they do, per Part 1's inspection-first rule.

---

## ML Priority Workflow (Phase 6 & 7)

After the application structure is stable (Parts 2, 4, and the frontend scaffolding in Part 5 all at least `IMPLEMENTED`), move to actual ML validation.

Install/use the correct PyTorch environment where available. Then, **in this exact order**:

1. Load real dataset
2. Run dataset validation
3. Train a baseline model
4. Evaluate species metrics
5. Evaluate genus metrics
6. Evaluate dangerous confusion pairs
7. Perform calibration **on validation data only**
8. Perform OOD (out-of-distribution) evaluation
9. Test Grad-CAM
10. Export model
11. Integrate inference runtime into backend
12. Test inference through the actual API
13. Test end-to-end image upload → prediction → review

**Report actual metrics. Do not fabricate or estimate performance.** If a step cannot be completed (e.g., a dependency is missing, or data volume is insufficient for a meaningful metric), mark it `BLOCKED` in `PROJECT_STATUS.md` rather than reporting a plausible-sounding number.

---

## Notes specific to this phase

- **Species → genus aggregation is mathematical, not a separately trained model**: genus probabilities are derived from species probabilities (per the architecture in Part 1), so validate that derivation logic explicitly — it's a common place for silent bugs (e.g., normalization errors after aggregation).
- **Dangerous confusion-pair handling** already has prior work (see Part 1, Section 3) — verify this still functions correctly once real data and a real trained model are in the loop, since the earlier verification was likely against synthetic/placeholder data.
- **Calibration must never leak validation data into training**, and must never leak test data into calibration — keep these splits strictly separate, consistent with the manifest's `split` field from Part 2.
- **OOD/unknown detection and Grad-CAM outputs are not optional extras** — they are required parts of the clinical safety contract (see Part 4): never hide low confidence or an OOD/unknown result from the clinician, no matter how well the base classifier performs.

---

## Before moving to Part 4

- Re-run the Testing Cadence in `00-foundation-and-status.md`, Appendix C.
- Update `PROJECT_STATUS.md`, being explicit about which of the 13 steps above reached which status (`IMPLEMENTED`, `UNIT TESTED`, `INTEGRATION TESTED`, `REAL-DATA VALIDATED`, or `PRODUCTION-READY`) — a model can be `REAL-DATA VALIDATED` on species metrics while still `BLOCKED` on Grad-CAM, for example; report each honestly and separately.
- Do not proceed to claiming the end-to-end demonstration (Part 1, Section 5) works until inference is actually integrated and tested through the real API (step 12) — not just in a notebook.

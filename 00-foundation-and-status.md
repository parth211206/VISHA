# Part 1 of 5 — Foundation, Current Status & Work Strategy

**India Snakebite Clinical Decision-Support + Epidemiological Surveillance System**

> Read this file first, in every working session, before touching any other part. It establishes what already exists, how to report status honestly, how to work autonomously, and the master phase order that the other four files map onto.

## How this prompt is split

1. **00-foundation-and-status.md** (this file) — architecture overview, inspection-first rule, existing verified work, work strategy, most-important-rule, and the master appendices (priority order, documentation checklist, testing cadence) that the other files reference.
2. **01-data-pipeline-taxonomy-and-images.md** — GBIF occurrence data, image dataset manifests, taxonomy (Phases 3–5).
3. **02-ml-model-development.md** — model training, calibration, OOD, Grad-CAM, export, inference integration (Phases 6–7).
4. **03-clinical-knowledge-antivenom-and-safety.md** — clinical knowledge structure, antivenom reference structure, clinical safety rules, LLM/RAG constraints (Phase 8 + cross-cutting safety).
5. **04-frontend-ui-and-watermelon-integration.md** — Watermelon UI MCP usage, full UI page spec, integration rules (Phases 1–2, touches Phase 9's epidemiology UI).

You are **continuing development of an existing project**. You are NOT starting a new project.

---

## 1. Current Architecture

The intended system is:

```
Clinician Intake
→ symptoms + bite site + geographic region + optional snake photograph
→ parallel evidence branches:

A. Clinical branch
   Symptoms + bite site + region
   → deterministic clinical/syndrome rules

B. Image branch
   Snake photograph
   → SnakeVision ML classifier
   → species probabilities
   → genus probabilities derived mathematically from species probabilities
   → calibration
   → OOD/unknown detection
   → Grad-CAM/explainability

C. Geographic branch
   GBIF/verified occurrence records
   → geographic prior
   → region-specific plausibility

A+B+C
→ evidence fusion/ranking
→ differential species/genus results
→ confidence + uncertainty
→ clinician review/confirmation

Then:

Clinician confirmation
→ verified case
→ antivenom/reference lookup
→ hospital/facility stock information
→ de-identified surveillance record
→ PostGIS
→ epidemiology dashboard
→ audit trail
```

LLM/RAG, if used, must remain an explanation/evidence-retrieval layer and **MUST NOT** silently override deterministic clinical rules, clinician confirmation, or verified reference data. (Full detail in Part 4.)

**The clinician remains the final decision-maker**, throughout every part of this system.

---

## 2. Do Not Start By Writing Code

First **inspect**:

- `backend/`
- `frontend/`
- `ml/`
- `database/`
- `data/`
- `configs/`
- Docker files
- `tests/`
- documentation
- taxonomy files
- existing manifests
- existing API schemas
- existing frontend routes/components

Then create or update `PROJECT_STATUS.md` with these exact headings:

```
## COMPLETED
## TESTED
## IMPLEMENTED BUT NOT TESTED
## IN PROGRESS
## BLOCKED
## MISSING
## NEXT PRIORITY
```

Do not claim something is "working" merely because the file exists or passes syntax checking.

Use these statuses, and only the strongest one actually demonstrated:

- `IMPLEMENTED`
- `UNIT TESTED`
- `INTEGRATION TESTED`
- `REAL-DATA VALIDATED`
- `PRODUCTION-READY`

---

## 3. Existing Verified Work

The previous development session already achieved substantial progress.

**Known completed/verified areas include:**

- taxonomy loading
- 29 target species
- 20 genera
- species → genus probability aggregation
- `metrics.py`
- dangerous confusion-pair handling
- dataset preparation
- dataset validation
- GBIF occurrence ingestion
- 101 backend tests passing
- correction of high-risk confusion-pair parsing
- Docker configuration files
- React/Vite/TypeScript frontend scaffolding
- authentication context
- role-based navigation
- route guards
- disclaimer banner
- reusable analysis result UI
- Login page
- Dashboard
- New Case
- Case List
- Case Detail
- antivenom reference UI
- facility stock lookup UI
- Epidemiology page started
- `GET /api/taxonomy/groups` endpoint

**The following ML components were written but were previously only syntax-checked because PyTorch was unavailable:**

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

**Therefore do NOT claim that the actual ML model is working until it has been executed with PyTorch and real data.** (Full ML validation workflow is in Part 3.)

---

## 4. Work Strategy

Do not ask "Should I continue?" after every small task.

**Work autonomously through the highest-priority unfinished task.**

Stop and ask only when a decision genuinely requires human input, such as:

- selecting an ambiguous dataset
- accepting a questionable medical source
- changing the target taxonomy
- deleting data
- publishing/deploying
- making a clinically consequential assumption

Otherwise, continue. Do NOT repeatedly stop because one small task is complete.

---

## 5. Most Important Rule

Do not optimize for number of files created.

**Optimize for:**

- CORRECTNESS
- TESTABILITY
- REPRODUCIBILITY
- CLINICAL SAFETY
- DATA PROVENANCE
- REAL-DATA VALIDATION
- GOOD UX

Before declaring the project complete, demonstrate the actual end-to-end flow:

```
Clinician
→ creates case
→ enters symptoms/region
→ uploads snake image
→ backend processes image
→ SnakeVision predicts
→ calibration/OOD runs
→ GeoPrior contributes
→ clinical rules contribute
→ evidence fusion produces differential
→ clinician reviews
→ clinician confirms
→ case is saved
→ surveillance record is created
→ epidemiology dashboard reflects the verified case
→ audit trail records the action
```

Use real data where available. **At the end of every working session, update `PROJECT_STATUS.md` with exactly what was actually tested and what remains.**

Start by inspecting the existing repository and producing the current `PROJECT_STATUS.md`. Then continue automatically from the highest-priority unfinished item, using Appendix A below.

---

## Appendix A — Master Priority Order / Phases

Use this order unless the repository reveals a more urgent blocker. Each other part-file maps onto one or more of these phases.

| Phase | Scope | Covered in |
|---|---|---|
| 1 | Finish and validate frontend routing/pages | Part 5 |
| 2 | Run frontend build/type checking and backend integration | Part 5 |
| 3 | Integrate and validate the supplied GBIF occurrence dataset | Part 2 |
| 4 | Create reproducible image dataset ingestion and manifests | Part 2 |
| 5 | Integrate SnakeCLEF/India image datasets | Part 2 |
| 6 | Run actual PyTorch ML training/evaluation | Part 3 |
| 7 | Integrate calibrated/OOD/Grad-CAM inference | Part 3 |
| 8 | Complete clinical knowledge and antivenom reference layer | Part 4 |
| 9 | Complete PostGIS surveillance and audit system | Part 4 (data model) + Part 5 (epidemiology UI) |
| 10 | Integrate constrained RAG/LLM explanations | Part 4 (constraints) |
| 11 | Complete documentation and deployment | Appendix B, below |

## Appendix B — Documentation Deliverables Checklist

Complete documentation **after the core application works** (Phase 11).

At minimum:

- `README.md`
- `ARCHITECTURE.md`
- `DATA_PIPELINE.md`
- `ML.md`
- `CLINICAL_SAFETY.md`
- `API.md`
- `DEPLOYMENT.md`
- `DATA_SOURCES.md`
- `SURVEILLANCE.md`

Include: setup, data provenance, licenses, architecture, model limitations, clinical limitations, reproducibility, testing, deployment, citations.

## Appendix C — Testing Cadence (applies after every phase, every file)

After every significant implementation:

1. Run backend tests
2. Run frontend type checking
3. Run frontend build
4. Test relevant API endpoints
5. Test affected UI route
6. Update `PROJECT_STATUS.md`

If a tool/dependency is unavailable: record it as `BLOCKED`. Do not pretend it worked.

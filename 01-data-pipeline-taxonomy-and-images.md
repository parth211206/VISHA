# Part 2 of 5 — Data Pipeline: GBIF Occurrence Data, Image Datasets & Taxonomy

**India Snakebite Clinical Decision-Support + Epidemiological Surveillance System**

> Maps to Phases 3, 4, 5 in the Master Priority Order (see `00-foundation-and-status.md`, Appendix A). Read Part 1 first — do not start here without having inspected the existing repository and produced/updated `PROJECT_STATUS.md`.

---

## 1. GBIF Occurrence Data (Phase 3)

There is an `occurrence.csv` file obtained from GBIF. **Inspect it yourself before using it** — do not assume its exact contents match the summary below without verifying against the actual file.

Known characteristics from prior inspection:

- approximately 9,766 records
- approximately 8,275 India records
- includes Reptilia and Amphibia
- includes snakes as well as non-snake reptiles
- contains species/genus/country/state/coordinates/event-date and biodiversity metadata

**Treat this as RAW OCCURRENCE DATA.**

Do not feed the entire file directly into the snake image model. Build a reproducible filtering/normalization pipeline:

```
raw occurrence data
→ valid taxonomy
→ snake-only records
→ India-relevant records
→ coordinate validation
→ duplicate handling
→ taxonomy normalization
→ clean GBIF snake occurrence dataset
→ GeoPriorEngine
```

**Preserve the original raw data and never overwrite it.**

---

## 2. Image Datasets (Phase 4 & 5)

The intended image sources are:

1. SnakeCLEF 2021
2. India-specific snake image dataset
3. Additional properly licensed India-focused observations, potentially from iNaturalist

**Do NOT blindly merge these datasets.**

Build this directory structure:

```
data/raw/
data/processed/
data/manifests/
```

Create a **master image manifest** containing at minimum, one row per image:

- `image_id`
- `filepath`
- `source_dataset`
- `source_url`
- `license`
- `species`
- `accepted_species`
- `genus`
- `country`
- `state`
- `observation_id`
- `quality_status`
- `verification_status`
- `split`
- `duplicate_group`

Before training, the pipeline must:

- normalize taxonomy
- detect duplicate images
- detect near-duplicates where feasible
- remove corrupted images
- check class balance
- check label validity
- check train/validation/test leakage
- preserve dataset provenance
- respect image licenses
- generate a reproducible train/validation/test manifest

Do not download or copy enormous datasets unnecessarily if a metadata/CLI-based workflow is better.

---

## 3. Taxonomy (Phase 4, underpins everything)

The project's target taxonomy currently contains **29 species and 20 genera**.

**Create one authoritative taxonomy source.** All datasets must map into that taxonomy.

Handle:

- accepted names
- synonyms
- genus
- family
- medical relevance
- India presence
- high-risk confusion groups

**Do not invent taxonomy.** If a source species cannot be reliably mapped to the project taxonomy: mark it as `UNMAPPED/QUARANTINED` rather than guessing.

---

## Before moving to Part 3

- Re-run the Testing Cadence in `00-foundation-and-status.md`, Appendix C.
- Update `PROJECT_STATUS.md` with exactly what was validated in this phase (e.g., "GBIF pipeline: REAL-DATA VALIDATED" vs. "IMPLEMENTED BUT NOT TESTED") — do not claim a stronger status than what was actually demonstrated.
- Only proceed to ML model development (Part 3) once the manifests and taxonomy mapping are in a state you can honestly call `IMPLEMENTED` or better.

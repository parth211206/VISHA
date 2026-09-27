# Snake Image Dataset Contract

## Purpose

This document defines how the snake image dataset must be interpreted by Claude and by the project's ML pipeline.

## Dataset root

```text
C:\AI_ML_Project\Snake Images
```

The dataset may contain:

```text
train/
    Venomous/
    Non Venomous/

test/
    Venomous/
    Non Venomous/
```

The exact structure must be verified by `dataset_manifest.csv`; do not assume folders exist if the manifest says otherwise.

## Label authority

The label recorded from the dataset folder is the **dataset-provided class label**.

Examples:

- `train/Venomous/...` -> folder label: `Venomous`
- `train/Non Venomous/...` -> folder label: `Non Venomous`

Do not silently change these labels.

## Critical taxonomy rule

The filename is NOT considered a species, genus, family, geographic, or clinical annotation.

Examples such as:

```text
0.jpg
_DSC0413.jpg
604A4956.jpg
random_hash.jpg
```

must not be interpreted as species names.

If species, genus, family, location, source, license, or other metadata is not explicitly present in a verified metadata source, record it as `UNKNOWN` rather than guessing.

## Visual interpretation

Representative images may be inspected to understand image characteristics, image quality, and dataset diversity.

Visual inspection must NOT be used to invent missing ground-truth labels.

A model may later learn visual patterns from the training labels, but those predictions are model outputs and must remain separate from ground-truth metadata.

## Train/test rule

The existing train/test split is authoritative unless a documented data-quality audit identifies a problem.

Do not move images between train and test automatically.

Exact duplicate leakage across train/test must be reported before training.

## Original files

The original JPG/PNG/etc. files are the source data for PyTorch training and inference.

Do not modify, rename, compress, or overwrite the original images as part of dataset inspection.

Derived files should go under:

```text
dataset_documentation/
```

## Required pre-training audit

Before changing or training the ML model, inspect:

1. Total image count
2. Train/test counts
3. Class counts
4. File formats
5. Image dimensions
6. Corrupt/unreadable images
7. Exact duplicate files
8. Exact train/test duplicate leakage
9. Very small images
10. Representative visual samples
11. Any missing or ambiguous labels
12. Whether the dataset actually contains species-level metadata

## Clinical-project safety rule

A binary `Venomous` / `Non Venomous` dataset must NOT automatically be described as a species-identification dataset.

Species/genus classification requires appropriate species/genus ground-truth annotations.

The clinical decision-support system must never treat a binary venom-status classifier as proof of snake species.

## Missing information

When information is unavailable:

```text
UNKNOWN
```

is preferred over inference or fabrication.

## Authority hierarchy

For dataset facts:

1. Actual image files
2. Generated `dataset_manifest.csv`
3. Generated validation/statistical reports
4. Verified external metadata/source documentation
5. Model predictions

Model predictions are never ground truth.

## Reproducibility

Dataset inspection should be reproducible.

The inspector uses a fixed random seed when selecting representative samples.

## Claude behavior

Before writing or changing ML code, Claude should:

1. Read the dataset contract.
2. Read the manifest and reports.
3. Check the actual reported class distribution.
4. Identify limitations and inconsistencies.
5. Ask for clarification only when an unresolved ambiguity materially affects the implementation.
6. Never invent species labels or dataset metadata.
7. Keep dataset facts separate from model predictions.

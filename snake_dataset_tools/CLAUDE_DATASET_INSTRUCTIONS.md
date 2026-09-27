# CLAUDE_DATASET_INSTRUCTIONS.md

You are working on an India-focused snakebite clinical decision-support and epidemiological surveillance project.

This document governs how you must use the snake image dataset.

## First task: DATASET AUDIT ONLY

Before modifying the ML architecture or writing training code, inspect:

- `DATASET_CONTRACT.md`
- `dataset_manifest.csv`
- `dataset_report.json`
- `validation_report.csv`
- `class_distribution.csv`
- `duplicate_report.csv`
- representative contact sheets under `sample_images/`

Your first response/work product should be a dataset audit, not a new model.

## What you must establish

Report:

1. Dataset root and structure
2. Number of images
3. Train/test counts
4. Class counts
5. Image formats
6. Common dimensions
7. Corrupt/unreadable files
8. Exact duplicates
9. Exact train/test leakage
10. Whether species/genus metadata exists
11. Important limitations
12. Any issues that must be fixed before training

Use the generated files as evidence. Do not invent numbers.

## Label discipline

The folders `Venomous` and `Non Venomous` represent the dataset's provided labels.

Do NOT claim that a particular image is a specific snake species merely because it visually resembles one.

Do NOT infer species from filenames.

Do NOT create synthetic species labels.

If species information is absent, state that it is absent.

## ML architecture discipline

This dataset may support a venom-status classification task.

It does NOT automatically provide sufficient ground truth for species-level identification.

Species-level identification must use a separately verified species-labeled dataset or verified metadata.

## File access

The original image dataset remains on the user's local computer.

Do not assume that a CSV containing Windows paths automatically gives you filesystem access.

Use the manifest/reports for dataset understanding. The local Python/PyTorch pipeline is responsible for loading the complete image dataset during training.

## Clinical safety

This project is a clinician-in-the-loop research prototype.

Do not turn model predictions into autonomous diagnosis or antivenom decisions.

Do not invent antivenom mappings.

Do not use an LLM as the authoritative clinical or antivenom engine.

## Required response after audit

End the audit with:

### Confirmed
Facts directly supported by the dataset audit.

### Unknown
Information the dataset does not provide.

### Problems
Data-quality or leakage issues discovered.

### Next implementation step
The smallest justified engineering step based on the audit.

Do not skip the audit.

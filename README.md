# Snake Dataset -> Claude Preparation Package

## What this package does

It creates a structured description of the existing snake image dataset without uploading the complete image collection.

The original images remain on the PC.

## Files

- `dataset_inspector.py` - scans the dataset
- `run_dataset_inspector.bat` - Windows one-click runner
- `DATASET_CONTRACT.md` - rules for interpreting the dataset
- `CLAUDE_DATASET_INSTRUCTIONS.md` - instructions to give Claude

After running the inspector, it creates:

```text
C:\AI_ML_Project\Snake Images\dataset_documentation\
    dataset_manifest.csv
    dataset_report.json
    validation_report.csv
    class_distribution.csv
    duplicate_report.csv
    sample_images\
```

## First-time setup

Open Command Prompt and run:

```text
python -m pip install Pillow
```

Then run:

```text
python dataset_inspector.py
```

or double-click:

```text
run_dataset_inspector.bat
```

The script is configured for:

```text
C:\AI_ML_Project\Snake Images
```

You can also supply another path:

```text
python dataset_inspector.py "D:\Some\Other\Snake Dataset"
```

## Safety

The inspector:

- does not rename original images
- does not move original images
- does not delete original images
- does not overwrite original images
- writes derived documentation to `dataset_documentation`

## Important limitation

The inspector can validate files and folder labels, but it cannot establish that a snake is a particular species merely from its appearance.

Species/genus metadata must come from a verified annotation/source.

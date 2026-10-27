# India taxonomy model — Phase 1

This is an additive implementation bundle. It does not overwrite `BinarySnakeClassifier`, the existing API, frontend, or current model artifacts.

## Why this phase is needed

The currently available `Snake Images` data is labeled only `venomous`/`non_venomous`; its species and genus fields are `UNKNOWN`. It cannot teach a model to identify genus or family. The taxonomy-candidate CSV, by contrast, has taxon labels but points to image files that are not currently extracted. The scripts below bridge those two required parts using the official SnakeCLEF2022 image archive.

## Expected source files

- `data/external/snakeclef2022/SnakeCLEF2022-TrainMetadata.csv`
- `data/taxonomy/india_snakes_taxonomy_v1.yaml`
- An official SnakeCLEF2022 **small-image training ZIP** placed under `data/external/snakeclef2022/archives/`

Official dataset page: https://www.imageclef.org/SnakeCLEF2022. The small-image training archive is listed at approximately 9 GB, compared with about 32 GB for medium and about 110 GB for large images. The script extracts only India-coded images whose species match the project's taxonomy; it does not expand the entire archive.

## Run on Windows PowerShell

From `C:\AI_ML_Project`, first apply the bundle by copying its `ml` files into the corresponding `ml` directories and copying the docs file into `docs` (merge folders; do not replace the repository or existing files).

After obtaining the official small-image archive and placing it in `data\external\snakeclef2022\archives\`, run:

```powershell
cd C:\AI_ML_Project
$archive = Get-ChildItem .\data\external\snakeclef2022\archives\*.zip | Select-Object -First 1
if (-not $archive) { throw 'Place the official SnakeCLEF2022 small-image ZIP in data\external\snakeclef2022\archives first.' }
python .\ml\scripts\extract_india_subset_from_zip.py --archive $archive.FullName
```

Then train the multi-head species/genus/family model:

```powershell
python .\ml\scripts\train_taxonomy_classifier.py --device auto --epochs 12 --batch-size 8
```

The script creates a new timestamped folder under `ml\runs\india_taxonomy_...`; it does not overwrite the current binary checkpoint. It attempts to initialize the EfficientNet feature extractor from the existing binary checkpoint, discarding the binary output head. Class counts below configurable support thresholds are excluded from their respective output head rather than being presented as supported classes.

Use the newly trained checkpoint to test one image:

```powershell
$checkpoint = Get-ChildItem .\ml\runs\india_taxonomy_*\best_model.pt | Sort-Object LastWriteTime -Descending | Select-Object -First 1
python .\ml\scripts\predict_taxonomy_image.py .\Snake Images\test\Venomous\<replace-with-an-existing-image-name>.jpg --checkpoint $checkpoint.FullName --device auto
```

Replace the sample path with a real existing image path; the binary dataset image is only a smoke test and is not taxonomically labeled ground truth.

## Important constraints

- These scripts prepare and train the model only. The existing FastAPI endpoint still reports its old two-class model until a separate, tested API integration change is applied.
- A model prediction is not clinical evidence. No automatic antivenom prescription or dose is produced.
- Training and test splits group images by the top-level observation directory to reduce leakage between multiple photographs of the same observation.
- Review `test_metrics.json`, per-class coverage, and class confusions before integrating this model. The held-out test score is a research metric, not a clinical safety claim.

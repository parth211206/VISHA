import os
import pandas as pd
import torch
from torch.utils.data import DataLoader
import yaml
from sklearn.model_selection import train_test_split
from pathlib import Path

from ml.data.dataset import SnakeImageDataset
from ml.data.manifest_loader import ManifestLoader
from ml.data.transforms import SnakeTransforms
from ml.models.binary_classifier import BinarySnakeClassifier
from ml.training.trainer import BinaryClassifierTrainer
from ml.training.experiment_tracker import ExperimentTracker

def main():
    # Paths
    manifest_path = r"data\manifests\image_manifest_v1_leakage_safe.csv"
    image_root = Path(r"Snake Images")
    config_path = r"ml\config\training_config_prototype.yaml"
    artifacts_dir = r"ml\artifacts"
    experiments_dir = r"ml\runs"

    # Load manifest
    df = pd.read_csv(manifest_path)

    # Helper to normalize path to absolute
    def norm_path(p):
        if os.path.isabs(p):
            return os.path.normpath(p)
        else:
            return os.path.normpath(os.path.join(os.getcwd(), p))

    # Verify all files exist and are readable (should be true after fix)
    missing = []
    for idx, row in df.iterrows():
        p = norm_path(row['absolute_path'])
        if not os.path.isfile(p):
            missing.append((idx, p))
    if missing:
        print("ERROR: Missing files referenced by manifest:")
        for idx, p in missing[:5]:
            print(f"  Row {idx}: {p}")
        return

    # Get active training and test rows based on flags
    train_df = df[(df['use_in_training'] == True) & (df['split'] == 'train')].copy()
    test_df = df[(df['use_in_evaluation'] == True) & (df['split'] == 'test')].copy()

    print(f"Active training rows: {len(train_df)}")
    print(f"Active test rows: {len(test_df)}")

    # Stratified split of training data into train and validation (15% validation)
    # We'll split by the binary_label column
    train_subset, val_subset = train_test_split(
        train_df,
        test_size=0.15,
        random_state=42,
        stratify=train_df['binary_label']
    )
    print(f"Training subset: {len(train_subset)} rows")
    print(f"Validation subset: {len(val_subset)} rows")

    # Define transforms
    train_transform = SnakeTransforms.from_config(Path(config_path), split="train")
    val_transform = SnakeTransforms.from_config(Path(config_path), split="val")

    # Create datasets
    train_dataset = SnakeImageDataset(
        manifest=train_subset,
        image_root=image_root,
        transform=train_transform,
        label_column="binary_label",
        label_map={"non_venomous": 0, "venomous": 1}
    )
    val_dataset = SnakeImageDataset(
        manifest=val_subset,
        image_root=image_root,
        transform=val_transform,
        label_column="binary_label",
        label_map={"non_venomous": 0, "venomous": 1}
    )
    test_dataset = SnakeImageDataset(
        manifest=test_df,
        image_root=image_root,
        transform=val_transform,  # use validation transform for test
        label_column="binary_label",
        label_map={"non_venomous": 0, "venomous": 1}
    )

    # Create data loaders
    config = yaml.safe_load(open(config_path))
    batch_size = config['training']['batch_size']
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # Device
    device = torch.device("cpu")
    if torch.cuda.is_available():
        device = torch.device("cuda")
    print(f"Using device: {device}")

    # Load model from config
    model = BinarySnakeClassifier.from_config(Path(config_path))
    # Freeze backbone for faster training (only train the classifier head)
    model.freeze_backbone()
    model = model.to(device)

    # Experiment tracker
    tracker = ExperimentTracker(Path(experiments_dir))
    experiment_id = "binary_prototype_" + pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

    # Trainer
    trainer = BinaryClassifierTrainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        config=config,
        tracker=tracker,
        experiment_id=experiment_id,
        device=device
    )

    # Train
    print("Starting training...")
    result = trainer.train()
    print("Training completed.")

    # Best model path from the trainer
    best_model_path = tracker.experiments_dir / experiment_id / "best_model.pt"
    print(f"Best model saved at: {best_model_path}")

    # Ensure artifacts directory exists
    os.makedirs(artifacts_dir, exist_ok=True)
    # Copy best model to the expected location
    import shutil
    dest_path = Path(artifacts_dir) / "binary_classifier_latest.pt"
    shutil.copy(best_model_path, dest_path)
    print(f"Copied best model to: {dest_path}")

    # Evaluate on test set
    print("Evaluating on test set...")
    # We'll reuse the trainer's validation loop but on test set
    # We can create a temporary trainer for test or just use the model.
    model.eval()
    all_labels = []
    all_preds = []
    all_probs = []
    with torch.no_grad():
        for inputs, labels, _ in test_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            logits = model(inputs)
            probs = torch.softmax(logits, dim=1)
            preds = torch.argmax(probs, dim=1)
            all_labels.extend(labels.cpu().numpy())
            all_preds.extend(preds.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    from ml.evaluation.metrics import compute_binary_metrics
    metrics = compute_binary_metrics(
        np.array(all_labels), np.array(all_preds), np.array(all_probs)
    )
    print("Test set metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Also compute confusion matrix
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(all_labels, all_preds)
    print("Confusion Matrix:")
    print(cm)
    print("Labels: [non_venomous, venomous]")

    # Check that probabilities are valid
    all_probs = np.array(all_probs)
    prob_sums = all_probs.sum(axis=1)
    if not np.allclose(prob_sums, 1.0, atol=1e-5):
        print("WARNING: Probability sums are not close to 1.")
    else:
        print("Probability sums are valid (sum to 1).")
    if (all_probs < 0).any() or (all_probs > 1).any():
        print("ERROR: Probabilities out of [0,1] range.")
    else:
        print("Probabilities are within [0,1].")

    print("Done.")

if __name__ == "__main__":
    import numpy as np
    main()
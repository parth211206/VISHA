import torch
from pathlib import Path
import numpy as np
from PIL import Image
from ml.data.dataset import SnakeImageDataset
from ml.data.transforms import SnakeTransforms
from ml.models.binary_classifier import BinarySnakeClassifier
import yaml

def main():
    # Load the trained model
    config_path = Path("ml/config/training_config_prototype.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    model = BinarySnakeClassifier.from_config(config_path)
    checkpoint_path = Path("ml/artifacts/binary_classifier_latest.pt")
    state_dict = torch.load(checkpoint_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    # Load the leakage-safe manifest to get a few test images
    manifest_path = Path("data/manifests/image_manifest_v1_leakage_safe.csv")
    import pandas as pd
    df = pd.read_csv(manifest_path)
    test_df = df[(df['use_in_evaluation'] == True) & (df['split'] == 'test')]

    # Select a few images (say 2 from each class)
    non_venomous = test_df[test_df['binary_label'] == 'non_venomous'].head(2)
    venomous = test_df[test_df['binary_label'] == 'venomous'].head(2)
    sample_df = pd.concat([non_venomous, venomous])

    # Prepare transform
    transform = SnakeTransforms.from_config(config_path, split="val")

    print("Running inference on sample held-out images:")
    print("=" * 50)
    for idx, row in sample_df.iterrows():
        img_path = Path(row['absolute_path'])
        image = Image.open(img_path).convert("RGB")
        tensor = transform(image).unsqueeze(0)  # Add batch dimension

        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0)
            pred_idx = torch.argmax(probs).item()
            pred_label = "venomous" if pred_idx == 1 else "non_venomous"
            true_label = row['binary_label']

        print(f"Image: {img_path.name}")
        print(f"  True label: {true_label}")
        print(f"  Predicted: {pred_label} (non_venomous: {probs[0]:.4f}, venomous: {probs[1]:.4f})")
        print(f"  Correct: {pred_label == true_label}")
        print()

    print("Inference verification complete.")

if __name__ == "__main__":
    main()
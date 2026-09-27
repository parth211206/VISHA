import pytest
import pandas as pd
from pathlib import Path

MANIFESTS_DIR = Path("data/manifests")

def test_image_manifest_binary_labels_normalized():
    df = pd.read_csv(MANIFESTS_DIR / "image_manifest_v1.csv")
    labels = df["binary_label"].unique()
    assert set(labels).issubset({"venomous", "non_venomous"})

def test_image_manifest_no_species_invented():
    df = pd.read_csv(MANIFESTS_DIR / "image_manifest_v1.csv")
    assert all(df["species_label"] == "UNKNOWN")

def test_usable_training_count():
    df = pd.read_csv(MANIFESTS_DIR / "image_manifest_v1.csv")
    train_usable = len(df[(df["split"] == "train") & (df["use_in_training"] == True)])
    assert train_usable == 1773  # 1775 total - 2 intra_split duplicates

def test_usable_evaluation_count():
    df = pd.read_csv(MANIFESTS_DIR / "image_manifest_v1.csv")
    test_usable = len(df[(df["split"] == "test") & (df["use_in_evaluation"] == True)])
    assert test_usable == 264  # 269 total - 5 leakage excluded

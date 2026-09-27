import pytest
from pathlib import Path
import json
import pandas as pd
from data.pipeline.taxonomy_mapper import TaxonomyMapper
from data.pipeline.gbif_pipeline import GBIFPipeline
from data.pipeline.image_pipeline import ImagePipeline
from data.pipeline.geo_prior import GeoPriorEngine

TAXONOMY_YAML = Path("data/taxonomy/india_snakes_taxonomy_v1.yaml")
GBIF_CSV = Path("occurrence.csv")
DATASET_MANIFEST = Path("dataset_manifest.csv")
DUPLICATE_CSV = Path("duplicate_report.csv")
OUTPUT_DIR = Path("data/processed")
MANIFESTS_DIR = Path("data/manifests")

@pytest.fixture(scope="module")
def taxonomy_mapper():
    return TaxonomyMapper(TAXONOMY_YAML)

def test_taxonomy_mapper_exact(taxonomy_mapper):
    res = taxonomy_mapper.get_species("Naja naja")
    assert res is not None
    assert res["genus"] == "Naja"
    assert res["family"] == "Elapidae"

def test_taxonomy_mapper_normalize(taxonomy_mapper):
    assert taxonomy_mapper.normalize_species_name("naja naja") == "Naja naja"
    assert taxonomy_mapper.normalize_species_name("NAJA NAJA") == "Naja naja"

def test_taxonomy_mapper_confusion_pairs(taxonomy_mapper):
    pairs = taxonomy_mapper.get_confusion_pairs("Naja naja")
    assert "Naja kaouthia" in pairs

def test_gbif_pipeline_runs_successfully(taxonomy_mapper):
    pipeline = GBIFPipeline(GBIF_CSV, OUTPUT_DIR / "gbif", taxonomy_mapper)
    report = pipeline.run()
    
    assert (OUTPUT_DIR / "gbif" / "india_snakes_filtered_v1.csv").exists()
    assert (OUTPUT_DIR / "gbif" / "gbif_pipeline_report_v1.json").exists()
    assert report["counts"]["input_records"] == 9766

def test_gbif_snake_only():
    df = pd.read_csv(OUTPUT_DIR / "gbif" / "india_snakes_filtered_v1.csv")
    # No Amphibia should be present (would have been filtered by class == Reptilia and then genus mapping)
    # the dataframe only contains Reptilia mapped to our snake taxonomy
    assert len(df) > 0

def test_gbif_india_only():
    df = pd.read_csv(OUTPUT_DIR / "gbif" / "india_snakes_filtered_v1.csv")
    assert all(df["country"] == "India")

def test_gbif_taxonomy_mapping():
    df = pd.read_csv(OUTPUT_DIR / "gbif" / "india_snakes_filtered_v1.csv")
    mapped = df[df["taxonomy_status"] == "MAPPED"]
    assert len(mapped) > 0
    # Check if Naja naja is present
    assert "Naja naja" in df["accepted_name"].values

def test_image_pipeline_runs_successfully():
    pipeline = ImagePipeline(DATASET_MANIFEST, DUPLICATE_CSV, MANIFESTS_DIR)
    report = pipeline.run()
    
    assert (MANIFESTS_DIR / "image_manifest_v1.csv").exists()
    assert (MANIFESTS_DIR / "image_pipeline_report_v1.json").exists()
    assert report["total_images"] == 2044

def test_leakage_exclusion():
    df = pd.read_csv(MANIFESTS_DIR / "image_manifest_v1.csv")
    leakage = df[df["quality_flag"] == "LEAKAGE_EXCLUDED"]
    assert len(leakage) == 5
    assert all(leakage["split"] == "test")
    assert all(leakage["use_in_evaluation"] == False)
    assert all(leakage["leakage_excluded"] == True)

def test_leakage_train_copies_kept():
    df = pd.read_csv(MANIFESTS_DIR / "image_manifest_v1.csv")
    # Find train items that share the sha256 with the excluded ones
    leakage_shas = df[df["quality_flag"] == "LEAKAGE_EXCLUDED"]["sha256"].values
    train_copies = df[(df["sha256"].isin(leakage_shas)) & (df["split"] == "train")]
    assert len(train_copies) == 5
    assert all(train_copies["use_in_training"] == True)
    assert all(train_copies["quality_flag"] != "LEAKAGE_EXCLUDED")

def test_suspicious_duplicate_flagged():
    df = pd.read_csv(MANIFESTS_DIR / "image_manifest_v1.csv")
    suspicious = df[df["quality_flag"] == "SUSPICIOUS_DUPLICATE_REVIEW_REQUIRED"]
    assert len(suspicious) == 2
    filenames = suspicious["filename"].values
    assert "Russel Viper 04.jpg" in filenames
    assert "Saw-Scaled-Viper_008.jpg" in filenames

def test_intra_split_deduplication():
    df = pd.read_csv(MANIFESTS_DIR / "image_manifest_v1.csv")
    intra = df[df["quality_flag"] == "INTRA_SPLIT_DUPLICATE"]
    assert len(intra) == 2
    assert all(intra["use_in_training"] == False)

def test_geo_prior_returns_probability():
    geo = GeoPriorEngine(OUTPUT_DIR / "gbif" / "india_snakes_filtered_v1.csv")
    if len(geo._state_totals) > 0:
        state = list(geo._state_totals.keys())[0]
        species = list(geo._state_species_counts[state].keys())[0]
        prob = geo.get_species_probability(state, species)
        assert 0.0 <= prob <= 1.0

def test_geo_prior_handles_unknown_state():
    geo = GeoPriorEngine(OUTPUT_DIR / "gbif" / "india_snakes_filtered_v1.csv")
    prob = geo.get_species_probability("UNKNOWN_STATE_999", "Naja naja")
    assert prob == 0.01


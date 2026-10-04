import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class ImagePipeline:
    def __init__(self, manifest_csv: Path, duplicate_csv: Path, output_dir: Path):
        self.manifest_csv = manifest_csv
        self.duplicate_csv = duplicate_csv
        self.output_dir = output_dir

        self.output_csv = self.output_dir / "image_manifest_v1.csv"
        self.output_report = self.output_dir / "image_pipeline_report_v1.json"

    def run(self):
        logger.info(f"Starting Image pipeline reading from {self.manifest_csv}")

        df = pd.read_csv(self.manifest_csv)

        report = {
            "timestamp": datetime.now().isoformat(),
            "pipeline_version": "1.0.0",
            "total_images": len(df),
            "leakage_excluded_count": 0,
            "intra_split_duplicates": 0,
            "suspicious_review_required": 0,
            "train_usable": 0,
            "test_usable": 0,
        }

        # Initialize new columns
        df["quality_flag"] = "OK"
        df["leakage_excluded"] = False
        df["use_in_training"] = True
        df["use_in_evaluation"] = True
        df["duplicate_group_id"] = ""
        df["source_dataset"] = "india_binary_v1"
        df["species_label"] = "UNKNOWN"
        df["genus_label"] = "UNKNOWN"
        df["binary_label"] = df["folder_label"].str.lower().str.replace(" ", "_")
        df["license"] = "UNKNOWN"
        df["geographic_provenance"] = "UNKNOWN"

        # Leakage groups from inspection
        leakage_shas = [
            "5dc6a4f1652834fe2fa4574ca204bb83b9e566ec17443c99ad466d3b5d25ee35",
            "03c012eaad006d95f57b3d68f1837526e1a8ee3c9d8db745dcb9ed48f21eb6ab",
            "ce2071a9f9aeed0e9a430e022dbbd6bc677d5a6a3ddf1d87297fb151b5d8a18b",
            "eb6140026301604d43bfba6f4912a25c3cd9e9d1a688ff6df8d0f139152c70e0",
            "8fc03a6f54d518dd4fd74dc9670fa81f7d4f423dffc470406e3fbf9883b810b5",
        ]

        # Apply leakage rules
        for sha in leakage_shas:
            mask = df["sha256"] == sha
            # mark the test split copies as leakage_excluded
            test_mask = mask & (df["split"] == "test")
            df.loc[test_mask, "quality_flag"] = "LEAKAGE_EXCLUDED"
            df.loc[test_mask, "leakage_excluded"] = True
            df.loc[test_mask, "use_in_evaluation"] = False
            report["leakage_excluded_count"] += int(test_mask.sum())

            df.loc[mask, "duplicate_group_id"] = sha[:12]

        # Suspicious duplicate logic
        suspicious_sha = "19c1a5872200abdc6f6a97bada26096f8061ac78d7156a330f681da7f5886fe1"
        susp_mask = df["sha256"] == suspicious_sha
        df.loc[susp_mask, "quality_flag"] = "SUSPICIOUS_DUPLICATE_REVIEW_REQUIRED"
        df.loc[susp_mask, "duplicate_group_id"] = suspicious_sha[:12]
        report["suspicious_review_required"] = int(susp_mask.sum())

        # Intra-split duplicates
        intra_shas = [
            "ffdbcab66ac7a0a9d40015dd69558733467ebc6d6e9993423a8f9e697c5fd25f",
            "dfb5764f80318cf95ca0175798326216b83f7fe7a5a0538c33395793311d72dc",
        ]

        for sha in intra_shas:
            mask = df["sha256"] == sha
            df.loc[mask, "duplicate_group_id"] = sha[:12]

            # find all paths in group
            group_indices = df[mask].sort_values("filename").index
            if len(group_indices) > 1:
                # keep first, exclude rest
                exclude_indices = group_indices[1:]
                df.loc[exclude_indices, "quality_flag"] = "INTRA_SPLIT_DUPLICATE"
                df.loc[exclude_indices, "use_in_training"] = False
                df.loc[exclude_indices, "use_in_evaluation"] = False
                report["intra_split_duplicates"] += len(exclude_indices)

        # Small image check
        small_mask = (df["width"] < 100) | (df["height"] < 100)
        df.loc[small_mask & (df["quality_flag"] == "OK"), "quality_flag"] = "SMALL_IMAGE"

        # Update evaluation usage
        df.loc[df["leakage_excluded"] == True, "use_in_evaluation"] = False

        report["train_usable"] = int(
            ((df["split"] == "train") & (df["use_in_training"] == True)).sum()
        )
        report["test_usable"] = int(
            ((df["split"] == "test") & (df["use_in_evaluation"] == True)).sum()
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.output_csv, index=False)

        with open(self.output_report, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Image pipeline completed. Output: {self.output_csv}")
        return report

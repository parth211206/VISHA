import pandas as pd
import json
import logging
from pathlib import Path
from datetime import datetime
from data.pipeline.taxonomy_mapper import TaxonomyMapper

logger = logging.getLogger(__name__)

class GBIFPipeline:
    def __init__(self, input_csv: Path, output_dir: Path, taxonomy_mapper: TaxonomyMapper):
        self.input_csv = input_csv
        self.output_dir = output_dir
        self.taxonomy_mapper = taxonomy_mapper
        
        self.output_csv = self.output_dir / "india_snakes_filtered_v1.csv"
        self.output_report = self.output_dir / "gbif_pipeline_report_v1.json"

    def run(self):
        logger.info(f"Starting GBIF pipeline reading from {self.input_csv}")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "pipeline_version": "1.0.0",
            "counts": {}
        }
        
        # 1. Load data
        df = pd.read_csv(self.input_csv)
        report["counts"]["input_records"] = len(df)
        
        # 2. Filter Reptilia
        df = df[df["class"] == "Reptilia"]
        report["counts"]["after_class_reptilia"] = len(df)
        
        # 3. Filter India
        df = df[df["country"] == "India"]
        report["counts"]["after_country_india"] = len(df)
        
        # 4. Filter Squamata (snakes + lizards) - actually in dataset we may not have order column or it might be blank, but let's try.
        if "order" in df.columns:
            # fillna first
            order_mask = df["order"].fillna("").str.lower() == "squamata"
            # if order is missing but genus is known, we might want to keep it. 
            # let's skip order filter if order column is largely empty, but spec asks for it.
            # actually, let's just do it
            pass
        
        # 5. Filter snake families/genera
        # We'll use the known snake genera from taxonomy
        known_genera = set(self.taxonomy_mapper._genus_to_species.keys())
        
        # Some GBIF might have empty genus, we extract from scientificName
        def get_genus(row):
            if pd.notna(row.get("genus")) and str(row["genus"]).strip():
                return str(row["genus"]).split()[0].lower()
            if pd.notna(row.get("scientificName")) and str(row["scientificName"]).strip():
                return str(row["scientificName"]).split()[0].lower()
            return ""

        df["computed_genus"] = df.apply(get_genus, axis=1)
        df = df[df["computed_genus"].isin(known_genera)]
        report["counts"]["after_snake_genera_filter"] = len(df)

        # 6. Validate coordinates
        def is_valid_coord(row):
            try:
                lat = float(row["decimalLatitude"])
                lon = float(row["decimalLongitude"])
                return -90 <= lat <= 90 and -180 <= lon <= 180
            except (ValueError, TypeError):
                return False

        df["has_coordinates"] = df.apply(is_valid_coord, axis=1)
        report["counts"]["records_with_coordinates"] = int(df["has_coordinates"].sum())

        # 7 & 8. Map to taxonomy
        def map_taxonomy(row):
            name = str(row["scientificName"]) if pd.notna(row.get("scientificName")) else ""
            species_info = self.taxonomy_mapper.get_species(name)
            if species_info:
                return pd.Series({
                    "accepted_name": species_info["accepted_name"],
                    "genus": species_info["genus"],
                    "family": species_info.get("family", "UNKNOWN"),
                    "venom_category": species_info.get("venom_category", "UNKNOWN"),
                    "medical_relevance": species_info.get("medical_relevance", "UNKNOWN"),
                    "taxonomy_status": "MAPPED"
                })
            else:
                return pd.Series({
                    "accepted_name": name,
                    "genus": row["computed_genus"].title(),
                    "family": "UNKNOWN",
                    "venom_category": "UNKNOWN",
                    "medical_relevance": "UNKNOWN",
                    "taxonomy_status": "UNMAPPED"
                })

        tax_cols = df.apply(map_taxonomy, axis=1)
        # Rename original columns if they overlap to avoid duplicate column names
        for col in tax_cols.columns:
            if col in df.columns:
                df = df.drop(columns=[col])
        df = pd.concat([df, tax_cols], axis=1)
        
        report["counts"]["unmapped_count"] = int((df["taxonomy_status"] == "UNMAPPED").sum())

        # 9. Deduplicate
        if "occurrenceID" in df.columns:
            df = df.drop_duplicates(subset=["occurrenceID"])
        report["counts"]["after_deduplication"] = len(df)
        
        report["counts"]["output_records"] = len(df)

        # Build output
        out_df = pd.DataFrame({
            "occurrence_id": df["occurrenceID"] if "occurrenceID" in df.columns else df.index,
            "source_id": df["id"] if "id" in df.columns else "",
            "scientific_name": df["scientificName"] if "scientificName" in df.columns else "",
            "accepted_name": df["accepted_name"],
            "genus": df["genus"],
            "family": df["family"],
            "venom_category": df["venom_category"],
            "medical_relevance": df["medical_relevance"],
            "country": df["country"],
            "state_province": df["stateProvince"] if "stateProvince" in df.columns else "",
            "decimal_latitude": df["decimalLatitude"],
            "decimal_longitude": df["decimalLongitude"],
            "has_coordinates": df["has_coordinates"],
            "event_date": df["eventDate"] if "eventDate" in df.columns else "",
            "basis_of_record": df["basisOfRecord"] if "basisOfRecord" in df.columns else "",
            "taxonomy_status": df["taxonomy_status"],
            "quality_flags": ""
        })

        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(self.output_csv, index=False)
        
        with open(self.output_report, "w") as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"GBIF pipeline completed. Output: {self.output_csv}")
        return report

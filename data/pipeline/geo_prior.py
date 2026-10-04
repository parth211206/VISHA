import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class GeoPriorEngine:
    def __init__(self, gbif_csv: Path):
        self.gbif_csv = gbif_csv
        self._df = None
        self._state_species_counts = {}
        self._state_totals = {}
        self._total_records = 0
        self.load()

    def load(self):
        if not self.gbif_csv.exists():
            logger.warning(
                f"GBIF data not found at {self.gbif_csv}. GeoPrior will return uniform probabilities."
            )
            return

        self._df = pd.read_csv(self.gbif_csv)
        self._df = self._df[self._df["taxonomy_status"] == "MAPPED"]
        self._total_records = len(self._df)

        # Aggregate by state and species
        grouped = self._df.groupby(["state_province", "accepted_name"]).size()
        for (state, species), count in grouped.items():
            state = str(state).strip().upper()
            if state not in self._state_species_counts:
                self._state_species_counts[state] = {}
                self._state_totals[state] = 0

            self._state_species_counts[state][species] = count
            self._state_totals[state] += count

    def get_species_probability(self, state: str, species: str) -> float:
        """Returns the normalized presence probability of a species in a state based on GBIF records."""
        if not state or not species:
            return 0.0

        state = state.strip().upper()
        if state not in self._state_species_counts:
            # We don't have data for this state, fallback to a small prior
            return 0.01

        species_count = self._state_species_counts[state].get(species, 0)
        total_count = self._state_totals[state]

        if total_count == 0:
            return 0.01

        # Add Laplace smoothing
        return (species_count + 1) / (total_count + len(self._state_species_counts[state]))

    def get_plausible_species(self, state: str, top_n: int = 10) -> list[dict]:
        if not state:
            return []

        state = state.strip().upper()
        if state not in self._state_species_counts:
            return []

        species_counts = self._state_species_counts[state]
        total = self._state_totals[state]

        sorted_species = sorted(species_counts.items(), key=lambda x: x[1], reverse=True)

        results = []
        for sp, count in sorted_species[:top_n]:
            results.append(
                {"species": sp, "count": count, "probability": count / total if total > 0 else 0}
            )

        return results

    def get_coverage_report(self) -> dict:
        return {
            "total_records": self._total_records,
            "states_covered": len(self._state_totals),
            "state_record_counts": self._state_totals,
            "sparsity_warning": self._total_records < 1000 or len(self._state_totals) < 5,
        }

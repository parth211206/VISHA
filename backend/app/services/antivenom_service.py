"""Evidence-gated lookup for the Snakebite CDS antivenom references."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.antivenom import AntivenomReference, VerificationStatus

logger = logging.getLogger(__name__)

ELIGIBLE_STATUSES = {
    VerificationStatus.SOURCE_VERIFIED,
    VerificationStatus.CLINICIAN_REVIEWED,
}

PLACEHOLDER_VALUES = {
    "",
    "placeholder",
    "source_required",
    "null",
    "none",
    "n/a",
}


class AntivenomService:
    """Load reference records and return only sufficiently documented entries.

    A returned record is a reference for clinician review, not a treatment
    recommendation. Empty, unverified, and placeholder records are excluded.
    """

    def __init__(self, yaml_path: Optional[Path] = None):
        project_root = Path(__file__).resolve().parents[3]

        if yaml_path is not None:
            self.yaml_path = Path(yaml_path)
        else:
            configured_path = Path(
                get_settings().dataset.antivenom_reference_file
            )
            legacy_path = (
                project_root
                / "data"
                / "antivenom"
                / "antivenom_reference.yaml"
            )

            if configured_path.is_file():
                self.yaml_path = configured_path
            elif legacy_path.is_file():
                self.yaml_path = legacy_path
                logger.warning(
                    "Configured antivenom reference file is missing: %s. "
                    "Using the legacy file for compatibility; its records "
                    "must still pass the reference eligibility checks.",
                    configured_path,
                )
            else:
                self.yaml_path = configured_path

        self.entries: list[AntivenomReference] = []
        self._load()

    def _load(self) -> None:
        """Load and validate the YAML file without accepting malformed rows."""
        if not self.yaml_path.is_file():
            logger.warning(
                "Antivenom reference file not found: %s",
                self.yaml_path,
            )
            return

        try:
            with self.yaml_path.open("r", encoding="utf-8") as stream:
                raw = yaml.safe_load(stream)
        except (OSError, yaml.YAMLError):
            logger.exception(
                "Could not load antivenom reference file: %s",
                self.yaml_path,
            )
            return

        if raw is None:
            return

        if not isinstance(raw, list):
            logger.error(
                "Expected a YAML list in antivenom reference file: %s",
                self.yaml_path,
            )
            return

        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                logger.warning(
                    "Skipping malformed antivenom reference row %d.",
                    index,
                )
                continue

            try:
                entry = AntivenomReference.model_validate(item)
            except ValidationError:
                logger.warning(
                    "Skipping invalid antivenom reference row %d.",
                    index,
                    exc_info=True,
                )
                continue

            self.entries.append(entry)

        logger.info(
            "Loaded %d antivenom reference records from %s.",
            len(self.entries),
            self.yaml_path,
        )

    @staticmethod
    def _normalise(value: Optional[str]) -> str:
        """Normalise case and whitespace for comparisons."""
        return " ".join((value or "").casefold().split())

    @classmethod
    def _populated(cls, value: Optional[str]) -> bool:
        """Reject missing values and common placeholder strings."""
        return cls._normalise(value) not in PLACEHOLDER_VALUES

    @classmethod
    def _eligible(cls, entry: AntivenomReference) -> bool:
        """Require a traceable, populated, explicitly verified reference."""
        if entry.verification_status not in ELIGIBLE_STATUSES:
            return False

        if not cls._populated(entry.product_name):
            return False

        if not cls._populated(entry.source_citation):
            return False

        if not entry.target_species:
            return False

        return all(cls._populated(species) for species in entry.target_species)

    @classmethod
    def _matches_genus(
        cls,
        entry: AntivenomReference,
        requested_genus: str,
    ) -> bool:
        """Compare the genus token rather than using a string prefix."""
        genus = cls._normalise(requested_genus)

        if not genus:
            return True

        return any(
            cls._normalise(species).split()[0] == genus
            for species in entry.target_species
            if cls._normalise(species)
        )

    @classmethod
    def _matches_state(
        cls,
        entry: AntivenomReference,
        requested_state: str,
    ) -> bool:
        """Apply geographic filtering, including explicitly India-wide scopes."""
        state = cls._normalise(requested_state)
        scope = cls._normalise(entry.geographic_scope)

        if not state:
            return True

        if not scope:
            return False

        india_wide_scopes = {
            "india",
            "all india",
            "pan india",
            "pan-india",
            "india-wide",
        }

        if scope in india_wide_scopes:
            return True

        scope_items = {
            item.strip()
            for item in scope.replace("|", ";").split(";")
            if item.strip()
        }

        return state in scope_items

    async def lookup(
        self,
        species: Optional[str] = None,
        genus: Optional[str] = None,
        state: Optional[str] = None,
    ) -> list[AntivenomReference]:
        """Return eligible reference entries matching the supplied filters."""
        requested_species = self._normalise(species)

        results: list[AntivenomReference] = []

        for entry in self.entries:
            if not self._eligible(entry):
                continue

            if requested_species:
                target_species = {
                    self._normalise(item)
                    for item in entry.target_species
                }
                if requested_species not in target_species:
                    continue

            if genus and not self._matches_genus(entry, genus):
                continue

            if state and not self._matches_state(entry, state):
                continue

            results.append(entry)

        return results
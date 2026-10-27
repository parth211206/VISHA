from pathlib import Path

import yaml
from pydantic import ValidationError

from app.schemas.clinical_reference import (
    ClinicalReference,
    ClinicalReferenceList,
)


class ClinicalReferencesService:
    """Load and serve validated clinical guideline references."""

    def __init__(self, yaml_path: Path | None = None) -> None:
        if yaml_path is None:
            project_root = Path(__file__).resolve().parents[3]
            yaml_path = (
                project_root
                / "data"
                / "clinical_references"
                / "snakebite_guidelines.yaml"
            )

        self.yaml_path = Path(yaml_path)
        self._entries: list[ClinicalReference] | None = None
        self._load()

    def _load(self) -> None:
        """Load and validate the reference catalogue."""
        if not self.yaml_path.is_file():
            raise FileNotFoundError(
                f"Clinical reference catalogue not found: {self.yaml_path}"
            )

        try:
            with self.yaml_path.open("r", encoding="utf-8") as file:
                raw = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            raise ValueError(
                f"Malformed clinical reference YAML: {self.yaml_path}"
            ) from exc

        if not isinstance(raw, list):
            raise ValueError(
                "Clinical reference catalogue must contain a YAML list."
            )

        if not raw:
            raise ValueError("Clinical reference catalogue is empty.")

        entries: list[ClinicalReference] = []
        seen_ids: set[str] = set()

        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Clinical reference entry {index} must be a mapping."
                )

            try:
                entry = ClinicalReference(**item)
            except ValidationError as exc:
                raise ValueError(
                    f"Invalid clinical reference entry {index}: {exc}"
                ) from exc

            if entry.reference_id in seen_ids:
                raise ValueError(
                    f"Duplicate reference ID: {entry.reference_id}"
                )

            seen_ids.add(entry.reference_id)
            entries.append(entry)

        self._entries = entries

    def list_references(self) -> ClinicalReferenceList:
        """Return validated references and their total count."""
        if self._entries is None:
            self._load()

        return ClinicalReferenceList(
            entries=self._entries,
            total=len(self._entries),
        )
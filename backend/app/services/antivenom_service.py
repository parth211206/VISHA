from pathlib import Path
from typing import List, Optional

import yaml

from app.schemas.antivenom import AntivenomReference


class AntivenomService:
    def __init__(self, yaml_path: Path = Path("data/antivenom/antivenom_reference.yaml")):
        self.yaml_path = yaml_path
        self._load()

    def _load(self) -> None:
        if not self.yaml_path.exists():
            self.entries = []
            return
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or []
        self.entries = [AntivenomReference(**e) for e in raw]

    async def lookup(
        self,
        species: Optional[str] = None,
        genus: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[AntivenomReference]:
        results = []
        for entry in self.entries:
            if species and entry.target_species and species not in entry.target_species:
                continue
            if (
                genus
                and entry.target_species
                and not any(s.startswith(genus) for s in entry.target_species)
            ):
                continue
            if state and entry.geographic_scope and state not in entry.geographic_scope:
                continue
            results.append(entry)
        return results

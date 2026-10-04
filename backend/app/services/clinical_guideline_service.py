from pathlib import Path
from typing import List, Optional

import yaml

from app.schemas.clinical_guideline import ClinicalGuideline


class ClinicalGuidelineService:
    def __init__(self, yaml_path: Path = Path("data/clinical/clinical_guidelines.yaml")):
        self.yaml_path = yaml_path
        self._load()

    def _load(self) -> None:
        if not self.yaml_path.exists():
            self.entries = []
            return
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or []
        self.entries = [ClinicalGuideline(**e) for e in raw]

    async def search(
        self,
        topic: Optional[str] = None,
    ) -> List[ClinicalGuideline]:
        results = []
        for entry in self.entries:
            if topic and entry.topic and topic.lower() not in entry.topic.lower():
                continue
            results.append(entry)
        return results

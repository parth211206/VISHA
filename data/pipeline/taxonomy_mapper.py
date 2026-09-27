import yaml
from pathlib import Path

class TaxonomyMapper:
    def __init__(self, taxonomy_path: Path):
        self.taxonomy_path = taxonomy_path
        self._taxonomy = None
        self._name_to_species = {}
        self._snakeclef_to_species = {}
        self._genus_to_species = {}
        self.load()
        
    def load(self):
        with open(self.taxonomy_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self._taxonomy = data
            
            for item in data.get("species", []):
                s_name = item["species"].lower()
                a_name = item["accepted_name"].lower()
                self._name_to_species[s_name] = item
                self._name_to_species[a_name] = item
                
                sc_name = item.get("snakeclef_binomial")
                if sc_name:
                    self._snakeclef_to_species[sc_name.lower()] = item
                    
                genus = item["genus"].lower()
                if genus not in self._genus_to_species:
                    self._genus_to_species[genus] = []
                self._genus_to_species[genus].append(item)

    def get_species(self, name: str) -> dict | None:
        if not name: return None
        return self._name_to_species.get(name.lower())

    def get_genus(self, genus: str) -> list[dict]:
        if not genus: return []
        return self._genus_to_species.get(genus.lower(), [])

    def normalize_species_name(self, name: str) -> str | None:
        species_info = self.get_species(name)
        if species_info:
            return species_info["accepted_name"]
        return None

    def is_india_relevant(self, species: str) -> bool:
        species_info = self.get_species(species)
        if species_info:
            return species_info.get("india_present", False)
        return False

    def get_confusion_pairs(self, species: str) -> list[str]:
        species_info = self.get_species(species)
        if species_info:
            return species_info.get("confusion_pairs", [])
        return []

    def map_from_snakeclef(self, binomial: str) -> dict | None:
        if not binomial: return None
        return self._snakeclef_to_species.get(binomial.lower())

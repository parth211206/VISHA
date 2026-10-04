from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "CHANGE_ME_to_a_long_random_string_at_least_32_chars"


class DatabaseSettings(BaseModel):
    url: str = "postgresql+asyncpg://snakebite:snakebite_dev_password@localhost:5432/snakebite_dev"
    pool_size: int = 10
    max_overflow: int = 20


class DatasetSettings(BaseModel):
    raw_root: Path = Path(r"C:\AI_ML_Project\Snake Images")
    raw_occurrence_csv: Path = Path(r"C:\AI_ML_Project\occurrence.csv")
    raw_snakeclef_metadata_csv: Path = Path(
        r"C:\AI_ML_Project\SnakeCLEF2021_min-train_metadata_PROD.csv"
    )
    raw_species_country_mapping_csv: Path = Path(r"C:\AI_ML_Project\species_to_country_mapping.csv")
    derived_root: Path = Path(r"C:\AI_ML_Project\data")
    manifests_dir: Path = Path(r"C:\AI_ML_Project\data\manifests")
    taxonomy_file: Path = Path(r"C:\AI_ML_Project\data\taxonomy\india_snakes_taxonomy_v1.yaml")
    clinical_knowledge_file: Path = Path(
        r"C:\AI_ML_Project\data\clinical\clinical_knowledge_v1.yaml"
    )
    antivenom_reference_file: Path = Path(
        r"C:\AI_ML_Project\data\antivenom\antivenom_reference_v1.yaml"
    )


class MLSettings(BaseModel):
    model_dir: Path = Path(r"C:\AI_ML_Project\ml\artifacts")
    binary_model_path: Path = Path(r"C:\AI_ML_Project\ml\artifacts\binary_classifier_latest.pt")
    device: str = "cpu"
    batch_size: int = 32


class AuthSettings(BaseModel):
    jwt_secret: str = "CHANGE_ME_another_long_random_string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7


class ClinicalSettings(BaseModel):
    min_confidence_threshold: float = 0.60
    ood_score_threshold: float = 0.80


class SurveillanceSettings(BaseModel):
    auto_record: bool = True
    coord_precision: int = 2


class Settings(BaseSettings):
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    dataset: DatasetSettings = Field(default_factory=DatasetSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    clinical: ClinicalSettings = Field(default_factory=ClinicalSettings)
    surveillance: SurveillanceSettings = Field(default_factory=SurveillanceSettings)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="__", extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

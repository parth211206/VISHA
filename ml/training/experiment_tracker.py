from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import uuid

@dataclass
class ExperimentConfig:
    experiment_id: str
    dataset_version: str
    manifest_path: str
    model_architecture: str
    training_config: dict
    random_seed: int
    created_at: str

@dataclass 
class ExperimentResult:
    config: ExperimentConfig
    train_metrics: list[dict]
    val_metrics: list[dict]
    test_metrics: dict | None
    best_epoch: int
    best_val_metric: float
    training_duration_seconds: float
    artifacts: dict[str, str]

class ExperimentTracker:
    def __init__(self, experiments_dir: Path):
        self.experiments_dir = experiments_dir
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        
    def start_experiment(self, config: ExperimentConfig) -> str:
        exp_dir = self.experiments_dir / config.experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        
        with open(exp_dir / "config.json", "w") as f:
            json.dump(asdict(config), f, indent=2)
            
        return config.experiment_id

    def log_epoch(self, experiment_id: str, epoch: int, train_metrics: dict, val_metrics: dict):
        exp_dir = self.experiments_dir / experiment_id
        metrics_file = exp_dir / "metrics.jsonl"
        
        data = {
            "epoch": epoch,
            "train": train_metrics,
            "val": val_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(metrics_file, "a") as f:
            f.write(json.dumps(data) + "\n")

    def finish_experiment(self, experiment_id: str, result: ExperimentResult):
        exp_dir = self.experiments_dir / experiment_id
        with open(exp_dir / "result.json", "w") as f:
            # Reconstruct dict cleanly to avoid dataclass nested serialization issues
            data = asdict(result)
            json.dump(data, f, indent=2)

    def load_experiment(self, experiment_id: str) -> ExperimentResult:
        exp_dir = self.experiments_dir / experiment_id
        with open(exp_dir / "result.json", "r") as f:
            data = json.load(f)
            
        config_data = data.pop("config")
        config = ExperimentConfig(**config_data)
        
        return ExperimentResult(config=config, **data)

    def list_experiments(self) -> list[ExperimentConfig]:
        configs = []
        for exp_dir in self.experiments_dir.iterdir():
            if exp_dir.is_dir():
                conf_file = exp_dir / "config.json"
                if conf_file.exists():
                    with open(conf_file, "r") as f:
                        configs.append(ExperimentConfig(**json.load(f)))
        return configs

from datetime import datetime

try:
    import numpy as np
    import torch
    from torch import nn, optim
    from torch.utils.data import DataLoader
except ImportError:
    pass

from ml.evaluation.metrics import compute_binary_metrics
from ml.models.binary_classifier import BinarySnakeClassifier
from ml.training.experiment_tracker import ExperimentConfig, ExperimentResult, ExperimentTracker


class BinaryClassifierTrainer:
    def __init__(
        self,
        model: BinarySnakeClassifier,
        train_loader: "DataLoader",
        val_loader: "DataLoader",
        config: dict,
        tracker: ExperimentTracker,
        experiment_id: str,
        device: "torch.device",
    ):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.config = config
        self.tracker = tracker
        self.experiment_id = experiment_id
        self.device = device

        # Setup loss and optimizer
        train_cfg = self.config.get("training", {})
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=float(train_cfg.get("learning_rate", 1e-4)),
            weight_decay=float(train_cfg.get("weight_decay", 1e-5)),
        )
        self.epochs = train_cfg.get("epochs", 30)

    def _train_epoch(self, epoch: int) -> dict:
        self.model.train()
        total_loss = 0

        for batch_idx, (inputs, labels, _) in enumerate(self.train_loader):
            inputs, labels = inputs.to(self.device), labels.to(self.device)
            self.optimizer.zero_grad()

            logits = self.model(inputs)
            loss = self.criterion(logits, labels)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        return {"loss": total_loss / len(self.train_loader)}

    def _val_epoch(self, epoch: int) -> dict:
        self.model.eval()
        total_loss = 0
        all_labels = []
        all_preds = []
        all_probs = []

        with torch.no_grad():
            for inputs, labels, _ in enumerate(self.val_loader):
                inputs, labels = inputs.to(self.device), labels.to(self.device)
                logits = self.model(inputs)
                loss = self.criterion(logits, labels)
                total_loss += loss.item()

                probs = torch.softmax(logits, dim=1)
                preds = torch.argmax(probs, dim=1)

                all_labels.extend(labels.cpu().numpy())
                all_preds.extend(preds.cpu().numpy())
                all_probs.extend(probs.cpu().numpy())

        metrics = compute_binary_metrics(
            np.array(all_labels), np.array(all_preds), np.array(all_probs)
        )
        metrics["val_loss"] = total_loss / len(self.val_loader)
        return metrics

    def train(self) -> ExperimentResult:
        start_time = datetime.now()
        best_val_loss = float("inf")
        best_epoch = 0

        train_metrics = []
        val_metrics = []

        for epoch in range(self.epochs):
            t_metrics = self._train_epoch(epoch)
            v_metrics = self._val_epoch(epoch)

            train_metrics.append(t_metrics)
            val_metrics.append(v_metrics)

            self.tracker.log_epoch(self.experiment_id, epoch, t_metrics, v_metrics)

            if v_metrics["val_loss"] < best_val_loss:
                best_val_loss = v_metrics["val_loss"]
                best_epoch = epoch
                # Save best model
                save_path = self.tracker.experiments_dir / self.experiment_id / "best_model.pt"
                self.model.save_checkpoint(save_path, metadata={"epoch": epoch})

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        exp_config = ExperimentConfig(
            experiment_id=self.experiment_id,
            dataset_version="v1",
            manifest_path=self.config.get("paths", {}).get("manifest", ""),
            model_architecture=self.config.get("model", {}).get("architecture", ""),
            training_config=self.config,
            random_seed=self.config.get("training", {}).get("random_seed", 42),
            created_at=start_time.isoformat(),
        )

        result = ExperimentResult(
            config=exp_config,
            train_metrics=train_metrics,
            val_metrics=val_metrics,
            test_metrics=None,
            best_epoch=best_epoch,
            best_val_metric=best_val_loss,
            training_duration_seconds=duration,
            artifacts={"best_model": f"{self.experiment_id}/best_model.pt"},
        )

        self.tracker.finish_experiment(self.experiment_id, result)
        return result

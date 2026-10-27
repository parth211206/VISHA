# Binary Snake Classifier Training Summary

## Objective
Train, evaluate, and verify a binary classifier for venomous vs non-venomous snake classification using the leakage-safe manifest.

## Dataset
- Leakage-safe manifest: `data/manifests/image_manifest_v1_leakage_safe.csv`
- Active training entries: 1,767
- Active test entries: 264
- Training/validation split: 15% of training data for validation (stratified by binary label)
  - Training subset: 1,501 rows
  - Validation subset: 266 rows

## Model
- Architecture: EfficientNet-B3 with pretrained ImageNet weights
- Backbone frozen for first 2 epochs (as per prototype config)
- Classification head: Dropout -> Linear(512) -> ReLU -> Dropout -> Linear(2)
- Input size: 300x300 RGB images

## Training Configuration
- Epochs: 2
- Batch size: 16
- Learning rate: 1e-4
- Weight decay: 1e-5
- Optimizer: AdamW
- Loss: CrossEntropyLoss
- Device: CPU (no GPU available)
- Early stopping: disabled for prototype
- Random seed: 42

## Results
### Test Set Metrics
- Accuracy: 0.8144
- Balanced Accuracy: 0.8131
- Precision (macro): 0.8147
- Recall (macro): 0.8131
- F1-score (macro): 0.8136
- ROC AUC: 0.9039
- Sensitivity (Venomous Recall): 0.8406
- Specificity (Non-venomous Recall): 0.7857
- PPV: 0.8112
- NPV: 0.8182

### Confusion Matrix
```
[[ 99  27]   # True Non-venomous: 99 correct, 27 misclassified as venomous
 [ 22 116]]  # True Venomous: 22 misclassified as non-venomous, 116 correct
```
Labels: [non_venomous, venomous]

### Probability Validation
- Probability sums are valid (sum to 1) for all test samples.
- All probabilities are within the [0,1] range.

## Checkpoints
- Best model: `ml/runs/binary_prototype_20261012_100432/best_model.pt`
- Copied to: `ml/artifacts/binary_classifier_latest.pt`

## Verification
- All ML unit tests pass (21/21)
- All backend unit tests pass (10/10)
- Full test suite passes (31/31)

## Notes
- This model is for binary classification only (venomous vs non-venomous).
- It does NOT perform species identification.
- No clinical validation or treatment recommendations are implied.
- The model is ready for integration with the FastAPI backend for prototype demonstration.

## Next Steps
1. Integrate the checkpoint with the existing FastAPI backend.
2. Create an inference endpoint that returns venomous/non-venomous probabilities.
3. Label the output as experimental binary classification.
import numpy as np

from ml.evaluation.metrics import compute_binary_metrics


def test_compute_binary_metrics_perfect():
    y_true = np.array([1, 0, 1, 0])
    y_pred = np.array([1, 0, 1, 0])
    y_prob = np.array([[0.1, 0.9], [0.8, 0.2], [0.2, 0.8], [0.7, 0.3]])

    metrics = compute_binary_metrics(y_true, y_pred, y_prob)
    assert metrics["accuracy"] == 1.0
    assert metrics["f1_macro"] == 1.0
    assert metrics["sensitivity"] == 1.0
    assert metrics["specificity"] == 1.0
    assert metrics["ppv"] == 1.0
    assert metrics["npv"] == 1.0


def test_compute_binary_metrics_all_wrong():
    y_true = np.array([1, 0, 1, 0])
    y_pred = np.array([0, 1, 0, 1])
    y_prob = np.array([[0.9, 0.1], [0.2, 0.8], [0.8, 0.2], [0.3, 0.7]])

    metrics = compute_binary_metrics(y_true, y_pred, y_prob)
    assert metrics["accuracy"] == 0.0
    assert metrics["sensitivity"] == 0.0
    assert metrics["specificity"] == 0.0


def test_compute_binary_metrics_shapes():
    y_true = np.array([1])
    y_pred = np.array([1])
    y_prob = np.array([[0.1, 0.9]])

    metrics = compute_binary_metrics(y_true, y_pred, y_prob)
    assert metrics["accuracy"] == 1.0


def test_sensitivity_is_venomous_recall():
    # TP=1, FN=1 -> sensitivity = 0.5
    # TN=1, FP=1 -> specificity = 0.5
    y_true = np.array([1, 1, 0, 0])
    y_pred = np.array([1, 0, 0, 1])
    y_prob = np.array([[0.1, 0.9], [0.6, 0.4], [0.8, 0.2], [0.4, 0.6]])

    metrics = compute_binary_metrics(y_true, y_pred, y_prob)
    assert metrics["sensitivity"] == 0.5
    assert metrics["specificity"] == 0.5

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

try:
    from sklearn.ensemble import IsolationForest  # type: ignore
except Exception:  # pragma: no cover
    IsolationForest = None


class TelemetryFaultMonitor:
    """IsolationForest fault scorer for robot telemetry vectors."""

    def __init__(self, contamination: float = 0.05, random_state: int = 42) -> None:
        self.contamination = contamination
        self.random_state = random_state
        self._model: Any = None
        self._baseline: np.ndarray = self._default_baseline()
        self._fit_model(self._baseline)

    def _default_baseline(self) -> np.ndarray:
        rng = np.random.default_rng(self.random_state)
        # Features: [min_lidar_dist, vel_error, imu_var, motor_temp, battery_drain]
        normal = np.column_stack(
            [
                rng.normal(2.2, 0.5, size=120),
                rng.normal(0.03, 0.02, size=120),
                rng.normal(0.02, 0.01, size=120),
                rng.normal(42.0, 3.0, size=120),
                rng.normal(0.08, 0.03, size=120),
            ]
        )
        return normal

    def _fit_model(self, data: np.ndarray) -> None:
        if IsolationForest is not None:
            clf = IsolationForest(contamination=self.contamination, random_state=self.random_state)
            clf.fit(data)
            self._model = clf
        else:
            self._model = None

    def fit_baseline(self, vectors: Sequence[Sequence[float]]) -> None:
        arr = np.asarray(vectors, dtype=float)
        if arr.ndim == 2 and arr.shape[0] >= 10:
            self._baseline = arr
            self._fit_model(self._baseline)

    def score_telemetry(self, vec: Sequence[float]) -> dict[str, Any]:
        arr = np.asarray(list(vec), dtype=float).reshape(1, -1)
        if arr.shape[1] != 5:
            raise ValueError("Telemetry vector must have 5 values: [min_lidar_dist, vel_error, imu_var, motor_temp, battery_drain]")

        if self._model is not None:
            raw_decision = float(self._model.decision_function(arr)[0])
            # Lower decision_function means more anomalous; map to [0.0, 1.0] anomaly score
            anomaly_score = round(float(np.clip(0.5 - raw_decision, 0.0, 1.0)), 4)
            pred = int(self._model.predict(arr)[0])
            fault_risk = bool(pred == -1 or anomaly_score >= 0.62)
        else:
            z = np.mean(np.abs(arr[0] - np.mean(self._baseline, axis=0)) / (np.std(self._baseline, axis=0) + 1e-6))
            anomaly_score = round(float(np.clip(z / 5.0, 0.0, 1.0)), 4)
            fault_risk = bool(anomaly_score >= 0.62)

        return {
            "anomaly_score": anomaly_score,
            "FAULT_RISK": fault_risk,
        }

    def compute_metrics(self, labeled_incidents: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Compute precision and recall against human-labeled incidents in telemetry_logs."""
        tp = fp = fn = 0
        for row in labeled_incidents:
            actual_fault = bool(row.get("actual_fault", False))
            predicted_fault = bool(row.get("predicted_fault", False))
            if predicted_fault and actual_fault:
                tp += 1
            elif predicted_fault and not actual_fault:
                fp += 1
            elif not predicted_fault and actual_fault:
                fn += 1

        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 1.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 1.0
        return {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "total_evaluated": len(labeled_incidents),
        }
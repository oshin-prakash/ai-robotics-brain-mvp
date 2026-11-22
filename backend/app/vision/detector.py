from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover
    YOLO = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VisionDetector:
    """Background vision worker capturing webcam/synthetic frames and running YOLOv8n."""

    def __init__(self, model_path: str = "yolov8n.pt", target_fps: float = 12.0, camera_index: int = 0) -> None:
        self.model_path = model_path
        self.target_fps = max(1.0, min(30.0, target_fps))
        self.camera_index = camera_index
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._model: Any = None
        self._latest_detections: list[dict[str, Any]] = []
        self._latest_jpeg: bytes = b""
        self._frame_count: int = 0

        if YOLO is not None:
            try:
                self._model = YOLO(self.model_path)
            except Exception:
                self._model = None

        # Seed initial synthetic frame so endpoints never return empty data
        frame = self._synthetic_frame(frame_idx=0)
        self._latest_jpeg = self._encode_jpeg(frame)
        self._latest_detections = []

    def _synthetic_frame(self, frame_idx: int) -> np.ndarray:
        canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        canvas[:] = (24, 28, 36)
        if cv2 is not None:
            cv2.rectangle(canvas, (16, 16), (624, 464), (60, 140, 220), 2)
            cv2.putText(
                canvas,
                "SYNTHETIC ROBOT CAMERA TELEMETRY",
                (34, 54),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (120, 220, 255),
                2,
            )
            cv2.putText(
                canvas,
                f"Frame: {frame_idx} | Mode: Fallback Canvas",
                (34, 86),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (180, 190, 205),
                1,
            )
        return canvas

    def _encode_jpeg(self, frame: np.ndarray) -> bytes:
        if cv2 is not None:
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ok:
                return bytes(buf)
        return frame.tobytes()

    def _process_once(self) -> None:
        detections: list[dict[str, Any]] = []
        frame: np.ndarray | None = None

        if cv2 is not None:
            cap = cv2.VideoCapture(self.camera_index)
            try:
                if cap is not None and cap.isOpened():
                    ok, img = cap.read()
                    if ok and img is not None:
                        frame = img
            finally:
                if cap is not None:
                    cap.release()

        if frame is None:
            frame = self._synthetic_frame(self._frame_count)

        if self._model is not None:
            try:
                results = self._model(frame, verbose=False)
                names = getattr(self._model, "names", {}) or {}
                for res in results:
                    boxes = getattr(res, "boxes", None)
                    if boxes is None:
                        continue
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        label = str(names.get(cls_id, f"class_{cls_id}"))
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]
                        if cv2 is not None:
                            cv2.rectangle(frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), (0, 220, 120), 2)
                            cv2.putText(
                                frame,
                                f"{label} {conf:.2f}",
                                (xyxy[0], max(20, xyxy[1] - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.55,
                                (0, 255, 140),
                                2,
                            )
                        detections.append(
                            {
                                "class_name": label,
                                "confidence": round(conf, 4),
                                "bbox": xyxy,
                            }
                        )
            except Exception:
                detections = []

        jpeg_bytes = self._encode_jpeg(frame)
        ts = _utc_now()
        summary = [
            {
                "class_name": d["class_name"],
                "confidence": d["confidence"],
                "count": 1,
                "timestamp": ts,
            }
            for d in detections
        ]

        with self._lock:
            self._frame_count += 1
            self._latest_jpeg = jpeg_bytes
            self._latest_detections = summary

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()

        def _loop() -> None:
            interval = 1.0 / self.target_fps
            while not self._stop_event.is_set():
                t0 = time.monotonic()
                try:
                    self._process_once()
                except Exception:
                    pass
                elapsed = time.monotonic() - t0
                sleep_for = max(0.01, interval - elapsed)
                self._stop_event.wait(sleep_for)

        self._thread = threading.Thread(target=_loop, name="vision-detector-daemon", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def get_latest_jpeg(self) -> bytes:
        with self._lock:
            return self._latest_jpeg

    def get_latest_detections(self) -> dict[str, Any]:
        with self._lock:
            items = list(self._latest_detections)
            frame_count = self._frame_count
        return {
            "count": len(items),
            "frame_count": frame_count,
            "timestamp": _utc_now(),
            "detections": items,
        }
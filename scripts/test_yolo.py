import sys
import numpy as np
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.vision.detector import LocalDetector

def main():
    print("Probando inicialización y detección YOLO...")
    detector = LocalDetector(model_name="yolov8n.pt")
    initialized = detector.initialize()
    print(f"Detector inicializado: {initialized}")

    fake_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    res = detector.detect_persons(fake_frame)
    print(f"Resumen de detección: personas={res.persons}, max_confidence={res.max_confidence}")

if __name__ == "__main__":
    main()

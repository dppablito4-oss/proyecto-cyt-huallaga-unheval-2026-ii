import sys
import time
import numpy as np
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.vision.image_processor import ImageProcessor

def main():
    print("Ejecutando Benchmark de procesamiento de imágenes...")
    processor = ImageProcessor(max_width=1280, jpeg_quality=70)
    fake_frame = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)

    t0 = time.perf_counter()
    for _ in range(50):
        processor.compress_jpeg(fake_frame)
    t1 = time.perf_counter()

    avg_ms = ((t1 - t0) / 50) * 1000
    print(f"Tiempo promedio de compresión JPEG (1080p -> 1280w, quality 70): {avg_ms:.2f} ms")

if __name__ == "__main__":
    main()

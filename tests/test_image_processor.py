import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import numpy as np
from app.vision.image_processor import ImageProcessor
from app.ai.vision_client import VisionAIClient


def test_image_compression():
    processor = ImageProcessor(max_width=640, jpeg_quality=70)
    # Crear un frame ficticio de 1000x1000 píxeles
    fake_frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
    
    # 1. Probar redimensionamiento
    resized = processor.resize_if_needed(fake_frame)
    assert resized.shape[1] == 640
    
    # 2. Probar compresión JPEG binaria (ImageProcessor)
    jpeg_bytes = processor.compress_jpeg(fake_frame)
    assert isinstance(jpeg_bytes, bytes)
    assert len(jpeg_bytes) > 0
    
    # 3. Probar serialización de transporte a Base64 Data URL (VisionAIClient)
    base64_url = VisionAIClient._bytes_to_data_url(jpeg_bytes)
    assert base64_url.startswith("data:image/jpeg;base64,")
    
    print("test_image_compression PASSED")


if __name__ == "__main__":
    test_image_compression()

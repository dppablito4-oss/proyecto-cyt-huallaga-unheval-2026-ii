import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import numpy as np
from app.vision.image_processor import ImageProcessor

def test_image_compression():
    processor = ImageProcessor(max_width=640, jpeg_quality=70)
    # Crear un frame ficticio de 1000x1000 píxeles
    fake_frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
    
    resized = processor.resize_if_needed(fake_frame)
    assert resized.shape[1] == 640
    
    jpeg_bytes = processor.compress_jpeg(fake_frame)
    assert len(jpeg_bytes) > 0
    
    base64_url = processor.to_base64_data_url(fake_frame)
    assert base64_url.startswith("data:image/jpeg;base64,")
    print("test_image_compression PASSED")

if __name__ == "__main__":
    test_image_compression()

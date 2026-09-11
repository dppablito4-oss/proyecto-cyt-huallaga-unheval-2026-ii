from pathlib import Path

import numpy as np

from app.config import settings


def test_committed_yoloe_prompts_match_runtime_classes_and_model():
    path = settings.YOLO_PROMPT_EMBEDDINGS_PATH
    if not path.is_absolute():
        path = settings.BASE_DIR / path

    assert Path(path).is_file()
    with np.load(path, allow_pickle=False) as payload:
        assert payload["model"].item() == "yoloe-26n"
        assert payload["names"].tolist() == list(settings.DETECTION_CLASSES)
        assert payload["embeddings"].shape == (1, len(settings.DETECTION_CLASSES), 512)

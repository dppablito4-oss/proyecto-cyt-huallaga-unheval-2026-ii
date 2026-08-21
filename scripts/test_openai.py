import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.ai.vision_client import VisionAI

def main():
    print("Probando cliente Vision AI...")
    vision = VisionAI()
    initialized = vision.initialize()
    print(f"VisionAI inicializado: {initialized}")
    result = vision.analyze_sequence([])
    print("Resultado:", result)

if __name__ == "__main__":
    main()

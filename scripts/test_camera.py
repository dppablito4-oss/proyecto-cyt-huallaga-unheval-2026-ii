import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.camera.usb_camera import UsbCamera

def main():
    print("Probando cámara USB...")
    cam = UsbCamera(camera_index=0)
    if cam.open():
        print("Cámara abierta exitosamente.")
        ret, frame = cam.read()
        if ret and frame is not None:
            print(f"Fotograma capturado correctamente. Resolución: {frame.shape[1]}x{frame.shape[0]}")
        cam.close()
    else:
        print("No se pudo abrir la cámara index 0 (esperado si no hay webcam conectada).")

if __name__ == "__main__":
    main()

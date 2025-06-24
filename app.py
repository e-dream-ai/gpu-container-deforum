import random
import cv2
import numpy as np
import os

def generate_flashing_video(output_path="flashing_video.mp4", duration_sec=5, fps=24):
    height, width = 512, 512
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = duration_sec * fps
    for _ in range(total_frames):
        color = [random.randint(0, 255) for _ in range(3)]
        frame = np.full((height, width, 3), color, dtype=np.uint8)
        out.write(frame)

    out.release()
    print(f"[+] Video generated at {output_path}")

if __name__ == "__main__":
    os.makedirs("/workspace/output", exist_ok=True)
    generate_flashing_video("/workspace/output/flashing_video.mp4")

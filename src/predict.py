import os
import json
import time
import shutil
import traceback
from deforum.shared_storage import models
from deforum import DeforumAnimationPipeline


class Predictor:
    def __init__(self):
        self.pipe = None

    def setup(self):
        total, used, free = shutil.disk_usage("/")
        print(
            f"[Init] Disk space total={total//(1024**3)}GB, "
            f"used={used//(1024**3)}GB, free={free//(1024**3)}GB"
        )

        cache_vars = [
            "HF_HOME",
            "HF_HUB_CACHE",
            "TRANSFORMERS_CACHE",
            "HF_DATASETS_CACHE",
            "DEFORUM_MODEL_ID",
        ]
        for var in cache_vars:
            print(f"[Init] {var} = {os.getenv(var)}")

        model_id = os.getenv("DEFORUM_MODEL_ID", "125703")
        model_filename = "protovisionXLHighFidelity3D_releaseV660Bakedvae.safetensors"

        pv_path = f"/runpod-volume/{model_filename}"
        baked_path = f"/deforum_storage/models/{model_filename}"
        selected_path = None

        print("[Init] Checking for local model file...")

        if os.path.exists(pv_path):
            selected_path = pv_path
            print(f"[Init] Found model in PV: {pv_path}")
        elif os.path.exists(baked_path):
            selected_path = baked_path
            print(f"[Init] Found model baked in image: {baked_path}")

        if "deforum_pipe" not in models:
            try:
                if selected_path:
                    models["deforum_pipe"] = DeforumAnimationPipeline.from_file(
                        model_path=selected_path
                    )
                    print(
                        f"[Init] Successfully loaded from local path: {selected_path}"
                    )
                else:
                    print(
                        f"[Init] No local model found, downloading from CivitAI "
                        f"with id={model_id}..."
                    )
                    models["deforum_pipe"] = (
                        DeforumAnimationPipeline.from_civitai(model_id=model_id)
                    )
                    print(
                        f"[Init] Successfully downloaded and loaded model "
                        f"{model_id} from CivitAI"
                    )
            except Exception as e:
                print("[Init][ERROR] Model load failed!")
                traceback.print_exc()
                raise RuntimeError(
                    f"Deforum model setup failed → {type(e).__name__}: {e}"
                )
        else:
            print("[Init] Re-using existing loaded pipeline.")

        self.pipe = models["deforum_pipe"]

    def predict(self, settings_file: str, progress_callback: callable = None) -> str:
        result = self.run_backend(settings_file, progress_callback)
        video_path = result.get("video_path")
        if not video_path:
            raise RuntimeError(f"Deforum failed, no video_path in result: {result}")
        return video_path

    def run_backend(self, settings_file: str, progress_callback: callable = None) -> dict:
        if not os.path.exists(settings_file):
            raise FileNotFoundError(f"Settings file '{settings_file}' not found.")

        with open(settings_file, "r") as f:
            params = json.load(f)

        params["settings_file"] = settings_file
        self.pipe.generator.optimize = params.get("optimize", True)

        prom = params.get("prompts", {})
        if isinstance(prom, str):
            lines = [ln for ln in prom.splitlines() if ln.strip()]
            keys_raw = params.get("keyframes", "0")
            keys = [k for k in str(keys_raw).splitlines() if k.strip()]
            params["animation_prompts"] = dict(zip(keys, lines))
        else:
            params["animation_prompts"] = prom

        ts = time.strftime("%Y%m%d%H%M%S")
        params["timestring"] = (
            (params.get("resume_from_timestring") and params.get("resume_timestring"))
            or ts
        )

        print(f"[Run] Starting pipeline with timestring={params['timestring']}")

        # ---- Preview settings ----
        PREVIEW_MAX_SIDE = int(params.get("preview_max_side", 512))
        PREVIEW_JPEG_QUALITY = int(params.get("preview_jpeg_quality", 85))

        def _encode_preview_base64(image):
            """
            Returns base64(JPEG) string or None.
            Supports PIL images and numpy arrays (OpenCV).
            """
            try:
                import base64
                from io import BytesIO

                import numpy as np

                # PIL-like
                if hasattr(image, "save"):
                    preview_img = image.copy()
                    preview_img.thumbnail((PREVIEW_MAX_SIDE, PREVIEW_MAX_SIDE))
                    buffered = BytesIO()
                    preview_img.save(
                        buffered,
                        format="JPEG",
                        quality=PREVIEW_JPEG_QUALITY,
                    )
                    return base64.b64encode(buffered.getvalue()).decode("utf-8")

                # ndarray (H,W,C) or (H,W)
                if isinstance(image, np.ndarray):
                    import cv2

                    h, w = image.shape[:2]
                    if h == 0 or w == 0:
                        return None

                    scale = PREVIEW_MAX_SIDE / max(h, w)
                    new_w = max(1, int(round(w * scale)))
                    new_h = max(1, int(round(h * scale)))

                    preview_img = cv2.resize(
                        image,
                        (new_w, new_h),
                        interpolation=cv2.INTER_AREA
                        if scale < 1.0
                        else cv2.INTER_LINEAR,
                    )

                    # If it's RGB, convert to BGR for OpenCV JPEG encoder
                    if (
                        len(preview_img.shape) == 3
                        and preview_img.shape[2] == 3
                        and preview_img.dtype == np.uint8
                    ):
                        preview_img = cv2.cvtColor(preview_img, cv2.COLOR_RGB2BGR)

                    ok, buffer = cv2.imencode(
                        ".jpg",
                        preview_img,
                        [cv2.IMWRITE_JPEG_QUALITY, PREVIEW_JPEG_QUALITY],
                    )
                    if not ok:
                        return None

                    return base64.b64encode(buffer.tobytes()).decode("utf-8")

                return None
            except Exception as e:
                print(f"[Run][Warning] Preview generation failed: {e}")
                return None

        def deforum_callback(data):
            if not progress_callback:
                return

            frame_idx = data.get("frame_idx")
            image = data.get("image") or data.get("img")
            max_frames = params.get("max_frames", 100)

            if frame_idx is None:
                return

            percent = round((frame_idx / max_frames) * 100, 1)

            preview_base64 = None
            if image is not None:
                preview_base64 = _encode_preview_base64(image)

            if preview_base64:
                progress_callback(percent, preview_base64)
            else:
                progress_callback(percent)

        animation = self.pipe(callback=deforum_callback, **params)

        result = {
            "status": "Ready",
            "timestring": animation.timestring,
            "resume_path": animation.outdir,
            "resume_from": getattr(animation, "max_frames", None),
            "video_path": getattr(animation, "video_path", None),
        }
        print(f"[Run] Pipeline finished, video_path={result['video_path']}")
        return result
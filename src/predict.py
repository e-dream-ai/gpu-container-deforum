import os
import sys
import json
import math
import time
import subprocess
import tempfile
import shutil
import traceback
from pathlib import Path
from deforum.shared_storage import models
from deforum import DeforumAnimationPipeline

class Predictor:
    def __init__(self):
        self.pipe = None

def setup(self):
        # Report disk space
        total, used, free = shutil.disk_usage("/")
        print(
            f"[Init] Disk space total={total//(1024**3)}GB, "
            f"used={used//(1024**3)}GB, free={free//(1024**3)}GB"
        )

        # Report env vars
        cache_vars = ["HF_HOME", "HF_HUB_CACHE", "TRANSFORMERS_CACHE",
                      "HF_DATASETS_CACHE", "DEFORUM_MODEL_ID"]
        for var in cache_vars:
            print(f"[Init] {var} = {os.getenv(var)}")

        # Deforum model ID (CivitAI fallback)
        model_id = os.getenv("DEFORUM_MODEL_ID", "125703")

        # Known model file name
        model_filename = "protovisionXLHighFidelity3D_releaseV660Bakedvae.safetensors"

        # Possible paths
        pv_path = f"/workspace/{model_filename}"           # Persistent Volume
        baked_path = f"/deforum_storage/models/{model_filename}"  # baked into image
        selected_path = None

        print(f"[Init] Checking for local model file...")

        if os.path.exists(pv_path):
            selected_path = pv_path
            print(f"[Init] Found model in PV: {pv_path}")
        elif os.path.exists(baked_path):
            selected_path = baked_path
            print(f"[Init] Found model baked in image: {baked_path}")

        # Initialize pipeline
        if "deforum_pipe" not in models:
            try:
                if selected_path:
                    models["deforum_pipe"] = DeforumAnimationPipeline.from_pretrained(selected_path)
                    print(f"[Init] Successfully loaded from local path: {selected_path}")
                else:
                    print(f"[Init] No local model found, downloading from CivitAI with id={model_id}...")
                    models["deforum_pipe"] = DeforumAnimationPipeline.from_civitai(model_id=model_id)
                    print(f"[Init] Successfully downloaded and loaded model {model_id} from CivitAI")
            except Exception as e:
                print(f"[Init][ERROR] Model load failed!")
                traceback.print_exc()
                raise RuntimeError(
                    f"Deforum model setup failed → {type(e).__name__}: {e}"
                )
        else:
            print(f"[Init] Re-using existing loaded pipeline.")

        self.pipe = models["deforum_pipe"]

    def predict(self, settings_file: str) -> str:
        """Run Deforum with the given settings file and return the generated video path."""
        result = self.run_backend(settings_file)
        video_path = result.get("video_path")
        if not video_path:
            raise RuntimeError(f"Deforum failed, no video_path in result: {result}")
        return video_path

    def run_backend(self, settings_file: str) -> dict:
        # Verify settings file
        if not os.path.exists(settings_file):
            raise FileNotFoundError(
                f"Settings file '{settings_file}' not found."
            )

        # Load JSON settings
        with open(settings_file, "r") as f:
            params = json.load(f)

        # Attach settings_file path
        params["settings_file"] = settings_file
        # Ensure generator optimization flag
        self.pipe.generator.optimize = params.get("optimize", True)

        # Parse prompts into dict if needed
        prom = params.get("prompts", {})
        if isinstance(prom, str):
            lines = prom.strip().split("")
            keys = params.get("keyframes", "0").strip().split("")
            params["animation_prompts"] = dict(zip(keys, lines))
        else:
            params["animation_prompts"] = prom

        # Handle timestring/resume
        ts = time.strftime("%Y%m%d%H%M%S")
        params["timestring"] = (
            params.get("resume_from_timestring")
            and params.get("resume_timestring")
            or ts
        )

        print(f"[Run] Starting pipeline with timestring={params['timestring']}")
        # Run the pipeline
        animation = self.pipe(callback=None, **params)

        # Collect result
        result = {
            "status": "Ready",
            "timestring": animation.timestring,
            "resume_path": animation.outdir,
            "resume_from": getattr(animation, "max_frames", None),
            "video_path": getattr(animation, "video_path", None),
        }
        print(f"[Run] Pipeline finished, video_path={result['video_path']}")
        return result
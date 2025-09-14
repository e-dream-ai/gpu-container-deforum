import os
import sys
import json
import math
import time
import subprocess
import tempfile
from pathlib import Path
from deforum.shared_storage import models
from deforum import DeforumAnimationPipeline

class Predictor:
    def __init__(self):
        self.pipe = None

    def setup(self):
        # Ensure cache directories exist
        cache_dir = os.getenv("HF_HOME", "/deforum_storage/huggingface")
        if not cache_dir:
            cache_dir = "/deforum_storage/huggingface"
        
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "transformers"), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, "hub"), exist_ok=True)
        
        # Set the HF_HOME environment variable to ensure it's available for the pipeline
        os.environ["HF_HOME"] = cache_dir
        
        # Load or reuse the Deforum pipeline
        model_id = os.getenv("DEFORUM_MODEL_ID", "125703")
        if 'deforum_pipe' not in models:
            try:
                print(f"Loading Deforum model {model_id} from CivitAI...")
                print(f"Using cache directory: {cache_dir}")
                models['deforum_pipe'] = DeforumAnimationPipeline.from_civitai(model_id=model_id)
                print(f"Successfully loaded Deforum model {model_id}")
            except TypeError as e:
                if "join() argument must be str" in str(e):
                    print(f"Cache directory error: {e}")
                    print(f"HF_HOME environment variable: {os.getenv('HF_HOME')}")
                    print(f"Current cache_dir value: {cache_dir}")
                    raise RuntimeError(f"Cache directory configuration error for model {model_id}. "
                                     f"Please ensure HF_HOME is properly set. Error: {e}")
                else:
                    raise RuntimeError(f"Failed to load Deforum model {model_id}: {e}")
            except Exception as e:
                print(f"Error loading model from CivitAI: {e}")
                print(f"Model ID: {model_id}")
                print(f"Cache directory: {cache_dir}")
                # Fallback: try to load a default model or handle gracefully
                raise RuntimeError(f"Failed to load Deforum model {model_id}: {e}")
        else:
            print(f"Reusing existing Deforum pipeline for model {model_id}")
        self.pipe = models['deforum_pipe']

    def predict(self, settings_file: str) -> str:
        """
        Run Deforum with the given settings file and return the generated video path.
        """
        result = self.run_backend(settings_file)
        video_path = result.get("video_path")
        if not video_path:
            raise RuntimeError(f"Deforum failed, no video_path in result: {result}")
        return video_path

    def run_backend(self, settings_file: str) -> dict:
        # Verify settings file
        if not os.path.exists(settings_file):
            raise FileNotFoundError(f"Settings file '{settings_file}' not found.")

        # Load JSON settings
        with open(settings_file, 'r') as f:
            params = json.load(f)

        # Attach settings_file path
        params["settings_file"] = settings_file
        # Ensure generator optimization flag
        self.pipe.generator.optimize = params.get('optimize', True)

        # Parse prompts into dict if needed
        prom = params.get("prompts", {})
        if isinstance(prom, str):
            lines = prom.strip().split("")
            keys = params.get("keyframes", "0").strip().split("")
            params["animation_prompts"] = dict(zip(keys, lines))
        else:
            params["animation_prompts"] = prom

        # Handle timestring/resume
        ts = time.strftime('%Y%m%d%H%M%S')
        params["timestring"] = params.get("resume_from_timestring") and params.get("resume_timestring") or ts

        # Run the pipeline
        animation = self.pipe(callback=None, **params)

        # Collect result
        result = {
            "status": "Ready",
            "timestring": animation.timestring,
            "resume_path": animation.outdir,
            "resume_from": getattr(animation, 'max_frames', None),
            "video_path": getattr(animation, 'video_path', None)
        }
        return result
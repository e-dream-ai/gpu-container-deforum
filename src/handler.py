import os
import uuid
import json

import runpod
from runpod.serverless.utils import upload_file_to_bucket
from runpod.serverless.utils.rp_validator import validate

from predict import Predictor
from rp_schema import INPUT_SCHEMA

# Instantiate and warm up your model exactly once
predictor = Predictor()
predictor.setup()

def handler(event):
    # 1) Extract & validate input
    inp = event.get("input")
    if inp is None:
        return { "error": "INPUT_NOT_PROVIDED" }

    validation = validate(inp, INPUT_SCHEMA)
    if validation.get("errors"):
        return { "error": "INVALID_INPUT", "details": validation["errors"] }

    params = validation["validated_input"]

    # 2) Merge in optional settings file
    settings_path = params.get("settings_file")
    if settings_path:
        try:
            with open(settings_path, "r") as f:
                file_settings = json.load(f)
            params.update(file_settings)
        except Exception as e:
            return { "error": "SETTINGS_FILE_READ_ERROR", "message": str(e) }

    # 3) Run prediction
    try:
        video_path = predictor.predict(**params)
    except Exception as e:
        return { "error": "PREDICTION_ERROR", "message": str(e) }

    if not video_path or not os.path.exists(video_path):
        return { "error": "PREDICTION_NO_OUTPUT", "message": "No video generated." }

    # 4) Upload to bucket
    try:
        file_url = upload_file_to_bucket(
            file_name=f"{uuid.uuid4()}.mp4",
            file_location=video_path,
            # To enable S3, uncomment and configure:
            # bucket_creds={…}, bucket_name="your-bucket"
        )
    except Exception as e:
        return { "error": "UPLOAD_ERROR", "message": str(e) }
    finally:
        # clean up local file if it exists
        if os.path.exists(video_path):
            os.remove(video_path)

    return { "video": file_url }

# Start the RunPod serverless handler
runpod.serverless.start({"handler": handler})

import os
import uuid
import runpod
from runpod.serverless.utils import upload_file_to_bucket
from runpod.serverless.utils.rp_validator import validate
import json
from predict import Predictor
from rp_schema import INPUT_SCHEMA

generate_video = Predictor()
generate_video.setup()

def handler(event):
    _input = event.get("input")
    if _input is None:
        return { "error": "INPUT_NOT_PROVIDED" }

    validated_input = validate(_input, INPUT_SCHEMA)
    if validated_input.get("errors") is not None:
        return validated_input["errors"]

    params = validated_input["validated_input"]

    # Optional file-based settings override
    if "settings_file" in params and params["settings_file"]:
        try:
            with open(params["settings_file"], "r") as f:
                file_settings = json.load(f)
                params.update(file_settings)
        except Exception as e:
            return { "error": f"Failed to read settings_file: {str(e)}" }

    # Predict
    video_path = generate_video.predict(**params)
    if not video_path or not os.path.exists(video_path):
        return { "error": "Video generation failed." }

    # Upload
    file_url = upload_file_to_bucket(
        file_name=f"{uuid.uuid4()}.mp4",
        file_location=video_path
        # To enable S3:
        # ,bucket_creds={...}, bucket_name="your-bucket"
    )

    os.remove(video_path)

    return { "video": file_url }

runpod.serverless.start({ "handler": handler })

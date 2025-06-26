import runpod
import os
import json
import uuid
import tempfile
import requests
from runpod.serverless.utils import upload_file_to_bucket
from runpod.serverless.utils.rp_validator import validate
from rp_schema import INPUT_SCHEMA
from predict import Predictor

# Initialize the Deforum predictor
generate_video = Predictor()
generate_video.setup()

# Helper to download a remote URL to a local file

def _download_if_url(path: str) -> str:
    if not path or not path.startswith(('http://', 'https://')):
        return path
    local_fd, local_path = tempfile.mkstemp(suffix=os.path.splitext(path)[1])
    os.close(local_fd)
    resp = requests.get(path, stream=True)
    resp.raise_for_status()
    with open(local_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return local_path


def handler(event):
    # Validate input
    _input = event.get("input") or {}
    validated = validate(_input, INPUT_SCHEMA)
    if validated.get("errors"):
        return {"errors": validated["errors"]}
    settings = validated["validated_input"]["settings"]

    # Download any remote file paths
    for key in ("video_init_path", "video_mask_path"):  # extend as needed
        if key in settings:
            try:
                settings[key] = _download_if_url(settings[key])
            except:
                pass

    # Write settings to a temporary JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as sf:
        json.dump(settings, sf)
        sf_path = sf.name

    # Run the predictor using the settings file
    video_local = generate_video.predict(settings_file=sf_path)
    os.remove(sf_path)

    # Upload to S3 (or configured bucket)
    file_url = upload_file_to_bucket(
        file_name=f"{uuid.uuid4()}.mp4",
        file_location=video_local
    )
    # Clean up local video
    os.remove(video_local)

    return {"video": file_url}

runpod.serverless.start({"handler": handler})

# # Local testing
# if __name__ == '__main__':
#     # Example event: load a sample settings JSON from disk
#     sample = json.load(open('test-settings.json'))
#     event = {"input": {"settings": sample}}
#     out = handler(event)
#     print(out)

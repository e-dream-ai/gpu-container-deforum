import os
import json
import uuid
import tempfile
import requests

import runpod
from runpod.serverless.utils.rp_validator import validate
from rp_schema import INPUT_SCHEMA
from predict import Predictor

import boto3

# Initialize the Deforum predictor
generate_video = Predictor()
generate_video.setup()

def _download_if_url(path: str) -> str:
    if not path or not path.startswith(("http://", "https://")):
        return path
    fd, local_path = tempfile.mkstemp(suffix=os.path.splitext(path)[1])
    os.close(fd)
    resp = requests.get(path, stream=True)
    resp.raise_for_status()
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    return local_path

def handler(event):
    # 1) validate input
    _input = event.get("input") or {}
    validated = validate(_input, INPUT_SCHEMA)
    if validated.get("errors"):
        return {"errors": validated["errors"]}
    settings = validated["validated_input"]["settings"]

    # 2) download any remote files
    for key in ("video_init_path", "video_mask_path"):
        if key in settings:
            try:
                settings[key] = _download_if_url(settings[key])
            except Exception:
                pass

    # 3) write settings to temp file
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as sf:
        json.dump(settings, sf)
        sf_path = sf.name

    # 4) run prediction
    video_local = generate_video.predict(settings_file=sf_path)
    os.remove(sf_path)

    # 5) configure boto3 S3 client
    bucket_name  = os.environ["BUCKET_NAME"]
    endpoint_url = os.environ["BUCKET_ENDPOINT_URL"]
    aws_key      = os.environ["BUCKET_ACCESS_KEY_ID"]
    aws_secret   = os.environ["BUCKET_SECRET_ACCESS_KEY"]

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        config=boto3.session.Config(s3={"addressing_style": "path"})
    )

    # 6) upload file
    s3_key = f"{uuid.uuid4()}.mp4"
    s3.upload_file(video_local, bucket_name, s3_key)

    # 7) cleanup local
    os.remove(video_local)

    # 8) construct public URL (path-style)
    video_url = f"{endpoint_url}/{bucket_name}/{s3_key}"

    return {"video": video_url}

runpod.serverless.start({"handler": handler})

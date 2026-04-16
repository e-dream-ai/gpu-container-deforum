import os
import time
import json
import uuid
import tempfile
import requests

import runpod
from runpod.serverless.utils.rp_validator import validate
from rp_schema import INPUT_SCHEMA
from predict import Predictor

import boto3

# Enforce a clean state after each job is done
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"

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

    start_time = time.perf_counter()

    def progress_callback(percent, preview=None):
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        countdown_ms = int((elapsed_ms / percent) * (100 - percent)) if percent > 0 else 0
        
        progress_data = {
            "progress": round(float(percent), 1),
            "countdown_ms": countdown_ms
        }
        
        if preview:
            progress_data["preview_frame"] = preview
            
        runpod.serverless.progress_update(event, progress_data)

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
    video_local = generate_video.predict(settings_file=sf_path, progress_callback=progress_callback)
    os.remove(sf_path)

    # 5) configure boto3 client for Cloudflare R2
    bucket_name  = os.environ["R2_BUCKET_NAME"]
    endpoint_url = os.environ["R2_ENDPOINT_URL"]  # https://<account-id>.r2.cloudflarestorage.com
    r2_key       = os.environ["R2_ACCESS_KEY_ID"]
    r2_secret    = os.environ["R2_SECRET_ACCESS_KEY"]

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=r2_key,
        aws_secret_access_key=r2_secret,
        region_name="auto",  # R2 uses 'auto' as region
        config=boto3.session.Config(s3={"addressing_style": "path"})
    )

    # 6) upload file to the specified directory (with fallback)
    upload_directory = os.environ.get("R2_UPLOAD_DIRECTORY", "test-renders")
    s3_key = f"{upload_directory}/{uuid.uuid4()}.mp4"
    s3.upload_file(video_local, bucket_name, s3_key)

    # 7) cleanup local
    os.remove(video_local)

    # 8) generate pre-signed download URL for secure access
    # Pre-signed URL allows temporary authenticated access to private R2 bucket
    # URL expires after specified time (24 hours by default)
    expiration_seconds = int(os.environ.get("R2_PRESIGNED_EXPIRY", "86400"))  # 24 hours default
    
    try:
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=expiration_seconds
        )
        
        return {
            "video": presigned_url,
            "s3_key": s3_key,
            "bucket": bucket_name,
            "expires_in": expiration_seconds,
            "refresh_worker": REFRESH_WORKER
        }
    except Exception as e:
        print(f"[ERROR] Failed to generate pre-signed URL: {e}")
        video_url = f"{endpoint_url}/{bucket_name}/{s3_key}"
        return {
            "video": video_url,
            "s3_key": s3_key,
            "bucket": bucket_name,
            "requires_auth": True,
            "refresh_worker": REFRESH_WORKER
        }

runpod.serverless.start({"handler": handler})

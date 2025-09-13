# SD XL Deforum Docker Image

This repository provides a Docker-based setup for **SD XL Deforum** featuring GPU-accelerated inference and a RunPod deployment handler.

## Features

- **Stable Diffusion XL Deforum**: Animation toolkit with advanced Deforum scripting.
- **Automatic Model + Deforum CLI Download**: On first GPU run, the Deforum code and required model checkpoints are fetched automatically.
- **Docker Image**: Based on `nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04` for seamless GPU support.
- **OpenCV Headless Enforcement**: Ensures only the headless OpenCV wheel is used to avoid GUI dependencies.
- **RunPod Handler**: Serverless function for hosting on RunPod's serverless framework, with optional Cloudflare R2 upload support.

## Prerequisites

- Docker Engine with GPU support (NVIDIA Docker).
- NVIDIA drivers and CUDA Toolkit on host.
- Python 3.10+ for local testing (optional).
- RunPod account for serverless deployment.

## Repository Structure

```text
├── Dockerfile-build                  # Base Docker build for Deforum
├── entrypoint.sh                     # Runtime entrypoint to enforce OpenCV headless
├── build-deforum-deploy.sh           # Build and deploy script
├── comprehensive-requirements.txt    # Pinned Python dependencies
└── README.md                         # This document
```

## Building the Docker Image

1. **Build with GPU support**:

   ```bash
   chmod +x build-deforum-deploy.sh
   ./build-deforum-deploy.sh
   ```

   - `<deforum-branch>` defaults to `dev`.
   - `[settings-file]` defaults to `test-settings.txt`.

2. **Result**:

   - Docker image tagged as `deforum-studio/animation-toolkit:<timestamp>-<branch>`.
   - Optional `comprehensive-requirements.txt` generated.

## Local Usage

Run a container manually:

```bash
docker run --gpus all -v $(pwd):/input \
  -e ROOT_PATH=/deforum_storage \
  deforum-studio/animation-toolkit:<tag> \
  deforum runsingle --file /input/your-settings.json
```

Output will be available in `/deforum_storage/output/video` and copied to `./output` by the build script.

## Deploying on RunPod

1. **Install dependencies**:

   ```bash
   pip install runpod
   ```

2. **Prepare handler**:

   - Ensure `runpod_handler.py` is present in project root.

3. **Configure RunPod**:

   ```bash
   export RUNPOD_API_KEY=YOUR_API_KEY_HERE
   ```

   - (Optional) Configure Cloudflare R2 bucket credentials in `handler.py`.

4. **Deploy**:

   ```bash
   runpod serverless deploy \
     --name sd-xl-deforum \
     --handler runpod_handler.handler \
     --image deforum-studio/animation-toolkit:<tag> \
     --memory 16384 \
     --gpu-count 1 \
     --region <your-region>
   ```

5. **Invoke**:

   ```bash
   runpod serverless invoke \
     --name sd-xl-deforum \
     --input '{"input": {"prompt": "A cinematic landscape", "steps": 30}}'
   ```

The response will include a `video` URL to your generated MP4.

## Advanced Configuration

- **Settings File**: Pass `settings_file` in payload to override JSON parameters.
- **Cloudflare R2 Upload**: Configure the following environment variables for R2 access:

### Cloudflare R2 Configuration

To enable video uploads to Cloudflare R2, set these environment variables:

```bash
export R2_BUCKET_NAME=your-bucket-name
export R2_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
export R2_ACCESS_KEY_ID=your-r2-access-key-id
export R2_SECRET_ACCESS_KEY=your-r2-secret-access-key
export R2_PUBLIC_DOMAIN=your-custom-domain.com  # Optional: for public URLs
```

**Getting R2 Credentials:**

1. Log in to your Cloudflare dashboard
2. Go to R2 Object Storage
3. Create a bucket if you haven't already
4. Go to "Manage R2 API tokens"
5. Create a new API token with R2 permissions
6. Your endpoint URL format: `https://<account-id>.r2.cloudflarestorage.com`

**Public Access (Optional):**

If you want public URLs for your videos, you can either:

- Set up a custom domain for your R2 bucket
- Use R2's public URL format (uncomment the appropriate line in `handler.py`)

---

> Happy animating with SD XL Deforum on Docker and RunPod!

# SD XL Deforum Docker Image

This repository provides a Docker-based setup for **SD XL Deforum** featuring GPU-accelerated inference and a RunPod deployment handler.

## Features

- **Stable Diffusion XL Deforum**: Animation toolkit with advanced Deforum scripting.
- **Automatic Model + Deforum CLI Download**: On first GPU run, the Deforum code and required model checkpoints are fetched automatically.
- **Docker Image**: Based on `nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04` for seamless GPU support.
- **OpenCV Headless Enforcement**: Ensures only the headless OpenCV wheel is used to avoid GUI dependencies.
- **RunPod Handler**: Serverless function for hosting on RunPod's serverless framework, with optional Cloudflare R2 upload support.
- **RunPod Network Storage**: Uses RunPod's network storage to serve models efficiently across serverless instances.

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

## CI/CD Build Process

### Automated Builds via GitHub Actions

This repository uses GitHub Actions to automatically build and push Docker images to Docker Hub:

1. **Trigger**: Automatic builds occur on every commit to the `main` branch
2. **Build Process**:
   - Uses the `Dockerfile-build` to create the image
   - Tags the image as `edreamai/deforum-studio:<timestamp>-<branch>`
   - Also creates a `latest` tag for the most recent build
   - Pushes both tags to Docker Hub registry

### Deployment Flow

The deployment process follows this workflow:

1. **Code Commit**: Push changes to the `main` branch
2. **Automated Build**: GitHub Actions automatically builds and pushes the Docker image to `docker.io/edreamai/deforum-studio`
3. **Image Tag**: Note the generated image tag from the GitHub Actions output (format: `<timestamp>-<branch>`)
4. **Serverless Deployment**: Update your serverless pod configuration to use the new image tag
5. **Release**: Deploy the updated configuration to your desired serverless environment

### Finding the Latest Image Tag

To find the correct image tag for deployment:

1. **GitHub Actions**: Check the latest successful workflow run in the "Actions" tab
2. **Docker Hub**: Visit Docker Hub to see all available tags

### Local Building (Development)

For local development and testing:

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
  edreamai/deforum-studio:<tag> \
  deforum runsingle --file /input/your-settings.json
```

Output will be available in `/deforum_storage/output/video` and copied to `./output` by the build script.

## Deploying on RunPod

This deployment uses **RunPod Network Storage** to serve models efficiently across serverless instances, eliminating the need to download models on each cold start.

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
   - **Network Storage**: The deployment leverages RunPod's network storage to cache models and dependencies, significantly reducing startup times for serverless functions.

4. **Deploy**:

   Use the image tag from the GitHub Actions build output:

   ```bash
   runpod serverless deploy \
     --name sd-xl-deforum \
     --handler runpod_handler.handler \
     --image edreamai/deforum-studio:<timestamp>-<branch> \
     --memory 16384 \
     --gpu-count 1 \
     --region <your-region>
   ```

   Replace `<timestamp>-<branch>` with the actual tag from the GitHub Actions build (e.g., `20250215123456-main`).

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

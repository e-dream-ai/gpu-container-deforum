
### 📁 Repo Structure (example)

```
deforum-comfyui-deploy/
├── Dockerfile
├── download_models.sh
├── upload_to_dockerhub.sh
├── requirements.txt
├── README.md
└── configs/
    └── comfyui_config.json
```


# Deforum + ComfyUI Docker Deployment

This repository packages [deforum-studio](https://github.com/XmYx/deforum-studio) and [ComfyUI](https://github.com/comfyanonymous/ComfyUI) into a single Docker image for scalable deployment with all necessary models preloaded.

## Features

- ⚡ One-click deployment with CUDA support
- 📦 Bundled model downloads for fast scaling
- 🧠 Includes Flux and other required models
- 🐳 DockerHub upload support

## Usage

### Build and push Docker image

```bash
./upload_to_dockerhub.sh
````

### Running the container

```bash
Example: docker run --gpus all -it -p 3000:3000 your-org/deforum-comfyui:latest
```

## Model Directory Structure

```
/workspace/models/
├── deforum/
├── flux/
└── comfyui/
```

Ensure `download_models.sh` uses appropriate links for your use case.

```
TODO's:
- The exact model download URLs (or Hugging Face repo names),
- `docker-compose.yml.

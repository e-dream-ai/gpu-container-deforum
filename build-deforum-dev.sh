#!/bin/bash

set -eox pipefail

DEFORUM_BRANCH=${1:-dev}
SETTINGS_FILE=${2:-test-settings.txt}  # Default settings file in current dir

timestamp=$(date +%Y%m%d%H%M%S)
version="${timestamp}-${DEFORUM_BRANCH}"
IMAGE_NAME="mixy89/ellaborate-chimpanzee-ops:${version}"

HUB_REPO="mixy89/ellaborate-chimpanzee-ops"
HUB_IMAGE="${HUB_REPO}:${version}"

# Check Docker disk space
docker_root=$(docker info --format '{{.DockerRootDir}}')
mount_point=$(df --output=target "$docker_root" | tail -1)
available_kb=$(df --output=avail "$mount_point" | tail -1)
available_gb=$((available_kb / 1024 / 1024))
threshold_gb=50
if (( available_gb < threshold_gb )); then
  echo "⚠️  Warning: Less than ${threshold_gb}GB available. Currently: ${available_gb}GB"
  echo "Attempting to clean up old Docker resources..."

  docker system prune -a -f --volumes

  # Recheck space
  available_kb=$(df --output=avail "$mount_point" | tail -1)
  available_gb=$((available_kb / 1024 / 1024))

  if (( available_gb < threshold_gb )); then
    echo "❌ Error: Still not enough space after cleanup. Available: ${available_gb}GB"
    exit 1
  else
    echo "✅ Space reclaimed. Continuing build..."
  fi
fi

# Step 1: Build base image without GPU steps
DOCKER_BUILDKIT=1 docker build \
  --build-arg DEFORUM_BRANCH="${DEFORUM_BRANCH}" \
  -t "${IMAGE_NAME}" \
  -f Dockerfile-dev-build .

# Step 2: Run container with GPU to trigger deforum model downloads
echo ""
echo "**************************************************"
echo "Running GPU initialization inside container"
echo "**************************************************"

container_id=$(docker run -d \
  --gpus all \
  -v "$(pwd)":/input \
  -e ROOT_PATH=/deforum_storage \
  ${IMAGE_NAME} \
  bash -c "\
    python3 src/handler.py   --test_input '{"input": {"settings": {"prompts":{"0":"Gargatuantan sacred castle"}}}}'
  ")


docker logs -f $container_id
docker wait $container_id > /tmp/exit_code
exit_code=$(cat /tmp/exit_code)

if [ "$exit_code" != "0" ]; then
    echo "Error: deforum run failed (exit code: $exit_code)"
    docker rm $container_id
    exit $exit_code
fi

# Extract output video before cleaning up the container
output_path_in_container="/deforum_storage/output/video"
output_path_on_host="./output"

mkdir -p "${output_path_on_host}"
docker cp "${container_id}:${output_path_in_container}" "${output_path_on_host}"

# Commit the initialized container (with models, configs, etc.)
docker commit $container_id "${IMAGE_NAME}"
docker rm $container_id

docker tag "${IMAGE_NAME}" "${HUB_IMAGE}"


echo ""
echo "**************************************************"
echo "Docker image '${IMAGE_NAME}' is ready with all dependencies and models bundled."
echo "You can now push it manually with:"
echo "  docker push ${IMAGE_NAME}"
echo "**************************************************"

echo ""
echo "**************************************************"
echo "Docker image '${HUB_IMAGE}' is ready with all dependencies and models bundled."
echo "Pushing to Docker Hub..."
docker push "${HUB_IMAGE}"
echo "✅ Push complete."
echo "**************************************************"

#!/bin/bash

set -eox pipefail

SETTINGS_FILE=${1:-test-settings.txt}

# Verify that the settings file exists
if [ ! -f "$SETTINGS_FILE" ]; then
  echo "❌ Error: Settings file '$SETTINGS_FILE' not found."
  exit 1
fi

# Find the most recent local image for deforum-studio/animation-toolkit
IMAGE_NAME=$(docker images --format '{{.Repository}}:{{.Tag}} {{.CreatedAt}}' \
  | grep '^deforum-studio/animation-toolkit:' \
  | sort -rk2 \
  | head -n1 \
  | awk '{print $1}')

if [ -z "$IMAGE_NAME" ]; then
  echo "❌ Error: No local deforum-studio/animation-toolkit image found."
  exit 1
fi

echo ""
echo "**************************************************"
echo "Using latest local image: ${IMAGE_NAME}"
echo "Settings file: ${SETTINGS_FILE}"
echo "**************************************************"

# Run container
container_id=$(docker run -d \
  --gpus all \
  -v "$(pwd)":/input \
  -e ROOT_PATH=/deforum_storage \
  "${IMAGE_NAME}" \
  deforum runsingle --file /input/${SETTINGS_FILE})

docker logs -f $container_id
docker wait $container_id > /tmp/exit_code
exit_code=$(cat /tmp/exit_code)

if [ "$exit_code" != "0" ]; then
  echo "❌ Error: deforum run failed (exit code: $exit_code)"
  docker rm $container_id
  exit $exit_code
fi

# Copy output
output_path_in_container="/deforum_storage/output/video"
output_path_on_host="./output"

mkdir -p "${output_path_on_host}"
docker cp "${container_id}:${output_path_in_container}" "${output_path_on_host}"

docker rm $container_id

echo ""
echo "✅ Deforum run complete. Output copied to '${output_path_on_host}'"

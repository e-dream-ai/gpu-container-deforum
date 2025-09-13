#!/bin/bash

set -euo pipefail

IMAGE_TAG=${1:-}
ENDPOINT_NAME=${2:-staging_deforum}

if [ -z "$IMAGE_TAG" ]; then
    echo "❌ Error: IMAGE_TAG is required as first argument"
    exit 1
fi

if [ -z "$RUNPOD_API_KEY" ]; then
    echo "❌ Error: RUNPOD_API_KEY environment variable is required"
    exit 1
fi

echo "🚀 Deploying to RunPod Serverless..."
echo "📦 Image: $IMAGE_TAG"
echo "🏷️  Endpoint: $ENDPOINT_NAME"

# Check if endpoint exists
ENDPOINT_EXISTS=$(runpod serverless list | grep -c "$ENDPOINT_NAME" || true)

if [ "$ENDPOINT_EXISTS" -eq 0 ]; then
    echo "📝 Creating new RunPod serverless endpoint..."
    
    runpod serverless deploy \
        --name "$ENDPOINT_NAME" \
        --handler "src.handler.handler" \
        --image "$IMAGE_TAG" \
        --memory 16384 \
        --gpu-count 1 \
        --gpu-type "NVIDIA RTX 4090" \
        --min-workers 0 \
        --max-workers 3 \
        --idle-timeout 60 \
        --env R2_BUCKET_NAME="$R2_BUCKET_NAME" \
        --env R2_ENDPOINT_URL="$R2_ENDPOINT_URL" \
        --env R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" \
        --env R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" \
        --env R2_PUBLIC_DOMAIN="$R2_PUBLIC_DOMAIN" \
        --region "EU-RO-1" \
        --volume-size 20 \
        --volume-mount-path "/workspace"
        
    echo "✅ New endpoint '$ENDPOINT_NAME' created successfully!"
else
    echo "🔄 Updating existing RunPod serverless endpoint..."
    
    runpod serverless update \
        --name "$ENDPOINT_NAME" \
        --image "$IMAGE_TAG" \
        --env R2_BUCKET_NAME="$R2_BUCKET_NAME" \
        --env R2_ENDPOINT_URL="$R2_ENDPOINT_URL" \
        --env R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" \
        --env R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" \
        --env R2_PUBLIC_DOMAIN="$R2_PUBLIC_DOMAIN"
        
    echo "✅ Endpoint '$ENDPOINT_NAME' updated successfully!"
fi

# Get endpoint info
echo ""
echo "📋 Endpoint Information:"
runpod serverless status --name "$ENDPOINT_NAME"

echo ""
echo "🎉 Deployment completed successfully!"
echo "🔗 You can now invoke your endpoint with:"
echo "   runpod serverless invoke --name '$ENDPOINT_NAME' --input '{\"input\": {\"settings\": {\"prompt\": \"A cinematic landscape\", \"steps\": 30}}}'"

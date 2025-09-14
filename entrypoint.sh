#!/usr/bin/env bash
set -e

# 1) Remove any unwanted OpenCV desktop build
pip uninstall -y opencv-python   || true

# 2) Make absolutely sure the headless wheel is in use
pip install --no-deps --force-reinstall opencv-python-headless

# 3) Ensure cache directories exist (in case they weren't created properly)
mkdir -p /deforum_storage/huggingface/transformers
mkdir -p /deforum_storage/huggingface/datasets
mkdir -p /deforum_storage/huggingface/hub
mkdir -p /deforum_storage/models

# 4) Set environment variables for Hugging Face cache
export HF_HOME=/deforum_storage/huggingface
export TRANSFORMERS_CACHE=/deforum_storage/huggingface/transformers
export HF_DATASETS_CACHE=/deforum_storage/huggingface/datasets
export HF_HUB_CACHE=/deforum_storage/huggingface/hub

# 5) Change to the deforum working directory and launch Runpod's serverless
cd /workdir/deforum
exec python3 src/handler.py "$@"
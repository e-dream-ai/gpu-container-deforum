#!/usr/bin/env bash
set -e

# 1) Remove any unwanted OpenCV desktop build
pip uninstall -y opencv-python   || true

# 2) Make absolutely sure the headless wheel is in use
pip install --no-deps --force-reinstall opencv-python-headless

# 3) Launch Runpod’s serverless with the given handler (e.g. "handler.handler")
exec python3 src/handler.py "$@"
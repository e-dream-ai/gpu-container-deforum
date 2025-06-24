# Install OpenCV
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

RUN apt-get update && \
    apt-get install -y git python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install opencv-python-headless numpy

# Copy the entrypoint script
COPY app.py /workspace/app.py

# Set the entrypoint
ENTRYPOINT ["python3", "/workspace/app.py"]
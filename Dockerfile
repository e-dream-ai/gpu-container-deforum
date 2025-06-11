# Use the specific NVIDIA CUDA image
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

# Set a working directory
WORKDIR /workdir

# Install necessary packages for Git, Python
RUN apt-get update && \
    apt-get install -y git python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Clone the develop branch of the deforum repository
RUN git clone --branch dev https://github.com/XmYx/deforum.git deforum

# Change to the cloned directory
WORKDIR /workdir/deforum

# Install the project in editable mode with dev dependencies
RUN pip install -e .[dev]

# Clone the ComfyUI repository with a specific commit
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /workdir/deforum/src/ComfyUI
WORKDIR /workdir/deforum/src/ComfyUI
# RUN git checkout daa92a8ff4d3e75a3b17bb1a6b6c508b27264ff5

# Reset the working directory
WORKDIR /workdir/deforum
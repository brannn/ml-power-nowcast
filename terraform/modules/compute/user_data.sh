#!/bin/bash
set -euo pipefail

# Log all output
exec > >(tee /var/log/user-data.log) 2>&1

echo "Starting user data script at $(date)"

# Update system
export DEBIAN_FRONTEND=noninteractive

# Fix apt-pkg issues first
apt-get update --fix-missing
apt-get install -y --reinstall python3-apt
apt-get update
apt-get upgrade -y

# Install SSM agent (critical for Ubuntu)
snap install amazon-ssm-agent --classic
systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service

# Install basic dependencies
apt-get install -y \
    curl \
    wget \
    git \
    htop \
    unzip \
    build-essential \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release

# Ensure Python 3.10 development packages are installed (STANDARDIZED ON 3.10)
apt-get install -y python3.10-venv python3.10-dev python3-pip

# Verify Python 3.10 is the system default (DO NOT CHANGE)
echo "System Python version: $(python3 --version)"

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Docker installation removed - not needed for basic ML development

# Install NVIDIA drivers and CUDA (only for GPU instances)
if lspci | grep -i nvidia; then
    echo "GPU detected, installing NVIDIA drivers and CUDA"
    # Install NVIDIA driver
    apt-get install -y ubuntu-drivers-common
    ubuntu-drivers autoinstall

    # Install CUDA toolkit
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
    dpkg -i cuda-keyring_1.1-1_all.deb
    apt-get update
    apt-get install -y cuda-toolkit-12-4
    rm cuda-keyring_1.1-1_all.deb

    # Add CUDA to PATH
    echo 'export PATH=/usr/local/cuda/bin:$PATH' >> /home/ubuntu/.bashrc
    echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> /home/ubuntu/.bashrc
else
    echo "No GPU detected, skipping NVIDIA driver installation"
fi

# Set environment variables
echo 'export MLFLOW_TRACKING_URI=${mlflow_tracking_uri}' >> /home/ubuntu/.bashrc
echo 'export AWS_DEFAULT_REGION=us-west-2' >> /home/ubuntu/.bashrc

# Create project directory
mkdir -p /home/ubuntu/ml-power-nowcast
chown ubuntu:ubuntu /home/ubuntu/ml-power-nowcast

# Install common Python packages system-wide (using Python 3.10)
echo "Installing Python packages with system Python 3.10"
python3 -m pip install --upgrade pip
python3 -m pip install --no-cache-dir \
    mlflow \
    pandas \
    numpy \
    scikit-learn \
    xgboost \
    torch \
    fastapi \
    uvicorn \
    jupyter \
    boto3 \
    matplotlib \
    seaborn

# Create project directory
mkdir -p /home/ubuntu/ml-power-nowcast
chown ubuntu:ubuntu /home/ubuntu/ml-power-nowcast

# Clean up
apt-get autoremove -y
apt-get autoclean

echo "User data script completed successfully at $(date)" | tee /var/log/user-data-completion.log

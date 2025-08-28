#!/bin/bash
set -euo pipefail

# Update system
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
    postgresql-client

# Install Python 3.12 and pip
add-apt-repository ppa:deadsnakes/ppa -y
apt-get update
apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip

# Make python3.12 the default python3
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install MLflow and dependencies
python3.12 -m pip install --upgrade pip
python3.12 -m pip install \
    mlflow[extras] \
    boto3 \
    psycopg2-binary

# Create MLflow user and directories
useradd -m -s /bin/bash mlflow
mkdir -p /opt/mlflow
chown mlflow:mlflow /opt/mlflow

# Create MLflow systemd service
cat > /etc/systemd/system/mlflow.service << 'EOF'
[Unit]
Description=MLflow Tracking Server
After=network.target

[Service]
Type=simple
User=mlflow
WorkingDirectory=/opt/mlflow
Environment=AWS_DEFAULT_REGION=us-west-2
ExecStart=/usr/bin/python3.12 -m mlflow server \
    --backend-store-uri sqlite:///mlflow.db \
    --default-artifact-root s3://${s3_bucket}/artifacts \
    --host 0.0.0.0 \
    --port 5001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start MLflow service
systemctl daemon-reload
systemctl enable mlflow
systemctl start mlflow

echo "MLflow server setup completed successfully" > /var/log/mlflow-setup-completion.log

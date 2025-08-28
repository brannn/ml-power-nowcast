packer {
  required_version = ">= 1.9"
  required_plugins {
    amazon = {
      version = ">= 1.2.8"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

# Variables
variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "instance_type" {
  type    = string
  default = "m6i.xlarge"
}

variable "project_name" {
  type    = string
  default = "ml-power-nowcast"
}

# Data source for Ubuntu 22.04 LTS AMI
data "amazon-ami" "ubuntu" {
  filters = {
    name                = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
    root-device-type    = "ebs"
    virtualization-type = "hvm"
  }
  most_recent = true
  owners      = ["099720109477"] # Canonical
  region      = var.aws_region
}

# Build configuration
source "amazon-ebs" "ubuntu-ml" {
  ami_name      = "${var.project_name}-ubuntu-ml-{{timestamp}}"
  instance_type = var.instance_type
  region        = var.aws_region
  source_ami    = data.amazon-ami.ubuntu.id
  ssh_username  = "ubuntu"

  # Use temporary security group for SSH access during build
  temporary_security_group_source_cidrs = ["0.0.0.0/0"]

  # EBS configuration
  ebs_optimized = true
  
  launch_block_device_mappings {
    device_name           = "/dev/sda1"
    volume_size           = 100
    volume_type           = "gp3"
    delete_on_termination = true
    encrypted             = true
  }

  # Tags for the AMI
  tags = {
    Name         = "${var.project_name}-ubuntu-ml-{{timestamp}}"
    Project      = var.project_name
    OS           = "Ubuntu 22.04 LTS"
    Type         = "ML Base AMI"
    BuildDate    = "{{timestamp}}"
    Description  = "Ubuntu 22.04 LTS with ML dependencies, NVIDIA drivers, and SSM agent"
  }

  # Tags for the snapshot
  snapshot_tags = {
    Name         = "${var.project_name}-ubuntu-ml-{{timestamp}}-snapshot"
    Project      = var.project_name
    Type         = "ML Base AMI Snapshot"
    BuildDate    = "{{timestamp}}"
  }
}

# Build steps
build {
  name = "ubuntu-ml-base"
  sources = [
    "source.amazon-ebs.ubuntu-ml"
  ]

  # Wait for cloud-init to complete
  provisioner "shell" {
    inline = [
      "echo 'Waiting for cloud-init to complete...'",
      "cloud-init status --wait"
    ]
  }

  # Update system and install basic packages
  provisioner "shell" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "sudo apt-get update --fix-missing",
      "sudo apt-get install -y --reinstall python3-apt",
      "sudo apt-get update",
      "sudo apt-get upgrade -y",
      "sudo apt-get install -y curl wget git htop unzip build-essential software-properties-common ca-certificates gnupg lsb-release"
    ]
  }

  # Install SSM agent (critical for Ubuntu)
  provisioner "shell" {
    inline = [
      "sudo snap install amazon-ssm-agent --classic",
      "sudo systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service"
    ]
  }

  # Install Python 3.10 development packages (system Python)
  provisioner "shell" {
    inline = [
      "sudo apt-get install -y python3.10-venv python3.10-dev python3-pip",
      "python3 --version"
    ]
  }

  # Install AWS CLI v2
  provisioner "shell" {
    inline = [
      "curl 'https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip' -o 'awscliv2.zip'",
      "unzip awscliv2.zip",
      "sudo ./aws/install",
      "rm -rf aws awscliv2.zip"
    ]
  }

  # Docker installation removed - not needed for basic ML development

  # Install NVIDIA drivers
  provisioner "shell" {
    inline = [
      "sudo apt-get install -y ubuntu-drivers-common",
      "sudo ubuntu-drivers autoinstall"
    ]
  }

  # Install CUDA repository
  provisioner "shell" {
    inline = [
      "wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb",
      "sudo dpkg -i cuda-keyring_1.1-1_all.deb",
      "sudo apt-get update",
      "rm cuda-keyring_1.1-1_all.deb"
    ]
  }

  # Install CUDA toolkit (may cause disconnect due to size)
  provisioner "shell" {
    expect_disconnect = true
    inline = [
      "sudo apt-get install -y cuda-toolkit-12-4",
      "echo 'export PATH=/usr/local/cuda/bin:$PATH' | sudo tee -a /etc/environment",
      "echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' | sudo tee -a /etc/environment"
    ]
  }

  # Install common ML Python packages system-wide to avoid PATH warnings
  provisioner "shell" {
    inline = [
      "sudo python3 -m pip install --upgrade pip",
      "sudo python3 -m pip install --no-cache-dir --force-reinstall --ignore-installed mlflow[extras] pandas numpy scikit-learn xgboost torch torchvision torchaudio fastapi uvicorn jupyter boto3 matplotlib seaborn plotly"
    ]
  }

  # Clone project repository (public HTTPS)
  provisioner "shell" {
    inline = [
      "cd /home/ubuntu",
      "git clone https://github.com/brannn/ml-power-nowcast.git ml-power-nowcast",
      "chown -R ubuntu:ubuntu ml-power-nowcast"
    ]
  }

  # Set up Python virtual environment and install dependencies
  provisioner "shell" {
    inline = [
      "cd /home/ubuntu/ml-power-nowcast",
      "python3 -m venv .venv",
      ". .venv/bin/activate && pip install --upgrade pip",
      ". .venv/bin/activate && pip install --no-cache-dir --force-reinstall -r requirements.txt",
      "chown -R ubuntu:ubuntu .venv"
    ]
  }

  # Set up environment configuration
  provisioner "shell" {
    inline = [
      "echo 'export PATH=$HOME/.local/bin:$PATH' >> /home/ubuntu/.bashrc",
      "echo 'export MLFLOW_TRACKING_URI=http://localhost:5001' >> /home/ubuntu/.bashrc",
      "echo 'export AWS_DEFAULT_REGION=us-west-2' >> /home/ubuntu/.bashrc",
      "echo '. /home/ubuntu/ml-power-nowcast/.venv/bin/activate' >> /home/ubuntu/.bashrc"
    ]
  }

  # Clean up
  provisioner "shell" {
    inline = [
      "sudo apt-get autoremove -y",
      "sudo apt-get autoclean",
      "sudo rm -rf /var/lib/apt/lists/*",
      "sudo rm -rf /tmp/*",
      "sudo rm -rf /var/tmp/*"
    ]
  }
}

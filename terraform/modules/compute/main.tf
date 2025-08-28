terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data source for Ubuntu 22.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Data source for custom ML AMI (if available)
data "aws_ami" "custom_ml" {
  count       = var.use_custom_ami ? 1 : 0
  most_recent = true
  owners      = ["self"]

  filter {
    name   = "name"
    values = ["${var.project_name}-ubuntu-ml-*"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# Launch template for ML instances
resource "aws_launch_template" "ml_instance" {
  name_prefix   = "${var.project_name}-${var.environment}-ml-"
  image_id      = var.use_custom_ami ? data.aws_ami.custom_ml[0].id : data.aws_ami.ubuntu.id
  instance_type = var.instance_type

  vpc_security_group_ids = var.security_group_ids

  iam_instance_profile {
    name = var.instance_profile_name
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    mlflow_tracking_uri = var.mlflow_tracking_uri
    s3_bucket          = var.mlflow_bucket_name
  }))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "${var.project_name}-${var.environment}"
      Environment = var.environment
      Project     = var.project_name
      Type        = "ml-workload"
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ml-template"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ML development instance (g6f.xlarge)
resource "aws_instance" "ml_dev" {
  count = var.create_dev_instance ? 1 : 0

  launch_template {
    id      = aws_launch_template.ml_instance.id
    version = "$Latest"
  }

  instance_type = var.dev_instance_type
  subnet_id     = var.private_subnet_ids[0]

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    Type        = "development"
  }
}

# ML production instance (g6.xlarge)
resource "aws_instance" "ml_prod" {
  count = var.create_prod_instance ? 1 : 0

  launch_template {
    id      = aws_launch_template.ml_instance.id
    version = "$Latest"
  }

  instance_type = var.prod_instance_type
  subnet_id     = var.private_subnet_ids[0]

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    Type        = "production"
  }
}

# MLflow server instance (optional dedicated instance)
resource "aws_instance" "mlflow_server" {
  count = var.create_mlflow_server ? 1 : 0

  ami           = var.use_custom_ami ? data.aws_ami.custom_ml[0].id : data.aws_ami.ubuntu.id
  instance_type = var.mlflow_instance_type
  subnet_id     = var.private_subnet_ids[0]

  vpc_security_group_ids = [var.mlflow_security_group_id]
  iam_instance_profile   = var.instance_profile_name

  user_data = base64encode(templatefile("${path.module}/mlflow_server_user_data.sh", {
    s3_bucket = var.mlflow_bucket_name
  }))

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-mlflow-server"
    Environment = var.environment
    Project     = var.project_name
    Type        = "mlflow-server"
  }
}

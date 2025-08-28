terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# IAM Role for EC2 instances with SSM access
resource "aws_iam_role" "ec2_ssm_role" {
  name = "${var.project_name}-${var.environment}-ec2-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2-ssm-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Attach SSM managed policy
resource "aws_iam_role_policy_attachment" "ssm_managed_instance_core" {
  role       = aws_iam_role.ec2_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Additional policy for S3 access (MLflow artifacts)
resource "aws_iam_role_policy" "s3_mlflow_access" {
  name = "${var.project_name}-${var.environment}-s3-mlflow-access"
  role = aws_iam_role.ec2_ssm_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.mlflow_bucket_name}",
          "arn:aws:s3:::${var.mlflow_bucket_name}/*"
        ]
      }
    ]
  })
}

# Instance profile for EC2
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2_ssm_role.name

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2-profile"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Security group for ML instances
resource "aws_security_group" "ml_instances" {
  name_prefix = "${var.project_name}-${var.environment}-ml-"
  vpc_id      = var.vpc_id

  # MLflow server port (if running locally)
  ingress {
    from_port   = 5001
    to_port     = 5001
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr_block]
    description = "MLflow tracking server"
  }

  # FastAPI port
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr_block]
    description = "FastAPI serving"
  }

  # MLflow model serving port
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr_block]
    description = "MLflow model serving"
  }

  # Jupyter notebook port (optional)
  ingress {
    from_port   = 8888
    to_port     = 8888
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr_block]
    description = "Jupyter notebook"
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ml-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Security group for MLflow server (if dedicated instance)
resource "aws_security_group" "mlflow_server" {
  name_prefix = "${var.project_name}-${var.environment}-mlflow-"
  vpc_id      = var.vpc_id

  # MLflow server port
  ingress {
    from_port   = 5001
    to_port     = 5001
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr_block]
    description = "MLflow tracking server"
  }

  # All outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-mlflow-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

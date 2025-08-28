terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# S3 bucket for MLflow artifacts
resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = var.bucket_name

  tags = {
    Name        = var.bucket_name
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "MLflow artifacts storage"
  }
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  rule {
    id     = "mlflow_artifacts_lifecycle"
    status = "Enabled"

    filter {
      prefix = ""
    }

    # Transition to IA after 30 days
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    # Transition to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Delete old versions after 365 days
    noncurrent_version_expiration {
      noncurrent_days = 365
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Optional: S3 bucket for data storage (if needed)
resource "aws_s3_bucket" "data_storage" {
  count  = var.create_data_bucket ? 1 : 0
  bucket = "${var.bucket_name}-data"

  tags = {
    Name        = "${var.bucket_name}-data"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "ML data storage"
  }
}

resource "aws_s3_bucket_versioning" "data_storage" {
  count  = var.create_data_bucket ? 1 : 0
  bucket = aws_s3_bucket.data_storage[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_storage" {
  count  = var.create_data_bucket ? 1 : 0
  bucket = aws_s3_bucket.data_storage[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "data_storage" {
  count  = var.create_data_bucket ? 1 : 0
  bucket = aws_s3_bucket.data_storage[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

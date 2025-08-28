variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ml-power-nowcast"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where security groups will be created"
  type        = string
}

variable "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  type        = string
}

variable "mlflow_bucket_name" {
  description = "Name of the S3 bucket for MLflow artifacts"
  type        = string
}

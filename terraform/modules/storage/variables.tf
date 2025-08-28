variable "bucket_name" {
  description = "Name of the S3 bucket for MLflow artifacts"
  type        = string
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ml-power-nowcast"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "create_data_bucket" {
  description = "Whether to create an additional bucket for data storage"
  type        = bool
  default     = false
}

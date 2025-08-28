variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ml-power-nowcast"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "instance_type" {
  description = "Default EC2 instance type"
  type        = string
  default     = "g6f.xlarge"
}

variable "dev_instance_type" {
  description = "EC2 instance type for development"
  type        = string
  default     = "g6f.xlarge"
}

variable "prod_instance_type" {
  description = "EC2 instance type for production"
  type        = string
  default     = "g6.xlarge"
}

variable "mlflow_instance_type" {
  description = "EC2 instance type for MLflow server"
  type        = string
  default     = "t3.medium"
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for ML instances"
  type        = list(string)
}

variable "mlflow_security_group_id" {
  description = "Security group ID for MLflow server"
  type        = string
}

variable "instance_profile_name" {
  description = "Name of the IAM instance profile"
  type        = string
}

variable "mlflow_tracking_uri" {
  description = "MLflow tracking URI"
  type        = string
  default     = "http://localhost:5001"
}

variable "mlflow_bucket_name" {
  description = "Name of the S3 bucket for MLflow artifacts"
  type        = string
}

variable "root_volume_size" {
  description = "Size of the root EBS volume in GB"
  type        = number
  default     = 100
}

variable "use_custom_ami" {
  description = "Whether to use custom ML AMI instead of base Ubuntu"
  type        = bool
  default     = false
}

variable "create_dev_instance" {
  description = "Whether to create development instance"
  type        = bool
  default     = true
}

variable "create_prod_instance" {
  description = "Whether to create production instance"
  type        = bool
  default     = false
}

variable "create_mlflow_server" {
  description = "Whether to create dedicated MLflow server instance"
  type        = bool
  default     = false
}

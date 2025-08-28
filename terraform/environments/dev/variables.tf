variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ml-power-nowcast"
}

variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
  default     = "ml-dev"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24"]
}

variable "dev_instance_type" {
  description = "EC2 instance type for development"
  type        = string
  default     = "m6i.xlarge"
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

variable "mlflow_tracking_uri" {
  description = "MLflow tracking URI"
  type        = string
  default     = "http://localhost:5001"
}

variable "root_volume_size" {
  description = "Size of the root EBS volume in GB"
  type        = number
  default     = 100
}

variable "use_custom_ami" {
  description = "Whether to use custom ML AMI instead of base Ubuntu"
  type        = bool
  default     = true  # Use our production-ready AMI with all dependencies pre-installed
}

variable "instance_mode" {
  description = "Instance deployment mode: 'dev' for g6f.xlarge, 'prod' for g6.xlarge, 'both' for both instances"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "prod", "both"], var.instance_mode)
    error_message = "Instance mode must be 'dev', 'prod', or 'both'."
  }
}

variable "create_mlflow_server" {
  description = "Whether to create dedicated MLflow server instance"
  type        = bool
  default     = false
}

variable "create_data_bucket" {
  description = "Whether to create an additional bucket for data storage"
  type        = bool
  default     = false
}

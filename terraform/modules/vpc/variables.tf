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
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "enable_ssm_endpoints" {
  description = "Enable SSM VPC endpoints for private subnet access"
  type        = bool
  default     = true
}

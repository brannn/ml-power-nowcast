terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "dev"
      Project     = "ml-power-nowcast"
      ManagedBy   = "terraform"
    }
  }
}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

locals {
  environment         = "dev"
  mlflow_bucket_name = "${var.project_name}-${local.environment}-mlflow-${random_string.suffix.result}"
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  vpc_name               = var.vpc_name
  vpc_cidr              = var.vpc_cidr
  public_subnet_cidrs   = var.public_subnet_cidrs
  private_subnet_cidrs  = var.private_subnet_cidrs
  environment           = local.environment
  enable_ssm_endpoints  = true
}

# Storage Module
module "storage" {
  source = "../../modules/storage"

  bucket_name        = local.mlflow_bucket_name
  project_name       = var.project_name
  environment        = local.environment
  create_data_bucket = var.create_data_bucket
}

# Security Module
module "security" {
  source = "../../modules/security"

  project_name       = var.project_name
  environment        = local.environment
  vpc_id            = module.vpc.vpc_id
  vpc_cidr_block    = module.vpc.vpc_cidr_block
  mlflow_bucket_name = module.storage.mlflow_artifacts_bucket_name
}

# Compute Module
module "compute" {
  source = "../../modules/compute"

  project_name              = var.project_name
  environment              = local.environment
  dev_instance_type        = var.dev_instance_type
  prod_instance_type       = var.prod_instance_type
  mlflow_instance_type     = var.mlflow_instance_type
  private_subnet_ids       = module.vpc.private_subnet_ids
  security_group_ids       = [module.security.ml_instances_security_group_id]
  mlflow_security_group_id = module.security.mlflow_server_security_group_id
  instance_profile_name    = module.security.ec2_instance_profile_name
  mlflow_tracking_uri      = var.mlflow_tracking_uri
  mlflow_bucket_name       = module.storage.mlflow_artifacts_bucket_name
  root_volume_size         = var.root_volume_size
  use_custom_ami           = var.use_custom_ami
  create_dev_instance      = contains(["dev", "both"], var.instance_mode)
  create_prod_instance     = contains(["prod", "both"], var.instance_mode)
  create_mlflow_server     = var.create_mlflow_server
}

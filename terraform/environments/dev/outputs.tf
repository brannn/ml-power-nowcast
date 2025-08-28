output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "mlflow_bucket_name" {
  description = "Name of the MLflow artifacts S3 bucket"
  value       = module.storage.mlflow_artifacts_bucket_name
}

output "ml_dev_instance_id" {
  description = "ID of the ML development instance"
  value       = module.compute.ml_dev_instance_id
}

output "ml_dev_private_ip" {
  description = "Private IP of the ML development instance"
  value       = module.compute.ml_dev_private_ip
}

output "ml_prod_instance_id" {
  description = "ID of the ML production instance"
  value       = module.compute.ml_prod_instance_id
}

output "mlflow_server_instance_id" {
  description = "ID of the MLflow server instance"
  value       = module.compute.mlflow_server_instance_id
}

output "ssm_connect_command_dev" {
  description = "AWS CLI command to connect to development instance via SSM"
  value = module.compute.ml_dev_instance_id != null ? "aws ssm start-session --target ${module.compute.ml_dev_instance_id} --region ${var.aws_region}" : "No development instance created"
}

output "ssm_connect_command_prod" {
  description = "AWS CLI command to connect to production instance via SSM"
  value = module.compute.ml_prod_instance_id != null ? "aws ssm start-session --target ${module.compute.ml_prod_instance_id} --region ${var.aws_region}" : "No production instance created"
}

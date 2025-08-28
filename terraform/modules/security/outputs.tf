output "ec2_instance_profile_name" {
  description = "Name of the EC2 instance profile"
  value       = aws_iam_instance_profile.ec2_profile.name
}

output "ec2_ssm_role_arn" {
  description = "ARN of the EC2 SSM role"
  value       = aws_iam_role.ec2_ssm_role.arn
}

output "ml_instances_security_group_id" {
  description = "Security group ID for ML instances"
  value       = aws_security_group.ml_instances.id
}

output "mlflow_server_security_group_id" {
  description = "Security group ID for MLflow server"
  value       = aws_security_group.mlflow_server.id
}

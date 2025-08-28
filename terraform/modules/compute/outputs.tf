output "ml_dev_instance_id" {
  description = "ID of the ML development instance"
  value       = var.create_dev_instance ? aws_instance.ml_dev[0].id : null
}

output "ml_dev_private_ip" {
  description = "Private IP of the ML development instance"
  value       = var.create_dev_instance ? aws_instance.ml_dev[0].private_ip : null
}

output "ml_prod_instance_id" {
  description = "ID of the ML production instance"
  value       = var.create_prod_instance ? aws_instance.ml_prod[0].id : null
}

output "ml_prod_private_ip" {
  description = "Private IP of the ML production instance"
  value       = var.create_prod_instance ? aws_instance.ml_prod[0].private_ip : null
}

output "mlflow_server_instance_id" {
  description = "ID of the MLflow server instance"
  value       = var.create_mlflow_server ? aws_instance.mlflow_server[0].id : null
}

output "mlflow_server_private_ip" {
  description = "Private IP of the MLflow server instance"
  value       = var.create_mlflow_server ? aws_instance.mlflow_server[0].private_ip : null
}

output "launch_template_id" {
  description = "ID of the launch template"
  value       = aws_launch_template.ml_instance.id
}

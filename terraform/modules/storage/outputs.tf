output "mlflow_artifacts_bucket_name" {
  description = "Name of the MLflow artifacts S3 bucket"
  value       = aws_s3_bucket.mlflow_artifacts.bucket
}

output "mlflow_artifacts_bucket_arn" {
  description = "ARN of the MLflow artifacts S3 bucket"
  value       = aws_s3_bucket.mlflow_artifacts.arn
}

output "data_storage_bucket_name" {
  description = "Name of the data storage S3 bucket"
  value       = var.create_data_bucket ? aws_s3_bucket.data_storage[0].bucket : null
}

output "data_storage_bucket_arn" {
  description = "ARN of the data storage S3 bucket"
  value       = var.create_data_bucket ? aws_s3_bucket.data_storage[0].arn : null
}

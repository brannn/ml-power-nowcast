output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.ml_dev.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.ml_dev.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.ml_dev.id
}

output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways"
  value       = aws_nat_gateway.ml_dev[*].id
}

output "ssm_endpoint_security_group_id" {
  description = "Security group ID for SSM endpoints"
  value       = var.enable_ssm_endpoints ? aws_security_group.ssm_endpoints[0].id : null
}

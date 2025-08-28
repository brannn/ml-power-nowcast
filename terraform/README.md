# Infrastructure Documentation

This directory contains Terraform configurations for deploying ML Power Nowcast infrastructure on AWS. The infrastructure supports machine learning workloads with GPU acceleration, secure access through AWS Systems Manager, and MLflow experiment tracking.

## Architecture Overview

The infrastructure creates a dedicated VPC named 'ml-dev' in the us-west-2 region. This VPC contains both public and private subnets across multiple availability zones for high availability. Private subnets host the ML workload instances, while public subnets contain NAT gateways for outbound internet access.

Security follows the principle of least privilege. EC2 instances have no direct internet access and use AWS Systems Manager Session Manager for remote administration. This eliminates SSH key management and reduces attack surface. IAM roles provide necessary permissions for S3 access and Systems Manager functionality.

The compute layer supports both development and production workloads. Development instances use g6f.xlarge instances with L4 GPUs for cost-effective experimentation. Production instances use g6.xlarge instances for optimized performance. All instances run Ubuntu 22.04 LTS with pre-installed ML dependencies.

Storage infrastructure includes S3 buckets for MLflow artifacts with appropriate lifecycle policies. Buckets use server-side encryption and block public access. Versioning enables artifact history tracking and recovery capabilities.

## Module Structure

The Terraform configuration uses a modular approach for reusability and maintainability. Each module encapsulates related resources and exposes necessary outputs for integration with other modules.

The VPC module creates the network foundation including subnets, route tables, NAT gateways, and VPC endpoints. VPC endpoints for Systems Manager services enable private subnet instances to communicate with AWS services without internet gateway traversal.

The security module defines IAM roles, instance profiles, and security groups. IAM roles follow least privilege principles, granting only necessary permissions for ML workloads and Systems Manager access. Security groups restrict network access to required ports and protocols.

The compute module manages EC2 instances and launch templates. Launch templates standardize instance configuration including AMI selection, instance profiles, and user data scripts. The module supports both custom ML AMIs and base Ubuntu images.

The storage module creates S3 buckets with appropriate security and lifecycle configurations. Bucket policies restrict access to authorized IAM roles while enabling MLflow artifact storage and retrieval.

## Prerequisites

Terraform version 1.6 or later is required for compatibility with the AWS provider version used in these configurations. The AWS CLI must be installed and configured with appropriate credentials for the target AWS account.

AWS credentials require permissions for VPC management, EC2 instance creation, IAM role management, and S3 bucket operations. The deploying user or role should have administrative permissions or specific permissions for all resources defined in the modules.

Packer version 1.9 or later is recommended for building custom AMIs, though the infrastructure can deploy using base Ubuntu AMIs if custom images are not available.

## Deployment Process

Infrastructure deployment follows a sequential process starting with the VPC foundation and progressing through security, storage, and compute resources. Terraform handles dependency ordering automatically based on resource references.

Begin deployment by initializing Terraform in the environments/dev directory. This downloads required providers and prepares the working directory for plan and apply operations.

Review the Terraform plan output carefully before applying changes. The plan shows all resources that will be created, modified, or destroyed. Pay particular attention to any resource replacements that might cause service interruption.

Apply the configuration after plan review. Terraform will create resources in dependency order, typically completing VPC and security resources before compute instances. Initial deployment usually takes 10-15 minutes depending on the instance mode selected.

## Environment Management

The infrastructure uses a single shared environment to minimize costs while supporting both development and production workloads. The `instance_mode` variable controls which instance types are deployed, allowing you to switch between cost-effective development instances (g6f.xlarge) and performance-optimized production instances (g6.xlarge) as needed.

This consolidated approach reduces infrastructure complexity and costs for personal projects while maintaining the ability to test different instance configurations. The same VPC, security groups, and storage support both development and production workloads.

Variable files should never be committed to version control if they contain sensitive values. Use environment variables, Terraform Cloud, or AWS Parameter Store for sensitive configuration values.

## Security Considerations

All infrastructure follows security best practices for cloud deployments. Network access is restricted through security groups and NACLs. Instance access uses Systems Manager Session Manager instead of SSH keys.

S3 buckets block public access and use server-side encryption. IAM roles follow least privilege principles with specific permissions for required operations only. VPC endpoints ensure private subnet traffic to AWS services remains within the AWS network.

Terraform state files may contain sensitive information and should be stored securely. Use Terraform Cloud, S3 with encryption, or similar secure backends for production deployments. Never commit state files to version control.

## Monitoring and Maintenance

Infrastructure monitoring uses AWS CloudWatch for basic metrics and alerting. Custom metrics can be added for application-specific monitoring requirements. Log aggregation through CloudWatch Logs provides centralized logging for troubleshooting.

Regular maintenance includes security patch application through Systems Manager Patch Manager. AMI updates should be tested in development environments before production deployment. Terraform state should be backed up regularly to enable recovery from configuration drift.

Cost optimization involves regular review of instance utilization and rightsizing recommendations. Development instances should be stopped when not in use. Production instances may benefit from Reserved Instance pricing for predictable workloads.

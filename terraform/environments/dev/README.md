# ML Infrastructure Deployment

This directory contains Terraform configuration for the ML Power Nowcast infrastructure. The configuration supports both development and production workloads within a single shared VPC to minimize costs while maintaining operational flexibility.

## Environment Configuration

The infrastructure creates a shared ml-dev VPC that hosts both development and production instances as needed. Development workloads use g6f.xlarge instances for cost-effective GPU acceleration, while production workloads use g6.xlarge instances for optimized performance. The same networking, security, and storage components support both instance types.

The configuration uses an `instance_mode` variable to control which instances are created. Set this to "dev" for development work, "prod" for production deployment, or "both" when you need concurrent access to different instance types.

The environment uses a randomly generated suffix for S3 bucket names to ensure uniqueness across AWS accounts. This prevents naming conflicts when multiple developers deploy their own development environments.

## Prerequisites

Ensure AWS CLI is configured with credentials that have permissions to create VPC resources, EC2 instances, IAM roles, and S3 buckets. The credentials should have administrative access or specific permissions for all resources defined in the Terraform modules.

Terraform version 1.6 or later must be installed and available in the system PATH. Verify the installation by running `terraform version` before proceeding with deployment.

If using custom AMIs, ensure they are available in the us-west-2 region and accessible to the deploying AWS account. The configuration can fall back to base Ubuntu 22.04 LTS AMIs if custom images are not available.

## Deployment Steps

Initialize the Terraform working directory to download required providers and modules:

```bash
cd terraform/environments/dev
terraform init
```

Create a terraform.tfvars file with environment-specific configuration. This file should not be committed to version control if it contains sensitive values:

```hcl
# terraform.tfvars
instance_mode = "dev"          # "dev", "prod", or "both"
create_mlflow_server = false   # Set to true if you need dedicated MLflow server
use_custom_ami = false         # Set to true after building custom AMI
```

Review the planned changes before applying the configuration:

```bash
terraform plan
```

The plan output shows all resources that will be created. Review this carefully, particularly noting the VPC CIDR blocks, instance types, and S3 bucket names. The plan should show approximately 25-30 resources for a complete development environment.

Apply the configuration after reviewing the plan:

```bash
terraform apply
```

Terraform will prompt for confirmation before creating resources. Type "yes" to proceed with deployment. The initial deployment typically takes 10-15 minutes to complete.

## Instance Access

After deployment, connect to the development instance using AWS Systems Manager Session Manager. The Terraform output provides the exact command for connection:

```bash
aws ssm start-session --target <instance-id> --region us-west-2
```

Replace `<instance-id>` with the actual instance ID from the Terraform output. This connection method requires no SSH keys and works from any location with AWS CLI access.

The instance includes pre-installed Python 3.12, common ML libraries, and AWS CLI. For custom AMIs, additional ML dependencies and NVIDIA drivers are pre-configured. Base Ubuntu AMIs require manual installation of ML dependencies.

## MLflow Configuration

The development environment supports both local MLflow servers and remote MLflow deployments. For local development, start an MLflow server on the development instance:

```bash
# On the development instance
export MLFLOW_TRACKING_URI=http://0.0.0.0:5001
mlflow server --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root s3://<bucket-name>/artifacts \
  --host 0.0.0.0 --port 5001
```

Replace `<bucket-name>` with the MLflow artifacts bucket name from the Terraform output. The instance IAM role includes necessary permissions for S3 access.

For team development, consider deploying a dedicated MLflow server by setting `create_mlflow_server = true` in the terraform.tfvars file. This creates a separate t3.medium instance running MLflow server with PostgreSQL backend.

## Instance Management

Control costs by running only the instances you need. Switch between development and production instances using the `instance_mode` variable:

```bash
# Deploy development instance only
terraform apply -var="instance_mode=dev"

# Switch to production instance
terraform apply -var="instance_mode=prod"

# Run both instances simultaneously (higher cost)
terraform apply -var="instance_mode=both"
```

Stop instances when not in use to minimize charges:

```bash
aws ec2 stop-instances --instance-ids <instance-id> --region us-west-2
aws ec2 start-instances --instance-ids <instance-id> --region us-west-2
```

S3 storage costs are minimal but the bucket lifecycle policy automatically manages cost optimization through storage class transitions.

## Customization Options

The infrastructure supports several customization options through Terraform variables. Common modifications include instance types, storage sizes, and component enablement.

Modify instance types for different performance requirements:

```hcl
dev_instance_type = "g6.xlarge"   # Upgrade development instance
prod_instance_type = "g6.2xlarge" # Larger production instance
```

Increase root volume size for datasets or model storage:

```hcl
root_volume_size = 200  # 200 GB instead of default 100 GB
```

Enable additional components:

```hcl
create_mlflow_server = true   # Dedicated MLflow server
create_data_bucket = true     # Additional S3 bucket for data
use_custom_ami = true         # Use custom-built AMI
```

## Troubleshooting

Common deployment issues include insufficient AWS permissions, resource limits, or naming conflicts. Check AWS CloudTrail logs for detailed error information if deployment fails.

Instance connectivity issues often relate to security group configuration or Systems Manager agent status. Verify that the instance has the correct IAM role and that Systems Manager endpoints are accessible from the private subnet.

MLflow connectivity problems typically involve S3 permissions or network access. Ensure the instance IAM role has read/write access to the MLflow artifacts bucket and that security groups allow the necessary ports.

## Environment Cleanup

Remove all resources when the development environment is no longer needed:

```bash
terraform destroy
```

This command removes all AWS resources created by Terraform, including instances, networking, and storage. S3 buckets with versioning enabled may require manual deletion of object versions before Terraform can remove the bucket.

Verify resource removal through the AWS console to ensure no unexpected charges continue after environment destruction.

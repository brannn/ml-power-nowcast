# Custom AMI Building

This directory contains Packer configurations for building custom Amazon Machine Images (AMIs) optimized for ML Power Nowcast workloads. Custom AMIs reduce instance startup time and ensure consistent environments across deployments.

## AMI Contents

The custom AMI builds upon Ubuntu 22.04 LTS with comprehensive ML dependencies and system configurations. The base image includes Python 3.12, common ML libraries, NVIDIA drivers, and CUDA toolkit for GPU acceleration.

System-level components include Docker for containerized workloads, AWS CLI v2 for cloud integration, and AWS Systems Manager agent for secure remote access. The SSM agent configuration is critical for Ubuntu instances since it requires manual installation and service enablement.

ML dependencies include MLflow for experiment tracking, PyTorch for neural network development, XGBoost for gradient boosting, and supporting libraries like pandas, numpy, and scikit-learn. These packages are installed system-wide to avoid repeated installation on each instance launch.

NVIDIA components include the latest stable GPU drivers and CUDA toolkit 12.4 for L4 GPU support. The installation includes proper PATH and library path configuration for all users, ensuring GPU acceleration works immediately after instance launch.

## Build Process

Packer uses the amazon-ebs builder to create AMIs from base Ubuntu images. The build process launches a temporary EC2 instance, applies provisioning scripts, and creates an AMI snapshot before terminating the build instance.

The build requires AWS credentials with permissions to launch EC2 instances, create AMIs, and manage temporary security groups. The same credentials used for Terraform deployment typically provide sufficient permissions for Packer builds.

Build instances use g6f.xlarge instance types to match the target deployment environment. This ensures compatibility between build and runtime environments, particularly for GPU driver installation and testing.

## Building the AMI

Navigate to the ubuntu-ml-base directory and execute the Packer build:

```bash
cd packer/ubuntu-ml-base
packer build ubuntu-ml-base.pkr.hcl
```

The build process typically takes 20-30 minutes depending on package installation time and network performance. Packer displays progress information including provisioning script output and any errors encountered during the build.

Monitor the build output for errors, particularly during NVIDIA driver installation and Python package installation. These steps are most likely to fail due to network issues or package conflicts.

Upon successful completion, Packer outputs the AMI ID and region. Record this information for use in Terraform configurations. The AMI will be available in the us-west-2 region with appropriate tags for identification.

## Build Customization

The Packer configuration supports customization through variables defined at the top of the HCL file. Common modifications include instance types, regions, and project naming.

To build in a different region, modify the aws_region variable:

```bash
packer build -var 'aws_region=us-east-1' ubuntu-ml-base.pkr.hcl
```

Change the instance type for builds requiring different hardware:

```bash
packer build -var 'instance_type=g6.xlarge' ubuntu-ml-base.pkr.hcl
```

Modify the project name to create AMIs with different naming conventions:

```bash
packer build -var 'project_name=custom-ml-project' ubuntu-ml-base.pkr.hcl
```

## Package Management

The AMI includes specific versions of ML packages to ensure reproducibility. Package versions are selected for compatibility with Python 3.12 and CUDA 12.4. Updates to package versions should be tested thoroughly before production use.

PyTorch installation includes CPU and GPU support with CUDA 12.4 compatibility. The installation uses pip rather than conda to maintain consistency with the project's dependency management approach.

System packages use Ubuntu's package manager with automatic security updates enabled. The build process includes package cache cleanup to minimize AMI size and reduce storage costs.

## Security Configuration

The AMI includes security hardening appropriate for ML workloads. SSH access is disabled by default, with Systems Manager Session Manager providing secure remote access. This eliminates SSH key management and reduces attack surface.

User accounts follow Ubuntu defaults with the ubuntu user having sudo privileges. Additional security measures include automatic security updates and minimal package installation to reduce potential vulnerabilities.

Network configuration uses Ubuntu defaults suitable for VPC deployment. No additional firewall rules are configured at the AMI level, relying on AWS security groups for network access control.

## Testing and Validation

After AMI creation, test the image by launching a test instance and verifying all components function correctly. Key validation points include Python 3.12 availability, ML library imports, GPU detection, and Systems Manager connectivity.

Test GPU functionality by importing PyTorch and checking CUDA availability:

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA devices: {torch.cuda.device_count()}")
```

Verify Systems Manager connectivity by connecting to the test instance through Session Manager. This confirms that the SSM agent is properly installed and configured.

Test MLflow functionality by starting a local server and verifying web interface accessibility. This ensures all dependencies are correctly installed and configured.

## AMI Management

Custom AMIs incur storage costs based on the snapshot size. The ubuntu-ml-base AMI typically requires 15-20 GB of storage. Monitor AMI usage and deregister unused images to control costs.

AMI naming includes timestamps to distinguish between builds. Older AMIs can be safely deregistered after validating newer versions. Terraform configurations should be updated to reference new AMI IDs after validation.

Consider automating AMI builds through CI/CD pipelines for consistent updates. This ensures that security patches and dependency updates are applied regularly without manual intervention.

## Troubleshooting

Build failures commonly occur during package installation or GPU driver setup. Check the Packer output for specific error messages and retry with verbose logging if needed:

```bash
packer build -debug ubuntu-ml-base.pkr.hcl
```

Network connectivity issues may prevent package downloads or AWS API access. Ensure the build environment has reliable internet connectivity and appropriate AWS credentials.

GPU driver installation failures often relate to kernel compatibility or package conflicts. The build uses ubuntu-drivers autoinstall to select appropriate drivers automatically, but manual intervention may be required for specific hardware configurations.

Systems Manager agent issues typically involve service configuration or permissions. The build script enables the service automatically, but manual verification may be required if connectivity tests fail.

## Version Management

Track AMI versions through git tags and AMI tags for correlation between code and infrastructure versions. This enables rollback to previous AMI versions if issues are discovered after deployment.

Document significant changes in AMI contents, particularly package version updates or configuration modifications. This information assists with troubleshooting and change management processes.

Consider maintaining multiple AMI versions for different use cases, such as development versus production optimized images. Development AMIs might include additional debugging tools while production AMIs focus on minimal attack surface.

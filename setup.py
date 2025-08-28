#!/usr/bin/env python3.12
"""
Setup script for ML Power Nowcast project.
Creates virtual environment and installs dependencies.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    return result


def check_python_version():
    """Check if Python 3.12+ is available."""
    try:
        result = run_command("python3.12 --version", check=False)
        if result.returncode == 0:
            print(f"Found {result.stdout.strip()}")
            return "python3.12"
    except FileNotFoundError:
        pass
    
    # Fallback to python3
    try:
        result = run_command("python3 --version", check=False)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"Found {version}")
            # Check if it's 3.12+
            version_parts = version.split()[1].split('.')
            major, minor = int(version_parts[0]), int(version_parts[1])
            if major == 3 and minor >= 12:
                print("Python version is compatible")
                return "python3"
            else:
                print("Error: Python 3.12+ required")
                sys.exit(1)
    except FileNotFoundError:
        pass

    print("Error: Python 3.12+ not found. Please install Python 3.12 or later.")
    sys.exit(1)


def setup_virtual_environment(python_cmd):
    """Create and setup virtual environment."""
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print("Virtual environment already exists")
    else:
        print("Creating virtual environment...")
        run_command(f"{python_cmd} -m venv .venv")
        print("Virtual environment created")
    
    # Determine activation script path
    if os.name == 'nt':  # Windows
        pip_cmd = ".venv\\Scripts\\pip"
        python_venv = ".venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        pip_cmd = ".venv/bin/pip"
        python_venv = ".venv/bin/python"
    
    # Upgrade pip
    print("Upgrading pip...")
    run_command(f"{pip_cmd} install --upgrade pip")
    
    # Install requirements
    if Path("requirements.txt").exists():
        print("Installing requirements...")
        run_command(f"{pip_cmd} install -r requirements.txt")
        print("Requirements installed")
    else:
        print("Error: requirements.txt not found")
        sys.exit(1)
    
    return python_venv, pip_cmd


def setup_environment_file():
    """Setup environment file from example."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from .env.example...")
        env_file.write_text(env_example.read_text())
        print(".env file created")
        print("Please review and update .env with your specific configuration")
    elif env_file.exists():
        print(".env file already exists")
    else:
        print("Warning: No .env.example found to copy from")


def check_aws_cli():
    """Check if AWS CLI is available."""
    result = run_command("aws --version", check=False)
    if result.returncode == 0:
        print(f"AWS CLI found: {result.stdout.strip()}")
    else:
        print("Warning: AWS CLI not found. Install it for cloud deployment.")


def check_terraform():
    """Check if Terraform is available."""
    result = run_command("terraform version", check=False)
    if result.returncode == 0:
        version_line = result.stdout.split('\n')[0]
        print(f"Terraform found: {version_line}")
    else:
        print("Warning: Terraform not found. Install it for infrastructure deployment.")


def check_packer():
    """Check if Packer is available."""
    result = run_command("packer version", check=False)
    if result.returncode == 0:
        print(f"Packer found: {result.stdout.strip()}")
    else:
        print("Warning: Packer not found. Install it for custom AMI building.")


def main():
    """Main setup function."""
    print("Setting up ML Power Nowcast project...")
    print()

    # Check Python version
    python_cmd = check_python_version()

    # Setup virtual environment
    python_venv, pip_cmd = setup_virtual_environment(python_cmd)

    # Setup environment file
    setup_environment_file()

    # Check optional tools
    print("\nChecking optional tools:")
    check_aws_cli()
    check_terraform()
    check_packer()

    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. Activate virtual environment:")
    if os.name == 'nt':
        print("   .venv\\Scripts\\activate")
    else:
        print("   source .venv/bin/activate")
    print("2. Review and update .env file")
    print("3. Run 'make help' to see available commands")
    print("4. For infrastructure: cd terraform/environments/dev && terraform init")


if __name__ == "__main__":
    main()

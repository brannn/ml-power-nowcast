terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# VPC
resource "aws_vpc" "ml_dev" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = var.vpc_name
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "ml_dev" {
  vpc_id = aws_vpc.ml_dev.id

  tags = {
    Name        = "${var.vpc_name}-igw"
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.ml_dev.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.vpc_name}-public-${count.index + 1}"
    Environment = var.environment
    Project     = "ml-power-nowcast"
    Type        = "public"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.ml_dev.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "${var.vpc_name}-private-${count.index + 1}"
    Environment = var.environment
    Project     = "ml-power-nowcast"
    Type        = "private"
  }
}

# NAT Gateways
resource "aws_eip" "nat" {
  count = length(var.public_subnet_cidrs)

  domain = "vpc"
  depends_on = [aws_internet_gateway.ml_dev]

  tags = {
    Name        = "${var.vpc_name}-nat-eip-${count.index + 1}"
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }
}

resource "aws_nat_gateway" "ml_dev" {
  count = length(var.public_subnet_cidrs)

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name        = "${var.vpc_name}-nat-${count.index + 1}"
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }

  depends_on = [aws_internet_gateway.ml_dev]
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.ml_dev.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.ml_dev.id
  }

  tags = {
    Name        = "${var.vpc_name}-public-rt"
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }
}

resource "aws_route_table" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id = aws_vpc.ml_dev.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.ml_dev[count.index].id
  }

  tags = {
    Name        = "${var.vpc_name}-private-rt-${count.index + 1}"
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count = length(var.public_subnet_cidrs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(var.private_subnet_cidrs)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# SSM VPC Endpoints for private subnet access
resource "aws_vpc_endpoint" "ssm" {
  count = var.enable_ssm_endpoints ? 1 : 0

  vpc_id              = aws_vpc.ml_dev.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ssm"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.ssm_endpoints[0].id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.vpc_name}-ssm-endpoint"
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }
}

resource "aws_vpc_endpoint" "ssmmessages" {
  count = var.enable_ssm_endpoints ? 1 : 0

  vpc_id              = aws_vpc.ml_dev.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ssmmessages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.ssm_endpoints[0].id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.vpc_name}-ssmmessages-endpoint"
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }
}

resource "aws_vpc_endpoint" "ec2messages" {
  count = var.enable_ssm_endpoints ? 1 : 0

  vpc_id              = aws_vpc.ml_dev.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ec2messages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.ssm_endpoints[0].id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.vpc_name}-ec2messages-endpoint"
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }
}

# Security group for SSM endpoints
resource "aws_security_group" "ssm_endpoints" {
  count = var.enable_ssm_endpoints ? 1 : 0

  name_prefix = "${var.vpc_name}-ssm-endpoints-"
  vpc_id      = aws_vpc.ml_dev.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.vpc_name}-ssm-endpoints-sg"
    Environment = var.environment
    Project     = "ml-power-nowcast"
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_region" "current" {}

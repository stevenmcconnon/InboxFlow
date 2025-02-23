############################################
# File: inboxflow-infrastructure/main.tf
############################################

# --- Add a VPC resource for LocalStack ---
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "localstack-vpc"
  }
}

provider "aws" {
  region                      = var.aws_region
  access_key                  = var.aws_access_key
  secret_key                  = var.aws_secret_key
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    lambda         = var.lambda_endpoint != "" ? var.lambda_endpoint : "http://127.0.0.1:4566"
    s3             = var.s3_endpoint != "" ? var.s3_endpoint : "http://127.0.0.1:4566"
    apigateway     = var.apigateway_endpoint != "" ? var.apigateway_endpoint : "http://127.0.0.1:4566"
    sns            = "http://127.0.0.1:4566"
    sqs            = "http://127.0.0.1:4566"
    rds            = "http://127.0.0.1:4566"
    iam            = "http://127.0.0.1:4566"
    secretsmanager = "http://127.0.0.1:4566"
    ec2            = "http://127.0.0.1:4566"  # Ensure EC2 calls go to LocalStack
  }
}

# Note: Ensure that your .env file sets AWS_S3_FORCE_PATH_STYLE=true for LocalStack testing.

# ---------------------------------------------------------------------
# S3 Bucket for Frontend Hosting (exposed to Internet)
# ---------------------------------------------------------------------
resource "aws_s3_bucket" "frontend" {
  # Use a bucket name without hyphens to avoid DNS resolution issues with LocalStack.
  bucket = "inboxflowfrontenddev"
  acl    = "public-read"

  dynamic "website" {
    for_each = var.use_website_configuration ? [1] : []
    content {
      index_document = "index.html"
    }
  }
}

# ---------------------------------------------------------------------
# API Gateway for internal communication (if needed)
# ---------------------------------------------------------------------
resource "aws_api_gateway_rest_api" "api" {
  name        = "InboxFlowAPI"
  description = "API for InboxFlow backend services."
}

# ---------------------------------------------------------------------
# SNS Topic
# ---------------------------------------------------------------------
resource "aws_sns_topic" "inboxflow_sns" {
  name = "InboxFlow-SNS"
}

# ---------------------------------------------------------------------
# SQS Queue
# ---------------------------------------------------------------------
resource "aws_sqs_queue" "inboxflow_sqs" {
  name                      = "InboxFlow-SQS"
  message_retention_seconds = 86400
}

# ---------------------------------------------------------------------
# Aurora Serverless (PostgreSQL)
# ---------------------------------------------------------------------
resource "aws_rds_cluster" "aurora" {
  count               = var.deploy_rds ? 1 : 0
  cluster_identifier  = "inboxflow-db-cluster"
  engine              = "aurora-postgresql"
  engine_mode         = "serverless"
  database_name       = "inboxflow"
  master_username     = var.db_username
  master_password     = var.db_password
  skip_final_snapshot = true
}

# ---------------------------------------------------------------------
# IAM Role for Lambda Function
# ---------------------------------------------------------------------
resource "aws_iam_role" "imap_sync_lambda_role" {
  name = "imap_sync_lambda_role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# IAM Policy Attachments for Lambda: Basic execution, VPC access, Secrets Manager access, etc.
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.imap_sync_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.imap_sync_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "secretsmanager_access" {
  role       = aws_iam_role.imap_sync_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

# ---------------------------------------------------------------------
# Secrets Manager: Store sensitive values (DB_URL, EMAIL_SERVER, etc.)
# ---------------------------------------------------------------------
resource "aws_secretsmanager_secret" "imap_sync_secrets" {
  name = "imap_sync_secrets"
}

resource "aws_secretsmanager_secret_version" "imap_sync_secrets_version" {
  secret_id     = aws_secretsmanager_secret.imap_sync_secrets.id
  secret_string = jsonencode({
    DB_URL         = var.db_url,
    EMAIL_SERVER   = var.email_server,
    EMAIL_USER     = var.email_user,
    EMAIL_PASSWORD = var.email_password
  })
}

# ---------------------------------------------------------------------
# Security Group for Lambda: Allow all outbound traffic
# ---------------------------------------------------------------------
resource "aws_security_group" "lambda_sg" {
  name        = "inboxflow-lambda-sg"
  description = "Security group for the Lambda function, allowing all outbound traffic"
  vpc_id      = aws_vpc.main.id

  # Outbound rule: allow all traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------------------------------------------------------------------
# Additional Resources for Internet Access
# ---------------------------------------------------------------------

# 1) Internet Gateway
resource "aws_internet_gateway" "main_igw" {
  vpc_id = aws_vpc.main.id
}

# 2) Public Subnet (for NAT Gateway)
resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"      # <-- Adjust as needed
  availability_zone       = "us-east-1a"       # <-- Adjust as needed
  map_public_ip_on_launch = true
}

# 3) Public Route Table
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main_igw.id
  }
}

# 4) Associate Public Route Table with Public Subnet
resource "aws_route_table_association" "public_subnet_assoc" {
  subnet_id      = aws_subnet.public_subnet_1.id
  route_table_id = aws_route_table.public_rt.id
}

# 5) Elastic IP for NAT Gateway
resource "aws_eip" "nat_eip" {
  vpc = true
}

# 6) NAT Gateway
resource "aws_nat_gateway" "main_nat_gw" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet_1.id
}

# 7) Private Subnet (where Lambda runs, routes to NAT)
resource "aws_subnet" "private_subnet_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"      # <-- Adjust as needed
  availability_zone       = "us-east-1a"       # <-- Adjust as needed
  map_public_ip_on_launch = false
}

# 8) Private Route Table (routes 0.0.0.0/0 to NAT Gateway)
resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main_nat_gw.id
  }
}

# 9) Associate Private Route Table with Private Subnet
resource "aws_route_table_association" "private_subnet_assoc" {
  subnet_id      = aws_subnet.private_subnet_1.id
  route_table_id = aws_route_table.private_rt.id
}

# ---------------------------------------------------------------------
# Lambda Function for IMAP Sync
# ---------------------------------------------------------------------
resource "aws_lambda_function" "imap_sync_lambda" {
  function_name = "inboxflow-imap-sync"
  role          = aws_iam_role.imap_sync_lambda_role.arn
  handler       = "imap_sync.lambda_handler"
  runtime       = "python3.9"
  timeout       = var.lambda_timeout

  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(abspath("${path.module}/${var.lambda_zip_path}"))

  environment {
    variables = {
      DB_URL         = var.db_url
      EMAIL_SERVER   = var.email_server
      EMAIL_USER     = var.email_user
      EMAIL_PASSWORD = var.email_password
      BATCH_SIZE     = var.batch_size
    }
  }

  # Updated VPC config: use the dedicated security group and the private subnet
  vpc_config {
    subnet_ids         = var.lambda_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}
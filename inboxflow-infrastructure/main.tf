############################################
# File: inboxflow-infrastructure/main.tf
############################################

resource "aws_vpc" "main" {
  count                = var.local_dev ? 0 : 1
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "production-vpc"
  }
}

provider "aws" {
  region     = var.aws_region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
  skip_credentials_validation = var.local_dev
  skip_metadata_api_check     = var.local_dev
  skip_requesting_account_id  = var.local_dev
}

resource "aws_s3_bucket" "frontend" {
  count  = var.local_dev ? 0 : 1
  bucket = "inboxflowfrontenddev"
  acl    = "public-read"

  dynamic "website" {
    for_each = var.use_website_configuration ? [1] : []
    content {
      index_document = "index.html"
    }
  }
}

resource "aws_api_gateway_rest_api" "api" {
  count       = var.local_dev ? 0 : 1
  name        = "InboxFlowAPI"
  description = "API for InboxFlow backend services."
}

resource "aws_sns_topic" "inboxflow_sns" {
  count = var.local_dev ? 0 : 1
  name  = "InboxFlow-SNS"
}

resource "aws_sqs_queue" "inboxflow_sqs" {
  count                     = var.local_dev ? 0 : 1
  name                      = "InboxFlow-SQS"
  message_retention_seconds = 86400
}

resource "aws_rds_cluster" "aurora" {
  count              = (var.deploy_rds && !var.local_dev) ? 1 : 0
  cluster_identifier = "inboxflow-db-cluster"
  engine             = "aurora-postgresql"
  engine_mode        = "serverless"
  database_name      = "inboxflow"
  master_username    = var.db_username
  master_password    = var.db_password
  skip_final_snapshot = true
}

resource "aws_iam_role" "imap_sync_lambda_role" {
  count = var.local_dev ? 0 : 1
  name  = "imap_sync_lambda_role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  count      = var.local_dev ? 0 : 1
  role       = aws_iam_role.imap_sync_lambda_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  count      = var.local_dev ? 0 : 1
  role       = aws_iam_role.imap_sync_lambda_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "secretsmanager_access" {
  count      = var.local_dev ? 0 : 1
  role       = aws_iam_role.imap_sync_lambda_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
}

resource "aws_secretsmanager_secret" "imap_sync_secrets" {
  count = var.local_dev ? 0 : 1
  name  = "imap_sync_secrets"
}

resource "aws_secretsmanager_secret_version" "imap_sync_secrets_version" {
  count         = var.local_dev ? 0 : 1
  secret_id     = aws_secretsmanager_secret.imap_sync_secrets[0].id
  secret_string = jsonencode({
    DB_URL         = var.db_url,
    EMAIL_SERVER   = var.email_server,
    EMAIL_USER     = var.email_user,
    EMAIL_PASSWORD = var.email_password
  })
}

resource "aws_security_group" "lambda_sg" {
  count       = var.local_dev ? 0 : 1
  name        = "inboxflow-lambda-sg"
  description = "Security group for the Lambda function, allowing all outbound traffic"
  vpc_id      = aws_vpc.main[0].id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_internet_gateway" "main_igw" {
  count  = var.local_dev ? 0 : 1
  vpc_id = aws_vpc.main[0].id
}

resource "aws_subnet" "public_subnet_1" {
  count               = var.local_dev ? 0 : 1
  vpc_id              = aws_vpc.main[0].id
  cidr_block          = "10.0.1.0/24"
  availability_zone   = "us-east-1a"
  map_public_ip_on_launch = true
}

resource "aws_route_table" "public_rt" {
  count  = var.local_dev ? 0 : 1
  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main_igw[0].id
  }
}

resource "aws_route_table_association" "public_subnet_assoc" {
  count          = var.local_dev ? 0 : 1
  subnet_id      = aws_subnet.public_subnet_1[0].id
  route_table_id = aws_route_table.public_rt[0].id
}

resource "aws_eip" "nat_eip" {
  count = var.local_dev ? 0 : 1
  vpc   = true
}

resource "aws_nat_gateway" "main_nat_gw" {
  count         = var.local_dev ? 0 : 1
  allocation_id = aws_eip.nat_eip[0].id
  subnet_id     = aws_subnet.public_subnet_1[0].id
}

resource "aws_subnet" "private_subnet_1" {
  count               = var.local_dev ? 0 : 1
  vpc_id              = aws_vpc.main[0].id
  cidr_block          = "10.0.2.0/24"
  availability_zone   = "us-east-1a"
  map_public_ip_on_launch = false
}

resource "aws_route_table" "private_rt" {
  count  = var.local_dev ? 0 : 1
  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main_nat_gw[0].id
  }
}

resource "aws_route_table_association" "private_subnet_assoc" {
  count          = var.local_dev ? 0 : 1
  subnet_id      = aws_subnet.private_subnet_1[0].id
  route_table_id = aws_route_table.private_rt[0].id
}

resource "aws_lambda_function" "imap_sync_lambda" {
  count = var.local_dev ? 0 : 1
  function_name = "inboxflow-imap-sync"
  role          = aws_iam_role.imap_sync_lambda_role[0].arn
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

  vpc_config {
    subnet_ids         = var.lambda_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg[0].id]
  }
}
# File: inboxflow-infrastructure/variables.tf

variable "aws_region" {
  description = "AWS region to deploy resources"
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS access key"
  type        = string
  default     = "dummy"
}

variable "aws_secret_key" {
  description = "AWS secret key"
  type        = string
  default     = "dummy"
}

variable "db_username" {
  description = "Database admin username"
  default     = "admin"
}

variable "db_password" {
  description = "Database admin password"
  type        = string
  default     = "pass"
}

variable "db_url" {
  description = "Database connection URL"
  type        = string
  default     = "postgresql://user:pass@inboxflow-postgres:5432/inboxflow"
}

variable "email_server" {
  description = "IMAP email server"
  type        = string
  default     = "imap.mail.yahoo.com"
}

variable "email_user" {
  description = "Email user for IMAP login"
  type        = string
  default     = "you@example.com"
}

variable "email_password" {
  description = "Email password for IMAP login"
  type        = string
  default     = "REDACTED_APP_PASSWORD"
}

variable "lambda_zip_path" {
  description = "Path to your zipped Lambda function code"
  type        = string
  default     = "lambda_package.zip"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  default     = 900
}

variable "batch_size" {
  description = "Batch size for processing emails in Lambda"
  default     = 1000
}

# New variable to control local development behavior
variable "local_dev" {
  description = "Set to true for local development (skips AWS resource creation and credential validation)"
  type        = bool
  default     = true
}

# LocalStack endpoint variables are no longer used; leave them blank.
variable "lambda_endpoint" {
  description = "Custom endpoint for Lambda (not used with SAM CLI)"
  default     = ""
}

variable "s3_endpoint" {
  description = "Custom endpoint for S3 (not used with SAM CLI)"
  default     = ""
}

variable "apigateway_endpoint" {
  description = "Custom endpoint for API Gateway (not used with SAM CLI)"
  default     = ""
}

# VPC configuration for Lambda (if required in production)
variable "lambda_subnet_ids" {
  description = "List of subnet IDs for the Lambda function"
  type        = list(string)
  default     = []
}

variable "lambda_security_group_ids" {
  description = "List of security group IDs for the Lambda function"
  type        = list(string)
  default     = []
}

# ECS Variables for deploying additional Dockerized services (production)
variable "ecs_subnet_ids" {
  description = "List of subnet IDs for ECS services"
  type        = list(string)
  default     = []
}

variable "ecs_security_group_ids" {
  description = "List of security group IDs for ECS services"
  type        = list(string)
  default     = []
}

variable "deploy_ecs" {
  description = "Deploy ECS resources? Set to true for production, false for local testing."
  type        = bool
  default     = false
}

variable "deploy_rds" {
  description = "Deploy RDS resources? Set to true for production, false for local testing."
  type        = bool
  default     = false
}

variable "use_website_configuration" {
  description = "Enable website configuration for S3 bucket. Set to true for production, false for local testing."
  type        = bool
  default     = false
}
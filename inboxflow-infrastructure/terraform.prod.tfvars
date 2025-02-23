# File: inboxflow-infrastructure/terraform.prod.tfvars

lambda_zip_path = "lambda_package.zip"

aws_access_key  = "YOUR_PRODUCTION_ACCESS_KEY"
aws_secret_key  = "YOUR_PRODUCTION_SECRET_KEY"
aws_region      = "us-east-1"

# Set local_dev to false for production deployment
local_dev = false

# Enable ECS and RDS resources for production
deploy_ecs = true
deploy_rds = true

# Enable S3 website configuration if desired
use_website_configuration = true

# Production Database connection URL (update with your production DB endpoint)
db_url = "postgresql://admin:pass@your-prod-db-endpoint:5432/inboxflow"

# Production IMAP settings (update as needed)
email_server  = "imap.mail.yahoo.com"
email_user    = "your-production-email@example.com"
email_password = "your-production-email-app-password"
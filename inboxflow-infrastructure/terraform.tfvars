# File: inboxflow-infrastructure/terraform.tfvars

lambda_zip_path = "lambda_package.zip"
aws_access_key  = "dummy"
aws_secret_key  = "dummy"
aws_region      = "us-west-1"
local_dev       = true
deploy_ecs      = false
deploy_rds      = false
use_website_configuration = false

# IMPORTANT: update the DB URL for local development inside Docker:
db_url         = "postgresql://user:pass@host.docker.internal:5432/inboxflow"
email_server   = "imap.mail.yahoo.com"
email_user     = "you@example.com"
email_password = "dummy"
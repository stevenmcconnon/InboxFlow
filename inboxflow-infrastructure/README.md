# InboxFlow Infrastructure

Terraform configuration for provisioning AWS infrastructure.

## Setup

1. Initialize Terraform:
   ```
   terraform init
   ```
2. Plan changes:
   ```
   terraform plan
   ```
3. Apply changes:
   ```
   terraform apply
   ```



# InboxFlow Infrastructure

This Terraform module defines AWS resources for the InboxFlow platform, including:

- An IAM Role for Lambda functions.
- A Lambda function for IMAP synchronization.
- An API Gateway for the API service (example).

## Setup

1. **Configure Variables:**
   Update the `.env` file or create a `terraform.tfvars` file with your AWS credentials, email settings, Lambda zip path, and DB URL.

2. **Initialize Terraform:**
   ```bash
   cd inboxflow-infrastructure
   terraform init
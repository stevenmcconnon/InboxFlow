output "frontend_s3_url" {
  description = "Frontend S3 bucket URL (website or bucket domain)"
  value       = var.use_website_configuration ? aws_s3_bucket.frontend.website_endpoint : aws_s3_bucket.frontend.bucket_domain_name
}

output "api_gateway_id" {
  description = "ID of the API Gateway for InboxFlow API"
  value       = aws_api_gateway_rest_api.api.id
}

output "sqs_queue_url" {
  description = "URL of the SQS queue"
  value       = aws_sqs_queue.inboxflow_sqs.url
}

output "aurora_endpoint" {
  description = "Endpoint of the Aurora RDS cluster (if deployed)"
  value       = var.deploy_rds ? aws_rds_cluster.aurora[0].endpoint : ""
}

output "imap_sync_lambda_arn" {
  description = "ARN of the IMAP Sync Lambda function"
  value       = aws_lambda_function.imap_sync_lambda.arn
}
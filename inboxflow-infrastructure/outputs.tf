output "frontend_s3_url" {
  description = "Frontend S3 bucket URL (website or bucket domain)"
  value       = length(aws_s3_bucket.frontend) > 0 ? (var.use_website_configuration ? aws_s3_bucket.frontend[0].website_endpoint : aws_s3_bucket.frontend[0].bucket_domain_name) : ""
}

output "api_gateway_id" {
  description = "ID of the API Gateway for InboxFlow API"
  value       = length(aws_api_gateway_rest_api.api) > 0 ? aws_api_gateway_rest_api.api[0].id : ""
}

output "sqs_queue_url" {
  description = "URL of the SQS queue"
  value       = length(aws_sqs_queue.inboxflow_sqs) > 0 ? aws_sqs_queue.inboxflow_sqs[0].url : ""
}

output "imap_sync_lambda_arn" {
  description = "ARN of the IMAP Sync Lambda function"
  value       = length(aws_lambda_function.imap_sync_lambda) > 0 ? aws_lambda_function.imap_sync_lambda[0].arn : ""
}
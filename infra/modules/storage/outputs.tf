output "bucket_names" {
  description = "Standard S3 bucket names."
  value       = { for key, bucket in aws_s3_bucket.this : key => bucket.bucket }
}

output "bucket_arns" {
  description = "Standard S3 bucket ARNs."
  value       = { for key, bucket in aws_s3_bucket.this : key => bucket.arn }
}

output "bucket_roots" {
  description = "Root URIs for ETL-facing S3 zones."
  value       = { for key, bucket in aws_s3_bucket.this : key => "s3://${bucket.bucket}" }
}

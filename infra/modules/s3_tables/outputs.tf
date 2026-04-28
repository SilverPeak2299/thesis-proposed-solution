output "table_bucket_name" {
  description = "Name of the S3 Tables bucket used for gold datasets."
  value       = aws_s3tables_table_bucket.this.name
}

output "table_bucket_arn" {
  description = "ARN of the S3 Tables bucket."
  value       = aws_s3tables_table_bucket.this.arn
}

output "namespace" {
  description = "Default S3 Tables namespace."
  value       = aws_s3tables_namespace.this.namespace
}

output "glue_catalog_id" {
  description = "Glue federated catalog identifier convention for the S3 Tables bucket."
  value       = "${var.account_id}:s3tablescatalog/${aws_s3tables_table_bucket.this.name}"
}

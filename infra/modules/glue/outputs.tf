output "job_role_arn" {
  description = "Glue job execution role ARN."
  value       = aws_iam_role.job.arn
}

output "crawler_role_arn" {
  description = "Glue crawler execution role ARN."
  value       = aws_iam_role.crawler.arn
}

output "catalog_databases" {
  description = "Standard Glue catalog databases created by this module."
  value       = { for key, db in aws_glue_catalog_database.this : key => db.name }
}

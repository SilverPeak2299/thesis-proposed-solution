output "log_group_names" {
  description = "Named CloudWatch log groups by service."
  value       = { for key, group in aws_cloudwatch_log_group.this : key => group.name }
}

output "log_group_arns" {
  description = "CloudWatch log group ARNs by service."
  value       = { for key, group in aws_cloudwatch_log_group.this : key => group.arn }
}

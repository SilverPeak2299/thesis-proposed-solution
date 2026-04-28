output "environment_name" {
  description = "MWAA environment name."
  value       = aws_mwaa_environment.this.name
}

output "environment_arn" {
  description = "MWAA environment ARN."
  value       = aws_mwaa_environment.this.arn
}

output "execution_role_arn" {
  description = "Execution role ARN for MWAA."
  value       = aws_iam_role.execution.arn
}

output "security_group_id" {
  description = "Security group attached to the MWAA environment."
  value       = aws_security_group.this.id
}

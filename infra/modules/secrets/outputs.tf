output "secret_arns" {
  description = "ARNs for the placeholder secrets."
  value       = { for key, secret in aws_secretsmanager_secret.this : key => secret.arn }
}

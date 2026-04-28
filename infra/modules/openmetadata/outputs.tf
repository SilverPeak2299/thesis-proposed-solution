output "instance_id" {
  description = "OpenMetadata instance ID."
  value       = aws_instance.this.id
}

output "instance_arn" {
  description = "OpenMetadata instance ARN."
  value       = aws_instance.this.arn
}

output "public_dns" {
  description = "Public DNS of the OpenMetadata host."
  value       = aws_instance.this.public_dns
}

output "security_group_id" {
  description = "Security group attached to the OpenMetadata host."
  value       = aws_security_group.this.id
}

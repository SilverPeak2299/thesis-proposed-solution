variable "name_prefix" {
  description = "Prefix used in log group names."
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention period."
  type        = number
}

variable "tags" {
  description = "Tags applied to observability resources."
  type        = map(string)
  default     = {}
}

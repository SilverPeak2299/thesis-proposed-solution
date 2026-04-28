variable "project_name" {
  description = "Project identifier used in generated bucket names."
  type        = string
}

variable "environment_name" {
  description = "Environment identifier used in generated bucket names."
  type        = string
}

variable "account_id" {
  description = "AWS account ID to help keep generated bucket names unique."
  type        = string
}

variable "bucket_overrides" {
  description = "Optional explicit names for raw, curated, manifests, and mwaa_artifacts buckets."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags applied to storage resources."
  type        = map(string)
  default     = {}
}

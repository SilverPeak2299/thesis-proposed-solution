variable "name_prefix" {
  description = "Prefix used in Glue IAM role names."
  type        = string
}

variable "raw_bucket_arn" {
  description = "ARN of the raw bucket."
  type        = string
}

variable "curated_bucket_arn" {
  description = "ARN of the curated bucket."
  type        = string
}

variable "manifests_bucket_arn" {
  description = "ARN of the manifests bucket."
  type        = string
}

variable "s3tables_bucket_arn" {
  description = "ARN of the S3 Tables bucket used for gold datasets."
  type        = string
}

variable "standard_catalog_prefix" {
  description = "Prefix used when naming standard Glue catalog databases."
  type        = string
}

variable "log_group_arn" {
  description = "CloudWatch log group ARN for Glue jobs."
  type        = string
}

variable "secret_arns" {
  description = "Secret ARNs accessible to Glue runtime roles."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags applied to Glue resources."
  type        = map(string)
  default     = {}
}

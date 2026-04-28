variable "project_name" {
  description = "Project identifier used in the derived table bucket name."
  type        = string
}

variable "environment_name" {
  description = "Environment identifier used in the derived table bucket name."
  type        = string
}

variable "account_id" {
  description = "AWS account ID to help keep the table bucket name unique."
  type        = string
}

variable "table_bucket_name" {
  description = "Optional explicit S3 Tables bucket name."
  type        = string
  default     = null
}

variable "namespace" {
  description = "Default namespace created inside the S3 Tables bucket."
  type        = string
}

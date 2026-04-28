variable "name_prefix" {
  description = "Prefix used in MWAA resource names."
  type        = string
}

variable "vpc_id" {
  description = "VPC identifier for the MWAA environment."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnets attached to the MWAA environment."
  type        = list(string)
}

variable "mwaa_bucket_arn" {
  description = "S3 bucket ARN used for MWAA DAGs and dependencies."
  type        = string
}

variable "mwaa_bucket_name" {
  description = "S3 bucket name used for MWAA DAGs and dependencies."
  type        = string
}

variable "data_bucket_arns" {
  description = "Additional S3 bucket ARNs MWAA may orchestrate around."
  type        = list(string)
  default     = []
}

variable "secret_arns" {
  description = "Secrets ARNs readable by the MWAA execution role."
  type        = list(string)
  default     = []
}

variable "webserver_access_mode" {
  description = "MWAA webserver access mode."
  type        = string
}

variable "environment_class" {
  description = "MWAA environment class."
  type        = string
}

variable "min_workers" {
  description = "Minimum number of MWAA workers."
  type        = number
}

variable "max_workers" {
  description = "Maximum number of MWAA workers."
  type        = number
}

variable "schedulers" {
  description = "Number of MWAA schedulers."
  type        = number
}

variable "dag_s3_path" {
  description = "S3 prefix where DAG bundles are stored."
  type        = string
}

variable "plugins_s3_path" {
  description = "Optional S3 key for MWAA plugins zip."
  type        = string
  default     = null
}

variable "requirements_s3_path" {
  description = "Optional S3 key for MWAA requirements file."
  type        = string
  default     = null
}

variable "startup_script_s3_path" {
  description = "Optional S3 key for MWAA startup script."
  type        = string
  default     = null
}

variable "airflow_configuration" {
  description = "Airflow configuration options for the MWAA environment."
  type        = map(string)
  default     = {}
}

variable "source_cidr_for_webserver" {
  description = "Unused placeholder for future MWAA ingress tightening."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to MWAA resources."
  type        = map(string)
  default     = {}
}

variable "aws_region" {
  description = "AWS region for the dev environment."
  type        = string
}

variable "aws_profile" {
  description = "AWS shared config/credentials profile used by the dev environment."
  type        = string
  default     = null
}

variable "project_name" {
  description = "Short project identifier used in names and tags."
  type        = string
  default     = "thesis-proposed-solution"
}

variable "environment_name" {
  description = "Environment identifier."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Two public subnet CIDR blocks used by the OpenMetadata host and NAT gateway."
  type        = list(string)
  default     = ["10.42.0.0/24", "10.42.1.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Exactly two public subnet CIDRs are required."
  }
}

variable "private_subnet_cidrs" {
  description = "Two private subnet CIDR blocks used by MWAA."
  type        = list(string)
  default     = ["10.42.10.0/24", "10.42.11.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Exactly two private subnet CIDRs are required."
  }
}

variable "availability_zones" {
  description = "Optional explicit availability zones for the two public and two private subnets."
  type        = list(string)
  default     = null

  validation {
    condition     = var.availability_zones == null || length(var.availability_zones) == 2
    error_message = "Set exactly two availability zones or leave the value null."
  }
}

variable "bucket_overrides" {
  description = "Optional explicit names for standard S3 buckets keyed by raw, curated, manifests, and mwaa_artifacts."
  type        = map(string)
  default     = {}
}

variable "secret_names" {
  description = "Secrets Manager placeholders used by platform services and later runtime assets."
  type        = set(string)
  default = [
    "openmetadata/admin",
    "openmetadata/database",
    "runtime/source",
  ]
}

variable "log_retention_days" {
  description = "Retention period for CloudWatch log groups."
  type        = number
  default     = 30
}

variable "gold_table_bucket_name" {
  description = "Optional explicit name for the S3 Tables table bucket. Leave null to derive one."
  type        = string
  default     = null
}

variable "gold_namespace" {
  description = "Default S3 Tables namespace for governed gold datasets."
  type        = string
  default     = "gold"
}

variable "glue_catalog_prefix" {
  description = "Prefix used when naming standard Glue catalog databases for raw and curated zones."
  type        = string
  default     = "thesis"
}

variable "enable_mwaa" {
  description = "Whether to provision the MWAA environment in dev. Disable this for local Docker-based Airflow development."
  type        = bool
  default     = false
}

variable "mwaa_webserver_access_mode" {
  description = "Webserver access mode for the MWAA environment."
  type        = string
  default     = "PUBLIC_ONLY"
}

variable "mwaa_environment_class" {
  description = "MWAA environment class."
  type        = string
  default     = "mw1.small"
}

variable "mwaa_min_workers" {
  description = "Minimum number of MWAA workers."
  type        = number
  default     = 1
}

variable "mwaa_max_workers" {
  description = "Maximum number of MWAA workers."
  type        = number
  default     = 2
}

variable "mwaa_schedulers" {
  description = "Number of MWAA schedulers."
  type        = number
  default     = 2
}

variable "mwaa_dag_s3_path" {
  description = "S3 prefix inside the MWAA artifact bucket where DAG bundles will be uploaded later."
  type        = string
  default     = "dags"
}

variable "mwaa_plugins_s3_path" {
  description = "S3 key for future MWAA plugins zip."
  type        = string
  default     = null
}

variable "mwaa_requirements_s3_path" {
  description = "S3 key for future MWAA requirements.txt."
  type        = string
  default     = null
}

variable "mwaa_startup_script_s3_path" {
  description = "S3 key for an optional future MWAA startup script."
  type        = string
  default     = null
}

variable "mwaa_airflow_configuration" {
  description = "Additional Airflow configuration options passed to the MWAA environment."
  type        = map(string)
  default = {
    "core.load_examples" = "False"
  }
}

variable "openmetadata_admin_ingress_cidrs" {
  description = "CIDR ranges allowed to reach the OpenMetadata UI and optional SSH."
  type        = list(string)
  default     = []
}

variable "openmetadata_instance_type" {
  description = "EC2 instance type for the OpenMetadata host."
  type        = string
  default     = "t3.small"
}

variable "openmetadata_ami_id" {
  description = "Optional explicit EC2 AMI ID for the OpenMetadata host. Leave null to resolve from SSM."
  type        = string
  default     = null
}

variable "openmetadata_ssh_key_name" {
  description = "Optional EC2 key pair name for emergency access."
  type        = string
  default     = null
}

variable "openmetadata_allow_ssh" {
  description = "Whether to expose SSH to the admin ingress CIDRs."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags applied to all supported resources."
  type        = map(string)
  default     = {}
}

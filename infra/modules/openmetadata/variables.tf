variable "name_prefix" {
  description = "Prefix used in OpenMetadata resource names."
  type        = string
}

variable "vpc_id" {
  description = "VPC identifier for the OpenMetadata host."
  type        = string
}

variable "public_subnet_id" {
  description = "Public subnet where the OpenMetadata EC2 host is launched."
  type        = string
}

variable "admin_ingress_cidrs" {
  description = "CIDR ranges allowed to reach the OpenMetadata UI."
  type        = list(string)
  default     = []
}

variable "instance_type" {
  description = "EC2 instance type for the OpenMetadata host."
  type        = string
}

variable "ami_id" {
  description = "Optional explicit AMI ID for the OpenMetadata host."
  type        = string
  default     = null
}

variable "ssh_key_name" {
  description = "Optional EC2 key pair for SSH access."
  type        = string
  default     = null
}

variable "allow_ssh" {
  description = "Whether to expose SSH from the admin ingress ranges."
  type        = bool
  default     = false
}

variable "secret_arns" {
  description = "Secret ARNs readable by the OpenMetadata host."
  type        = list(string)
  default     = []
}

variable "log_group_name" {
  description = "Reserved for future CloudWatch agent configuration."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to OpenMetadata resources."
  type        = map(string)
  default     = {}
}

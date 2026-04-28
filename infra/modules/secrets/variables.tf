variable "name_prefix" {
  description = "Prefix applied to all placeholder secret names."
  type        = string
}

variable "secret_names" {
  description = "Relative secret names to create."
  type        = set(string)
}

variable "tags" {
  description = "Tags applied to secrets."
  type        = map(string)
  default     = {}
}

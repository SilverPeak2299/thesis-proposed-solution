output "raw_root" {
  description = "ETL-facing raw zone root."
  value       = module.storage.bucket_roots["raw"]
}

output "curated_root" {
  description = "ETL-facing curated zone root."
  value       = module.storage.bucket_roots["curated"]
}

output "manifest_root" {
  description = "ETL-facing run and release manifest root."
  value       = module.storage.bucket_roots["manifests"]
}

output "mwaa_bucket_name" {
  description = "Bucket used later for DAG bundles and MWAA dependencies."
  value       = module.storage.bucket_names["mwaa_artifacts"]
}

output "mwaa_environment_name" {
  description = "Provisioned MWAA environment name when enable_mwaa is true."
  value       = var.enable_mwaa ? module.mwaa[0].environment_name : null
}

output "mwaa_execution_role_arn" {
  description = "Execution role used by the MWAA environment when enable_mwaa is true."
  value       = var.enable_mwaa ? module.mwaa[0].execution_role_arn : null
}

output "glue_job_role_arn" {
  description = "Execution role intended for future Glue jobs."
  value       = module.glue.job_role_arn
}

output "glue_crawler_role_arn" {
  description = "Execution role intended for future Glue crawlers."
  value       = module.glue.crawler_role_arn
}

output "glue_catalog_databases" {
  description = "Standard Glue catalog databases for raw and curated assets."
  value       = module.glue.catalog_databases
}

output "gold_table_bucket_name" {
  description = "S3 Tables table bucket used for the managed Iceberg gold layer."
  value       = module.s3_tables.table_bucket_name
}

output "gold_table_bucket_arn" {
  description = "ARN of the S3 Tables table bucket."
  value       = module.s3_tables.table_bucket_arn
}

output "gold_namespace" {
  description = "Default S3 Tables namespace for governed gold datasets."
  value       = module.s3_tables.namespace
}

output "gold_glue_catalog_id" {
  description = "Glue federated catalog identifier convention for the S3 Tables bucket."
  value       = module.s3_tables.glue_catalog_id
}

output "openmetadata_instance_id" {
  description = "OpenMetadata EC2 instance identifier."
  value       = module.openmetadata.instance_id
}

output "openmetadata_public_dns" {
  description = "Public DNS name of the OpenMetadata EC2 host, if assigned."
  value       = module.openmetadata.public_dns
}

output "secret_arns" {
  description = "Secrets Manager placeholders created for this environment."
  value       = module.secrets.secret_arns
}

output "log_group_names" {
  description = "CloudWatch log groups created by the observability module."
  value       = module.observability.log_group_names
}

output "terraform_state_reference" {
  description = "Placeholder state reference used until a remote backend is introduced."
  value       = "local-state:infra/envs/dev"
}

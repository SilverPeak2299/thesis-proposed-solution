data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  common_tags = merge(
    var.tags,
    {
      Project     = var.project_name
      Environment = var.environment_name
      ManagedBy   = "terraform"
      ThesisScope = "control-plane-first"
    }
  )

  name_prefix = "${var.project_name}-${var.environment_name}"
}

module "network" {
  source = "../../modules/network"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  availability_zones   = slice(data.aws_availability_zones.available.names, 0, 2)
  tags                 = local.common_tags
}

module "storage" {
  source = "../../modules/storage"

  project_name     = var.project_name
  environment_name = var.environment_name
  account_id       = data.aws_caller_identity.current.account_id
  bucket_overrides = var.bucket_overrides
  tags             = local.common_tags
}

module "secrets" {
  source = "../../modules/secrets"

  name_prefix  = local.name_prefix
  secret_names = var.secret_names
  tags         = local.common_tags
}

module "observability" {
  source = "../../modules/observability"

  name_prefix        = local.name_prefix
  log_retention_days = var.log_retention_days
  tags               = local.common_tags
}

module "s3_tables" {
  source = "../../modules/s3_tables"

  project_name      = var.project_name
  environment_name  = var.environment_name
  account_id        = data.aws_caller_identity.current.account_id
  table_bucket_name = var.gold_table_bucket_name
  namespace         = var.gold_namespace
}

module "glue" {
  source = "../../modules/glue"

  name_prefix             = local.name_prefix
  raw_bucket_arn          = module.storage.bucket_arns["raw"]
  curated_bucket_arn      = module.storage.bucket_arns["curated"]
  manifests_bucket_arn    = module.storage.bucket_arns["manifests"]
  s3tables_bucket_arn     = module.s3_tables.table_bucket_arn
  standard_catalog_prefix = var.glue_catalog_prefix
  log_group_arn           = module.observability.log_group_arns["glue"]
  secret_arns             = values(module.secrets.secret_arns)
  tags                    = local.common_tags
}

module "mwaa" {
  source = "../../modules/mwaa"

  name_prefix               = local.name_prefix
  vpc_id                    = module.network.vpc_id
  private_subnet_ids        = module.network.private_subnet_ids
  mwaa_bucket_arn           = module.storage.bucket_arns["mwaa_artifacts"]
  mwaa_bucket_name          = module.storage.bucket_names["mwaa_artifacts"]
  data_bucket_arns          = values(module.storage.bucket_arns)
  secret_arns               = values(module.secrets.secret_arns)
  webserver_access_mode     = var.mwaa_webserver_access_mode
  environment_class         = var.mwaa_environment_class
  min_workers               = var.mwaa_min_workers
  max_workers               = var.mwaa_max_workers
  schedulers                = var.mwaa_schedulers
  dag_s3_path               = var.mwaa_dag_s3_path
  plugins_s3_path           = var.mwaa_plugins_s3_path
  requirements_s3_path      = var.mwaa_requirements_s3_path
  startup_script_s3_path    = var.mwaa_startup_script_s3_path
  airflow_configuration     = var.mwaa_airflow_configuration
  glue_pass_role_arns       = [module.glue.job_role_arn, module.glue.crawler_role_arn]
  source_cidr_for_webserver = module.network.vpc_cidr
  tags                      = local.common_tags
}

module "openmetadata" {
  source = "../../modules/openmetadata"

  name_prefix         = local.name_prefix
  vpc_id              = module.network.vpc_id
  public_subnet_id    = module.network.public_subnet_ids[0]
  admin_ingress_cidrs = var.openmetadata_admin_ingress_cidrs
  instance_type       = var.openmetadata_instance_type
  ssh_key_name        = var.openmetadata_ssh_key_name
  allow_ssh           = var.openmetadata_allow_ssh
  secret_arns         = values(module.secrets.secret_arns)
  log_group_name      = module.observability.log_group_names["openmetadata"]
  tags                = local.common_tags
}

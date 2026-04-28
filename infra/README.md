# Infrastructure

This directory contains the Terraform foundation for the AWS-first target
architecture.

## Scope of this slice

This first cut provisions the minimum platform needed for the parallel ETL
team to target stable infrastructure contracts without requiring DAG or Glue
script changes in this folder.

Included:

- dedicated VPC with public and private subnets
- standard S3 buckets for `raw`, `curated`, `manifests`, and MWAA artifacts
- Amazon S3 Tables bucket and namespace for the managed Iceberg gold layer
- MWAA environment foundation
- Glue execution and crawler roles plus baseline catalog databases
- Secrets Manager placeholders
- OpenMetadata EC2 host foundation
- CloudWatch log groups for Glue and OpenMetadata

Out of scope for this slice:

- DAG bundles and MWAA plugin content
- Glue job scripts and packaging
- CI/CD deployment workflows
- full OpenMetadata application deployment and backing services
- production-grade hardening for IAM, HA, and remote Terraform state

## Layout

```text
infra/
├── envs/
│   └── dev/            # single dev environment composition
└── modules/
    ├── glue/
    ├── mwaa/
    ├── network/
    ├── observability/
    ├── openmetadata/
    ├── s3_tables/
    ├── secrets/
    └── storage/
```

## Entry point

The current root module is [infra/envs/dev](/Users/danny/Documents/UNI/thesis/thesis-proposed-solution/infra/envs/dev).

Typical workflow:

```bash
cd infra/envs/dev
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
```

## ETL-facing outputs

The ETL team should consume Terraform outputs and variables rather than
hardcoding AWS names:

- `raw_root`
- `curated_root`
- `manifest_root`
- `mwaa_bucket_name`
- `mwaa_environment_name`
- `glue_job_role_arn`
- `gold_table_bucket_name`
- `gold_namespace`
- `gold_glue_catalog_id`

The gold layer is not a plain S3 prefix. It is an Amazon S3 Tables table
bucket plus namespace, so ETL promotion should target table identifiers rather
than a `gold_root` path.

## Backend posture

This slice intentionally does not hardcode a remote backend. The environment
currently exposes a placeholder `terraform_state_reference` output so the ETL
and evidence model can wire the field now while a later control-plane slice
adds remote state conventions.

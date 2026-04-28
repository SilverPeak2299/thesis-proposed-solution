locals {
  table_bucket_name = lower(coalesce(var.table_bucket_name, "${var.project_name}-${var.environment_name}-gold-${var.account_id}"))
}

resource "aws_s3tables_table_bucket" "this" {
  name = local.table_bucket_name
}

resource "aws_s3tables_namespace" "this" {
  namespace        = var.namespace
  table_bucket_arn = aws_s3tables_table_bucket.this.arn
}

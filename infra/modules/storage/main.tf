locals {
  default_bucket_names = {
    raw            = "${var.project_name}-${var.environment_name}-raw-${var.account_id}"
    curated        = "${var.project_name}-${var.environment_name}-curated-${var.account_id}"
    manifests      = "${var.project_name}-${var.environment_name}-manifests-${var.account_id}"
    mwaa_artifacts = "${var.project_name}-${var.environment_name}-mwaa-${var.account_id}"
  }

  bucket_names = {
    for key, default_name in local.default_bucket_names :
    key => lower(lookup(var.bucket_overrides, key, default_name))
  }
}

resource "aws_s3_bucket" "this" {
  for_each = local.bucket_names

  bucket = each.value

  tags = merge(var.tags, {
    Name = each.value
    Zone = each.key
  })
}

resource "aws_s3_bucket_versioning" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = aws_s3_bucket.this

  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

locals {
  catalog_databases = {
    raw     = "${var.standard_catalog_prefix}_raw"
    curated = "${var.standard_catalog_prefix}_curated"
  }
}

data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "job" {
  name               = "${var.name_prefix}-glue-job"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-glue-job"
  })
}

resource "aws_iam_role" "crawler" {
  name               = "${var.name_prefix}-glue-crawler"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-glue-crawler"
  })
}

resource "aws_iam_role_policy_attachment" "service_role" {
  for_each = {
    job     = aws_iam_role.job.name
    crawler = aws_iam_role.crawler.name
  }

  role       = each.value
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

data "aws_iam_policy_document" "runtime_access" {
  statement {
    sid    = "GlueStandardBucketAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      var.raw_bucket_arn,
      "${var.raw_bucket_arn}/*",
      var.curated_bucket_arn,
      "${var.curated_bucket_arn}/*",
      var.manifests_bucket_arn,
      "${var.manifests_bucket_arn}/*",
    ]
  }

  statement {
    sid    = "GlueS3TablesAccess"
    effect = "Allow"
    actions = [
      "s3tables:*",
    ]
    resources = [
      var.s3tables_bucket_arn,
      "${var.s3tables_bucket_arn}/*",
    ]
  }

  statement {
    sid    = "GlueLoggingAccess"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [var.log_group_arn, "${var.log_group_arn}:*"]
  }

  statement {
    sid    = "GlueCatalogAccess"
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:DeleteTable",
      "glue:CreateDatabase",
      "glue:UpdateDatabase",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "GlueSecretReadAccess"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = var.secret_arns
  }
}

resource "aws_iam_role_policy" "runtime_access" {
  for_each = {
    job     = aws_iam_role.job.id
    crawler = aws_iam_role.crawler.id
  }

  name   = "${each.key}-runtime-access"
  role   = each.value
  policy = data.aws_iam_policy_document.runtime_access.json
}

resource "aws_glue_catalog_database" "this" {
  for_each = local.catalog_databases

  name = each.value
}

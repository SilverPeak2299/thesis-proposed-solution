locals {
  environment_name = "${var.name_prefix}-mwaa"
}

data "aws_iam_policy_document" "mwaa_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["airflow.amazonaws.com", "airflow-env.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "execution_policy_base" {
  statement {
    sid    = "MwaaArtifactBucketAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = concat(
      [var.mwaa_bucket_arn, "${var.mwaa_bucket_arn}/*"],
      flatten([
        for arn in var.data_bucket_arns : [arn, "${arn}/*"]
      ])
    )
  }

  statement {
    sid    = "MwaaLoggingAndMetrics"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "cloudwatch:PutMetricData",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "MwaaQueueAccess"
    effect = "Allow"
    actions = [
      "sqs:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "MwaaServiceIntegration"
    effect = "Allow"
    actions = [
      "glue:*",
      "airflow:PublishMetrics",
      "ec2:Describe*",
      "elasticloadbalancing:Describe*",
      "kms:Decrypt",
      "kms:GenerateDataKey*",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "execution_policy_passrole" {
  count = length(var.glue_pass_role_arns) == 0 ? 0 : 1

  statement {
    sid    = "MwaaPassGlueRuntimeRoles"
    effect = "Allow"
    actions = [
      "iam:PassRole",
    ]
    resources = var.glue_pass_role_arns

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["glue.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "execution_policy_secrets" {
  count = length(var.secret_arns) == 0 ? 0 : 1

  statement {
    sid    = "MwaaSecretReadAccess"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = var.secret_arns
  }
}

data "aws_iam_policy_document" "execution_policy" {
  source_policy_documents = compact([
    data.aws_iam_policy_document.execution_policy_base.json,
    try(data.aws_iam_policy_document.execution_policy_secrets[0].json, null),
    try(data.aws_iam_policy_document.execution_policy_passrole[0].json, null),
  ])
}

resource "aws_iam_role" "execution" {
  name               = "${local.environment_name}-execution"
  assume_role_policy = data.aws_iam_policy_document.mwaa_assume_role.json

  tags = merge(var.tags, {
    Name = "${local.environment_name}-execution"
  })
}

resource "aws_iam_role_policy" "execution" {
  name   = "${local.environment_name}-execution"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution_policy.json
}

resource "aws_security_group" "this" {
  name        = "${local.environment_name}-sg"
  description = "MWAA environment security group."
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${local.environment_name}-sg"
  })
}

resource "aws_vpc_security_group_ingress_rule" "self" {
  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = aws_security_group.this.id
  ip_protocol                  = "-1"
  description                  = "Required self-referencing ingress for MWAA component communication."
}

resource "aws_mwaa_environment" "this" {
  name               = local.environment_name
  source_bucket_arn  = var.mwaa_bucket_arn
  dag_s3_path        = var.dag_s3_path
  execution_role_arn = aws_iam_role.execution.arn

  environment_class     = var.environment_class
  min_workers           = var.min_workers
  max_workers           = var.max_workers
  schedulers            = var.schedulers
  webserver_access_mode = var.webserver_access_mode

  airflow_configuration_options = var.airflow_configuration
  plugins_s3_path               = var.plugins_s3_path
  requirements_s3_path          = var.requirements_s3_path
  startup_script_s3_path        = var.startup_script_s3_path

  logging_configuration {
    dag_processing_logs {
      enabled   = true
      log_level = "INFO"
    }

    scheduler_logs {
      enabled   = true
      log_level = "INFO"
    }

    task_logs {
      enabled   = true
      log_level = "INFO"
    }

    webserver_logs {
      enabled   = true
      log_level = "INFO"
    }

    worker_logs {
      enabled   = true
      log_level = "INFO"
    }
  }

  network_configuration {
    security_group_ids = [aws_security_group.this.id]
    subnet_ids         = var.private_subnet_ids
  }

  tags = merge(var.tags, {
    Name = local.environment_name
  })
}

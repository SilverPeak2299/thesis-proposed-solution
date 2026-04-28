data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "secret_read" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = var.secret_arns
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.name_prefix}-openmetadata"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-openmetadata"
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy" "secret_read" {
  count = length(var.secret_arns) == 0 ? 0 : 1

  name   = "${var.name_prefix}-openmetadata-secret-read"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.secret_read.json
}

resource "aws_iam_instance_profile" "this" {
  name = "${var.name_prefix}-openmetadata"
  role = aws_iam_role.this.name
}

resource "aws_security_group" "this" {
  name        = "${var.name_prefix}-openmetadata"
  description = "OpenMetadata host security group."
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  dynamic "ingress" {
    for_each = var.admin_ingress_cidrs

    content {
      description = "OpenMetadata UI"
      from_port   = 8585
      to_port     = 8585
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  dynamic "ingress" {
    for_each = var.allow_ssh ? var.admin_ingress_cidrs : []

    content {
      description = "SSH"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-openmetadata"
  })
}

locals {
  bootstrap_script = <<-EOT
    #!/bin/bash
    set -euxo pipefail

    dnf update -y
    dnf install -y docker
    systemctl enable docker
    systemctl start docker
    usermod -aG docker ec2-user

    mkdir -p /opt/openmetadata /var/log/openmetadata
    cat <<'EOF' >/opt/openmetadata/README.txt
    This host is prepared for a containerised OpenMetadata deployment.
    Supply the compose files, secrets, and external dependencies in a later stage.
    EOF

    echo "Bootstrap completed on $(date -u +"%Y-%m-%dT%H:%M:%SZ")" | tee /var/log/openmetadata/bootstrap.log
  EOT
}

resource "aws_instance" "this" {
  ami                         = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = var.instance_type
  subnet_id                   = var.public_subnet_id
  vpc_security_group_ids      = [aws_security_group.this.id]
  iam_instance_profile        = aws_iam_instance_profile.this.name
  associate_public_ip_address = true
  key_name                    = var.ssh_key_name
  user_data                   = local.bootstrap_script
  user_data_replace_on_change = true

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-openmetadata"
  })
}

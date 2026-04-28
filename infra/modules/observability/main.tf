locals {
  log_group_names = {
    glue         = "/${var.name_prefix}/glue/jobs"
    openmetadata = "/${var.name_prefix}/openmetadata"
  }
}

resource "aws_cloudwatch_log_group" "this" {
  for_each = local.log_group_names

  name              = each.value
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = each.value
  })
}

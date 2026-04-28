package thesis.change_gates

deny[msg] {
  not input.governance.branch_name_valid
  msg := "Branch name must match <issue-id>/<short-name>."
}

deny[msg] {
  count(input.governance.issue_references) != 1
  msg := "PR body must link exactly one governing issue using #<issue-id>."
}

deny[msg] {
  input.governance.branch_name_valid
  count(input.governance.issue_references) == 1
  input.governance.branch_issue_id != input.governance.linked_issue_id
  msg := "Branch issue id must match the PR's governing issue id."
}

deny[msg] {
  not input.governance.phase
  msg := "PR body must declare the affected phase."
}

deny[msg] {
  count(input.governance.requirements) == 0
  msg := "PR body must declare at least one affected requirement."
}

deny[msg] {
  not input.governance.template_sections.summary
  msg := "PR body must retain the required governance template sections."
}

deny[msg] {
  not input.governance.template_sections.governing_issue
  msg := "PR body must retain the required governing-issue template section."
}

deny[msg] {
  not input.governance.template_sections.requirements_phase
  msg := "PR body must retain the requirements-and-phase template section."
}

deny[msg] {
  not input.governance.template_sections.validation
  msg := "PR body must retain the validation template section."
}

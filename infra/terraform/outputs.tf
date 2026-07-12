output "run_table_name" {
  value = aws_dynamodb_table.runs.name
}

output "runtime_execution_role_arn" {
  value = aws_iam_role.runtime.arn
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.agentforge.name
}

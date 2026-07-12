variable "aws_region" {
  type        = string
  description = "AWS Region for AgentForge resources."
}

variable "environment" {
  type        = string
  description = "Deployment environment, such as staging or production."
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "log_retention_days" {
  type        = number
  default     = 30
  description = "CloudWatch retention period for application audit logs."
}

variable "runtime_execution_role_name" {
  type        = string
  default     = "agentforge-runtime-execution"
  description = "Execution role passed to AgentCore Runtime during deployment."
}

# IAM Account Access
variable "trusted_principals" {
  description = "IAM ARNs that can assume the Terraform execution role (e.g., your IAM user or SSO role)"
  type        = list(string)
  default     = [] # e.g., ["arn:aws:iam::123456789012:user/you", "arn:aws:iam::123456789012:role/AWSReservedSSO_AdministratorAccess_..."]
}

variable "tf_state_bucket" {
    description = "Terraform State S3 Bucket file name"
    type        = string
}

variable "tf_state_prefix" {
    description = "Terraform state file prefix naming convention"
    type        = string
}

variable "aws_region" {
  type        = string
  description = "AWS region for VPC and resources"
  default     = "ap-southeast-1"
}
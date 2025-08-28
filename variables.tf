# Terraform State File
variable "tf_state_bucket" {
    description = "Terraform State S3 Bucket file name"
    type        = string
}

variable "tf_state_prefix" {
    description = "Terraform state file prefix naming convention"
    type        = string
}

# Redis Cloud Secret Keys
variable "rediscloud_api_key" {
    description = "API key for Redis Cloud account"
    type        = string
}

variable "rediscloud_secret_key" {
    description = "Secret key for Redis Cloud account"
    type        = string
    sensitive   = true
}

variable "redis_subscription_name" {
  type    = string
  default = "demo-subscription"
}

variable "aws_region" {
  type        = string
  description = "AWS region for VPC and resources"
  default     = "ap-southeast-1"
}

# IAM Account Access
variable "trusted_principals" {
  description = "IAM ARNs that can assume the Terraform execution role (e.g., your IAM user or SSO role)"
  type        = list(string)
  default     = [] # e.g., ["arn:aws:iam::123456789012:user/you", "arn:aws:iam::123456789012:role/AWSReservedSSO_AdministratorAccess_..."]
}

# Networking Configuration
variable "vpc_cidr" {
  type        = string
  default     = "10.42.0.0/16"
}
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

# Redis Cloud Subscription Provisioning
variable "subscription_name" {
    type = string
    description = "Redis subscription name"
    default = "default subscription"
}

variable "aws_region_redis_cloud" {
  type        = string
  description = "AWS region for Redis Cloud"
  default     = "ap-southeast-1"
}

variable "preferred_azs" {
  type        = list(string)
  description = "Exact AZ names to use (must be in the selected region)"
  default     = ["ap-southeast-1a", "ap-southeast-1b"]

  validation {
    condition     = length(var.preferred_azs) >= 1 && alltrue([for az in var.preferred_azs : startswith(az, var.region)])
    error_message = "Provide at least one AZs, all starting with the region (e.g., ap-southeast-1a, ap-southeast-1b for ap-southeast-1)."
  }
}

variable "redis_version" {
    type = string
    description = "Redis version to deploy your resources"
    default = "7.2"
}

variable "creation_plans" {
  description = "Aggregated plans Redis uses to pre-provision capacity"
  type = list(object({
    dataset_size_in_gb           = number
    quantity                     = number
    replication                  = bool
    throughput_measurement_by    = string
    throughput_measurement_value = number
    modules = list(string)
  }))
}


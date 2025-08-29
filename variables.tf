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

variable "preferred_azs" {
  type        = list(string)
  description = "Exact AZ names to use (must be in the selected region)"
  default     = ["ap-southeast-1a", "ap-southeast-1b"]

  validation {
    condition     = length(var.preferred_azs) >= 1 && alltrue([for az in var.preferred_azs : startswith(az, var.aws_region)])
    error_message = "Provide at least one AZs, all starting with the region (e.g., ap-southeast-1a, ap-southeast-1b for ap-southeast-1)."
  }
}

variable "preferred_azs" {
  type        = list(string)
  description = "Exact AZ names to use (must be in the selected region)"
  default     = ["ap-southeast-1a", "ap-southeast-1b"]

  validation {
    condition     = length(var.preferred_azs) >= 1 && alltrue([for az in var.preferred_azs : startswith(az, var.aws_region_redis_cloud)])
    error_message = "Provide at least one AZ, and ensure all start with the selected region (e.g., ap-southeast-1a, ap-southeast-1b for ap-southeast-1)."
  }
}

# ----- Dynamic creation_plan input (from your JSON) -----
variable "creation_plans" {
  description = "Reservation plan(s) Redis Cloud uses to pre-provision capacity"
  type = list(object({
    dataset_size_in_gb           = number   # allow decimals like 0.1
    quantity                     = number
    replication                  = bool
    throughput_measurement_value = number
    # optional in your JSON; default to ops/sec if omitted
    throughput_measurement_by    = optional(string, "operations-per-second")
  }))
  default = []
}

# ----- (Optional) per-DB input if/when you add DB resources -----
variable "databases" {
  description = "Per-database config (create one rediscloud_subscription_database per entry)"
  type = map(object({
    dataset_size_in_gb           = number
    replication                  = bool
    throughput_measurement_value = number
    modules                      = optional(list(string), [])
    support_oss_cluster_api      = optional(bool, false)
  }))
  default = {}

  validation {
    condition = alltrue([
      for db in values(var.databases) :
      db.dataset_size_in_gb > 0 && db.throughput_measurement_value >= 0
    ])
    error_message = "Each database must have dataset_size_in_gb > 0 and throughput_measurement_value >= 0."
  }
}

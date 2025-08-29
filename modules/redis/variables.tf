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
    condition     = length(var.preferred_azs) >= 1 && alltrue([for az in var.preferred_azs : startswith(az, var.aws_region_redis_cloud)])
    error_message = "Provide at least one AZ, and ensure all start with the selected region (e.g., ap-southeast-1a, ap-southeast-1b for ap-southeast-1)."
  }
}

variable "redis_version" {
    type = string
    description = "Redis version to deploy your resources"
    default = "7.2"
}

variable "redis_deployment_cidr_block" {
    type = string
    description = "CIDR block redis cloud use on its deployment"
    default = "10.250.1.0/24"
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
}

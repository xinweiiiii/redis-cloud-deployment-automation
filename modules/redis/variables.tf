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

variable "aws_account_id" {
  type        = string
  description = "12-digit AWS Account ID that owns the app VPC"
}

variable "aws_vpc_id" {
  type        = string
  description = "VPC ID to peer with Redis Cloud"
}

variable "app_vpc_cidr" {
  type        = string
  description = "CIDR of your app VPC (if not provided, we'll look it up)"
  default     = null
}

variable "route_table_ids" {
  type        = list(string)
  description = "Route table IDs in your VPC that should route to Redis Cloud via the peering"
  default     = []
}

variable "redis_version" {
  type        = string
  description = "Redis version for the subscription"
  default     = "7.4"
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

variable "databases" {
  description = "Per-database config (create one rediscloud_subscription_database per entry)"
  type = map(object({
    dataset_size_in_gb           = number
    replication                  = bool
    throughput_measurement_value = number
    modules = optional(list(object({
      name    = string
      version = optional(string)
    })))    
    support_oss_cluster_api      = optional(bool, false)
  
    # TODO: Consider shifting this to another env variable
    # Security (all optional — only set in tfvars if you want them)
    enable_tls             = optional(bool)
    password               = optional(string)
    source_ips             = optional(list(string))
    client_ssl_certificate = optional(string)
  
    # --- Data management (make these optional) ---
    data_persistence            = optional(string) # e.g. "none","aof-every-write","aof-every-1-second","snapshot-every-1-hour"
    data_eviction               = optional(string) # e.g. "volatile-lru","allkeys-lru","noeviction", etc.
    average_item_size_in_bytes  = optional(number)
  
    # --- Replication of external DBs (optional) ---
    # URIs like: redis://user:pass@host:port
    replica_ofs                 = optional(list(string))
  
    # --- Alerts (optional) ---
    alerts = optional(list(object({
      name  = string  # e.g., "dataset-size"
      value = number  # threshold
    })))
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

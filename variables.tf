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
# This only works for Redis Cloud Pro Plan and Enterprise Plan
terraform {
  required_providers {
    rediscloud = {
      source = "RedisLabs/rediscloud"
      version = "2.3.1"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.11"
    }
  }
}

provider "rediscloud" {
  api_key    = var.rediscloud_api_key
  secret_key = var.rediscloud_secret_key
}

provider "aws" {
  region = var.aws_region
}

terraform {
  backend "s3" {
    bucket = "redis-cloud-state"
    key = "redis"
    region = "ap-southeast-1"
    encrypt = true
  }
}
# This only works for Redis Cloud Pro Plan and Enterprise Plan
terraform {
  required_providers {
    rediscloud = {
      source = "RedisLabs/rediscloud"
      version = "2.1.5"
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
    bucket = "demo-my-terraform-state-bucket"
    key = "rediscloud/terraform.tfstate"
    region = "ap-southeast-1"
    encrypt = true
  }
}
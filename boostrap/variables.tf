variable "aws_region" {
  type        = string
  description = "AWS region for VPC and resources"
  default     = "ap-southeast-1"
}

variable "tf_state_bucket" {
    description = "Terraform State S3 Bucket file name"
    type        = string
}
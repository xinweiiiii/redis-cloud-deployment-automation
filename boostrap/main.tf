provider "aws" { region = var.aws_region }

# --- S3 bucket for Terraform state ---
resource "aws_s3_bucket" "state" {
  bucket = var.tf_state_bucket
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Default encryption: SSE-S3 (AES256) – NO KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"   # SSE-S3
    }
  }
}

# Deny any non-HTTPS requests
resource "aws_s3_bucket_policy" "deny_insecure_transport" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid       = "DenyInsecureTransport",
      Effect    = "Deny",
      Principal = "*",
      Action    = "s3:*",
      Resource  = [
        aws_s3_bucket.state.arn,
        "${aws_s3_bucket.state.arn}/*"
      ],
      Condition = { Bool = { "aws:SecureTransport": "false" } }
    }]
  })
}
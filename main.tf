module "iam_role" {
    source = "./modules/iam"

    trusted_principals = var.trusted_principals
    tf_state_bucket = var.tf_state_bucket
    tf_state_prefix = var.tf_state_prefix
    aws_region = var.aws_region

}

module "terraform_s3_state" {
    source = "./boostrap"

    aws_region = var.aws_region
    tf_state_bucket = var.tf_state_bucket
}
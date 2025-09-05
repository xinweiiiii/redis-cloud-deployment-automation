module "iam_role" {
    source = "./modules/iam"

    trusted_principals = var.trusted_principals
    tf_state_bucket = var.tf_state_bucket
    tf_state_prefix = var.tf_state_prefix
    aws_region = var.aws_region
    aws_account_id = var.aws_account_id

}

module "terraform_s3_state" {
    source = "./boostrap"
    aws_region = var.aws_region
    tf_state_bucket = var.tf_state_bucket
}

module "redis" {
    source = "./modules/redis"
    
    subscription_name = var.subscription_name
    aws_region_redis_cloud = var.aws_region_redis_cloud
    aws_account_id = var.aws_account_id
    aws_vpc_id = var.aws_vpc_id
    app_vpc_cidr = var.app_vpc_cidr
    route_table_ids = var.route_table_ids
    redis_version = var.redis_version
    redis_deployment_cidr_block = var.redis_deployment_cidr_block
    creation_plans = var.creation_plans
    databases = var.databases
}




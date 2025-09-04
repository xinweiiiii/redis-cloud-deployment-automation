# data "aws_vpc" "app" {
#   id = var.aws_vpc_id
# }

# locals {
#   vpc_cidr_for_peering = coalesce(var.app_vpc_cidr, data.aws_vpc.app.cidr_block)
# }

# resource "rediscloud_subscription_peering" "vpc_peering" {
#   subscription_id = rediscloud_subscription.sub.id

#   # AWS-specific fields
#   region         = var.aws_region_redis_cloud
#   aws_account_id = var.aws_account_id
#   vpc_id         = var.aws_vpc_id
#   vpc_cidr       = local.vpc_cidr_for_peering  # or var.app_vpc_cidr if you don’t use the data source
# }

# # Accept Redis Cloud's peering request in your AWS account
# resource "aws_vpc_peering_connection_accepter" "accept" {
#   vpc_peering_connection_id = rediscloud_subscription_peering.this.aws_peering_id
#   auto_accept               = true
# }

# # Let your VPC resolve private DNS names over the peering
# resource "aws_vpc_peering_connection_options" "acceptor_opts" {
#   vpc_peering_connection_id = aws_vpc_peering_connection_accepter.accept.id

#   accepter {
#     allow_remote_vpc_dns_resolution = true
#   }
# }

# resource "aws_route" "to_redis" {
#   for_each                  = toset(var.route_table_ids)
#   route_table_id            = each.key
#   destination_cidr_block    = var.redis_deployment_cidr_block
#   vpc_peering_connection_id = aws_vpc_peering_connection_accepter.accept.id
# }


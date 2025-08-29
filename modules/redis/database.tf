# Create one Redis Cloud DB per entry in var.databases
resource "rediscloud_subscription_database" "db" {
  for_each = var.databases

  subscription_id = rediscloud_subscription.sub.id
  name            = each.key

  # Size: you're supplying dataset_size_in_gb in your variables.tf
  dataset_size_in_gb = each.value.dataset_size_in_gb

  replication                  = each.value.replication
  throughput_measurement_by    = "operations-per-second"
  throughput_measurement_value = each.value.throughput_measurement_value

  modules                 = try(each.value.modules, [])
  support_oss_cluster_api = try(each.value.support_oss_cluster_api, false)
}
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

    # --- Security (optional) ---
    enable_tls             = try(each.value.enable_tls, null)
    password               = try(each.value.password, null)               # use null, not ""
    source_ips             = try(each.value.source_ips, null)
    client_ssl_certificate = try(each.value.client_ssl_certificate, null) # PEM string
    
    # Data management (optional)
    data_persistence           = try(each.value.data_persistence, null)
    data_eviction              = try(each.value.data_eviction, null)

    # --- Replication of external DBs (optional) ---
    replica_of = try(each.value.replica_ofs, null)

    # --- Alerts (optional) ---
    dynamic "alerts" {
        for_each = try(each.value.alerts, [])
        content {
        name  = alerts.value.name
        value = alerts.value.value
        }
    }
}
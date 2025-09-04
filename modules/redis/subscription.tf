# --------------------
# Data: default payment method - To be added manually in the console
# --------------------
data "rediscloud_payment_method" "default" {}

# --------------------
# Subscription
# --------------------
resource "rediscloud_subscription" "sub" {
    name             = var.subscription_name
    payment_method   = "credit-card"                               # ignored after create
    payment_method_id= data.rediscloud_payment_method.default.id
    memory_storage   = "ram"                                       # or "ram-and-flash"

    # Cloud provider + region details (add more cloud_provider blocks if multi-region)
    cloud_provider {
        provider = "AWS"
        region {
            region                      = var.aws_region_redis_cloud
            networking_deployment_cidr  = var.redis_deployment_cidr_block 
            multiple_availability_zones = true
            # preferred_availability_zones= var.preferred_azs
        }
    }

    // TODO: To be retreive and configure via env variable
    # Creation plan tells Redis Cloud how to size the cluster to host your DBs
    dynamic "creation_plan" {
        for_each = var.creation_plans
        content {
            dataset_size_in_gb              = creation_plan.value.dataset_size_in_gb
            quantity                        = creation_plan.value.quantity
            replication                     = creation_plan.value.replication
            throughput_measurement_by       = try(creation_plan.value.throughput_measurement_by, "operations-per-second")
            throughput_measurement_value    = creation_plan.value.throughput_measurement_value
        }
    }

    # Optional: maintenance windows
    # TODO: Update this config to environment variable but set it as optional
    maintenance_windows {
        mode = "manual"
        window {
            start_hour        = 2
            duration_in_hours = 1
            days              = ["Tuesday", "Friday"]
        }
    }
}
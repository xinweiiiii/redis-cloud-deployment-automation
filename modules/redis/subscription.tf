# --------------------
# Data: default payment method - To be added manually in the console
# --------------------
data "rediscloud_payment_method" "default" {}

# --------------------
# Subscription
# --------------------
resource "rediscloud_subscription" "sub" {
    name             = "demo-subscription"
    payment_method   = "credit-card"                               # ignored after create
    payment_method_id= data.rediscloud_payment_method.default.id
    memory_storage   = "ram"                                       # or "ram-and-flash"
    redis_version    = "7.2"

    # Cloud provider + region details (add more cloud_provider blocks if multi-region)
    cloud_provider {
        provider = "aws"
        region {
            region                      = var.region
            networking_deployment_cidr  = "10.250.1.0/24"               # CIDR Redis Cloud uses on its side
            multiple_availability_zones = true
            preferred_availability_zones= var.preferred_azs
        }
    }

    // TODO: To be retreive and configure via env variable
    # Creation plan tells Redis Cloud how to size the cluster to host your DBs
    creation_plan {
        dataset_size_in_gb              = 2       # per DB
        quantity                        = 1       # number of DBs planned at this size
        replication                     = true
        throughput_measurement_by       = "operations-per-second"
        throughput_measurement_value    = 2000
        # Some provider versions allow defaults here; modules etc. are usually set on the DB resource.
    }

    # Optional: maintenance windows
    maintenance_windows {
        mode = "manual"
        window {
            start_hour        = 2
            duration_in_hours = 1
            days              = ["Tuesday", "Friday"]
        }
    }
}
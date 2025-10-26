# redis-cloud-deployment-automation

This project automates the provisioning of Redis Enterprise Cloud resources (subscriptions and databases) using Terraform or the Redis Cloud REST API based on sizing input provided in an Excel file.

# Overview
The workflow has two pain paths
## 1. Terraform-based Provisioning (Infrastructure as Code)
- Convert a sizing Excel (redis2re) into Terraform variable files.
- Run Terraform to provision:
  - A secure S3 bucket for state storage
  - IAM roles with least privileges
  - Redis Cloud subscription(s) and database(s)

## 2. Redis Cloud API-based Provisionig (Direct REST automation)
- Converts a sizing Excel file into a JSON payloads compatinle with the Redis Cloud REST API
- Uses python scripts to invoke `POST /v1/subscriptions` and `POST /v1/subscriptions/{id}/databases` to provision Redis Cloud resources directly
- Enables programmtic intergration into CI/CD pipelines without terraform

# Prerequsite
- Terraform 
```
brew install terraform
```
- Python 3.9+ (with venv and pip)
- Redis Cloud API Keys
  - Account API Key (`REDIS_CLOUD_ACCOUNT KEY`)
  - User API Key (`REDIS_CLOUD_API_KEY`)
  - Account ID (`REDIS_CLOUD_ACCOUNT_ID`)
  - Provider and Region (e.g. `AWS`, `ap-southeast-1`)
  - Pyament Method ID (`REDIS_CLOUD_PAYMENT_ID`)

You can retreive the payemnt method and ID by running the `get-payment-info.py` script

# Using Redis Cloud API (Direct Provisioning)

## Step 1: Convert Excel/CSV to Redis API JSON payloads
Use `re_stats_json.py` to transform your sizing sheet into Redis Cloud - compatible JSON

```
cd input
python3 -m venv .virtualenv && source .virtualenv/bin/activate
pip install -r requirements.txt

python re_stats_json.py \
  --input ./samples/{filename}.xlsx \
  --out-combined redis_payloads.json
```

This produces a JSON file shaped like
```
{
  "databases": [
    {
      "name": "xw-redis-db1-test",
      "dataset_size_in_gb": 0.1,
      "replication": false,
      "throughput_measurement_by": "operations-per-second",
      "throughput_measurement_value": 100,
      "modules": [],
      "support_oss_cluster_api": false
    }
  ],
  "subscription": {
    "creation_plan": [
      {
        "dataset_size_in_gb": 0.1,
        "quantity": 1,
        "replication": false,
        "throughput_measurement_by": "operations-per-second",
        "throughput_measurement_value": 100
      }
    ]
  }
```

## Step 2: Provision Using Redis Cloud REST API
```
cat ../input/redis_payloads.json | python3 create-db.py
```
This will:
1. Create a redis Cloud PRO subscription using `POST /v1/subscriptions` 
2. Wait until the subscription become active
3. Create the corresponding database under the subscription

All progress and API responses are logged to the console, and task-level details (including error information) are printed if an operation fails.

# Terraform Path
## Convert the `redis2re` input to terraform env variable
```
cd input

python3 -m venv .virtualenv && source .virtualenv/bin/activate

pip install -r requirements.txt

python re_stats_tfvars.py ./samples/{filename}
```
## Initial Run Terraform Init
Comment this code in `config.tf`
```
terraform {
  backend "s3" {
    bucket = "redis-cloud-state"
    key = "redis"
    region = "ap-southeast-1"
    encrypt = true
  }
}
``` 

```
terraform init 
```

```
terraform plan -out=tfplan \
  --var-file="./input/terraform.auto.tfvars.json" \
  --var-file="env.tfvars"
```

Apply the changes
```
terraform apply "tfplan"
```

# Deployment
The initial deployment will create the following resources
1. S3 bucket to store the terraform state refer to next step on how to migrate local terraform state 
2. Create the necessary IAM roles with least priviledge to run the script by assuming the role instead of the user
[Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#bp-workloads-use-roles)
3. Provision Terraform subscription and Databases according to config in `env.tfvars` 

# How to migrate state from local to S3 bucket
Uncomment the code mentioned above:
```
terraform init -migrate-state 
```

# Notes & Best Practices

State safety: Never commit `.tfstate` or `.tfplan` files to Git. They contain sensitive info. Use .gitignore:

```
*.tfstate
*.tfstate.*
.terraform/
*.tfplan
terraform.log
```


Naming: Databases defined in env.tfvars are managed via rediscloud_subscription_database. The initial seed DB created by creation_plan will be adopted/renamed in Terraform.

Modules: If no modules are defined per DB, defaults (RedisJSON, RediSearch) are applied automatically.

IAM roles: Make sure you have credentials that can assume the role provisioned by Terraform.

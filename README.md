# redis-cloud-deployment-automation

This project automates the provisioning of Redis Enterprise Cloud resources (subscriptions and databases) using Terraform, based on sizing input provided in an Excel file.

The workflow:
Convert a sizing Excel (redis2re) into Terraform variable files.

Run Terraform to provision:
- A secure S3 bucket for state storage
- IAM roles with least privileges
- Redis Cloud subscription(s) and database(s)

# Prerequsite
- Terraform 
```
brew install terraform
```
- Python 3.9+ (with venv and pip)

# Run the script
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

# Alternatives
- Explore using redis cloud API directly -> JSON format
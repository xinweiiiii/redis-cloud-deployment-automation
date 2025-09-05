# redis-cloud-deployment-automation

# Prerequsite
- Terraform 
```
brew install terraform
```

# Run the script
## Convert the `redis2re` input to terraform env variable
```
cd input

python3 -m venv .virtualenv && source .virtualenv/bin/activate

pip install -r requirements.txt

python excel_to_terraform_tfvars.py ./samples/{filename}
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
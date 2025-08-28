# redis-cloud-deployment-automation

# Run the script
```
cd bootstrap
terraform init
terraform apply \
  -var 'bucket_name=your-unique-tf-state-bucket' \
  -var 'aws_region=ap-southeast-1' \
```
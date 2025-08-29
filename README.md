# redis-cloud-deployment-automation

# Run the script
```
cd bootstrap
terraform init
terraform apply \
  -var 'bucket_name=your-unique-tf-state-bucket' \
  -var 'aws_region=ap-southeast-1' \
```

# Prepare and activate the virtual environment

```bash
python3 -m venv .virtualenv && source .virtualenv/bin/activate
```

Install necessary libraries and dependencies

```
pip install -r requirements.txt
```
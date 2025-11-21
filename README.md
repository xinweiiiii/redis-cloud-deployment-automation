# Redis Cloud Deployment Automation

A comprehensive automation toolkit for provisioning Redis Enterprise Cloud resources (subscriptions and databases) using either REST API or Terraform (Infrastructure as Code), with an integrated RESTful API service for seamless integration.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [REST API](#rest-api)
- [Command-Line Usage](#command-line-usage)
- [Terraform Path](#terraform-path)
- [Environment Variables](#environment-variables)
- [Input File Format](#input-file-format)
- [Docker Deployment](#docker-deployment)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Overview

This project provides **three deployment paths** for automating Redis Cloud provisioning:

### 1. REST API Service (Recommended)
- **RESTful API** with HTTP endpoints for conversion and provisioning
- File upload support (CSV/Excel)
- Docker containerized with Gunicorn
- Ideal for CI/CD integration and web applications
- No command-line knowledge required

### 2. Redis Cloud API-based Provisioning (Direct REST automation)
- Converts Excel/CSV sizing files into JSON payloads compatible with Redis Cloud REST API
- Uses Python scripts to invoke Redis Cloud API directly
- Enables programmatic integration without Terraform
- Command-line based workflow

### 3. Terraform-based Provisioning (Infrastructure as Code)
- Converts sizing Excel/CSV into Terraform variable files
- Full IaC approach with state management
- Provisions secure S3 bucket, IAM roles, and Redis Cloud resources
- Best for infrastructure teams and GitOps workflows

## Features

### REST API Features
- RESTful endpoints for all conversion and provisioning operations
- File upload support (CSV, Excel formats)
- Automatic conversion of sizing data
- Direct Redis Cloud provisioning
- Combined conversion and provisioning workflow
- Docker containerization with health checks
- Production-ready with Gunicorn (4 workers)
- Comprehensive error handling

### Core Features
- Fuzzy column matching (handles various naming conventions)
- Supports CSV and Excel (.xlsx/.xls) formats
- Expandable quantities (one row becomes N database entries)
- Module support (RedisJSON, RedisSearch, etc.)
- OSS Cluster API configuration
- Replication and throughput management
- Both sync and async operation modes

## Quick Start

### Option 1: Using REST API (Docker - Recommended)

```bash
# 1. Navigate to project directory
cd redis-cloud-deployment-automation

# 2. Configure environment variables
cp rest-api/example.env rest-api/.env
# Edit rest-api/.env with your Redis Cloud credentials

# 3. Start the API service
docker-compose up -d

# 4. Verify service is running
curl http://localhost:9000/health

# 5. Convert and provision in one step
curl -X POST http://localhost:9000/api/convert-and-provision \
  -F "file=@input/samples/sizing.xlsx"
```

### Option 2: Using Makefile

```bash
# Build and run
make run

# Check health
make health

# View logs
make logs

# Run tests
./test-api.sh
```

### Option 3: Command-Line (Direct Provisioning)

```bash
# 1. Install dependencies
cd input
python3 -m venv .virtualenv && source .virtualenv/bin/activate
pip install -r requirements.txt

# 2. Convert Excel to JSON
python re_stats_json.py \
  --input ./samples/sizing.xlsx \
  --out-combined redis_payloads.json

# 3. Provision
cd ../rest-api
cat ../input/redis_payloads.json | python create-db.py
```

## REST API

The REST API service provides HTTP endpoints for all automation tasks.

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/api/convert/json` | POST | Convert CSV/Excel to Redis Cloud JSON |
| `/api/convert/tfvars` | POST | Convert CSV/Excel to Terraform tfvars |
| `/api/provision` | POST | Provision Redis Cloud resources |
| `/api/convert-and-provision` | POST | Convert and provision in one step |

### 1. Health Check

```bash
curl http://localhost:9000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "redis-cloud-automation-api",
  "version": "1.0.0"
}
```

### 2. Convert to JSON

Convert CSV/Excel to Redis Cloud API JSON payloads.

```bash
curl -X POST http://localhost:9000/api/convert/json \
  -F "file=@sizing.xlsx" \
  -F "output_type=combined" \
  -o redis_payloads.json
```

**Parameters:**
- `file` (required): CSV or Excel file
- `output_type` (optional): `databases`, `subscription`, or `combined` (default: `combined`)

**Response Example:**
```json
{
  "databases": [
    {
      "name": "prod-cache-1",
      "dataset_size_in_gb": 10,
      "throughput_measurement_by": "operations-per-second",
      "throughput_measurement_value": 5000,
      "replication": true,
      "modules": ["RedisJSON", "RedisSearch"]
    }
  ],
  "subscription": {
    "creation_plan": [
      {
        "dataset_size_in_gb": 10,
        "quantity": 3,
        "replication": true,
        "throughput_measurement_by": "operations-per-second",
        "throughput_measurement_value": 5000
      }
    ]
  }
}
```

### 3. Convert to Terraform tfvars

```bash
curl -X POST http://localhost:9000/api/convert/tfvars \
  -F "file=@sizing.csv" \
  -F "emit_hcl=true" \
  | jq '.'
```

**Parameters:**
- `file` (required): CSV or Excel file
- `emit_hcl` (optional): `true` or `false` (default: `false`)

### 4. Provision Redis Cloud Resources

```bash
curl -X POST http://localhost:9000/api/provision \
  -H "Content-Type: application/json" \
  -d @redis_payloads.json
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "subscription_id": 12345,
    "database_ids": [67890, 67891, 67892]
  }
}
```

### 5. Convert and Provision (One-Step)

```bash
curl -X POST http://localhost:9000/api/convert-and-provision \
  -F "file=@sizing.xlsx"
```

### Using Python with the API

```python
import requests

# Convert to JSON
with open('sizing.xlsx', 'rb') as f:
    response = requests.post(
        'http://localhost:9000/api/convert/json',
        files={'file': f},
        data={'output_type': 'combined'}
    )
    payload = response.json()

# Provision
response = requests.post(
    'http://localhost:9000/api/provision',
    json=payload
)
print(response.json())
```

## Command-Line Usage

### Using the Python Scripts Directly

#### Step 1: Convert Excel/CSV to Redis API JSON

```bash
cd input
python3 -m venv .virtualenv && source .virtualenv/bin/activate
pip install -r requirements.txt

python re_stats_json.py \
  --input ./samples/sizing.xlsx \
  --out-databases databases.json \
  --out-subscription subscription.json \
  --out-combined redis_payloads.json
```

**Output files:**
- `databases.json` - Array of individual database objects (quantities expanded)
- `subscription.json` - Aggregated `creation_plan` grouped by size/replication/throughput
- `redis_payloads.json` - Combined JSON with both databases and subscription

#### Step 2: Provision Using Redis Cloud REST API

```bash
cd ../rest-api
cat ../input/redis_payloads.json | python create-db.py
```

This will:
1. Create a Redis Cloud PRO subscription using `POST /v1/subscriptions`
2. Wait until the subscription becomes active
3. Create the corresponding databases under the subscription

All progress and API responses are logged to the console.

## Terraform Path

### Step 1: Convert to Terraform Variables

```bash
cd input
python3 -m venv .virtualenv && source .virtualenv/bin/activate
pip install -r requirements.txt

python re_stats_tfvars.py \
  --input ./samples/sizing.xlsx \
  --output terraform.auto.tfvars.json \
  --emit-hcl
```

### Step 2: Initial Terraform Setup

**Note:** For the first run, comment out the backend configuration in `config.tf`:

```hcl
# terraform {
#   backend "s3" {
#     bucket = "redis-cloud-state"
#     key = "redis"
#     region = "ap-southeast-1"
#     encrypt = true
#   }
# }
```

Then initialize:

```bash
terraform init
```

### Step 3: Plan and Apply

```bash
# Create execution plan
terraform plan -out=tfplan \
  --var-file="./input/terraform.auto.tfvars.json" \
  --var-file="env.tfvars"

# Apply changes
terraform apply "tfplan"
```

### Step 4: Migrate State to S3 (After Initial Deployment)

Uncomment the backend configuration in `config.tf`, then:

```bash
terraform init -migrate-state
```

### What Terraform Creates

1. **S3 Bucket** - For Terraform state storage with encryption
2. **IAM Roles** - With least privilege permissions (follows AWS best practices)
3. **Redis Cloud Subscription** - Based on `creation_plan` from tfvars
4. **Redis Cloud Databases** - Individual databases with custom configurations

## Environment Variables

### Required for Redis Cloud Provisioning

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_CLOUD_ACCOUNT_KEY` | Redis Cloud account API key | `abc123...` |
| `REDIS_CLOUD_API_KEY` | Redis Cloud user secret key | `xyz789...` |
| `REDIS_CLOUD_ACCOUNT_ID` | Redis Cloud account ID | `12345` |
| `REDIS_CLOUD_PROVIDER` | Cloud provider | `AWS`, `GCP`, or `Azure` |
| `REDIS_CLOUD_REGION` | Cloud region | `us-east-1`, `ap-southeast-1` |
| `REDIS_CLOUD_PAYMENT_METHOD_ID` | Payment method ID | `67890` |

### Optional Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_CLOUD_BASE_URL` | API endpoint | `https://api.redislabs.com/v1` |
| `REDIS_CLOUD_SUBSCRIPTION_NAME` | Custom subscription name | Auto-generated |
| `REDIS_CLOUD_DEPLOYMENT_CIDR` | VPC CIDR block | `10.0.1.0/24` |
| `PORT` | API server port | `9000` |
| `FLASK_DEBUG` | Enable debug mode | `false` |

### Getting Your Payment Method ID

```bash
cd rest-api
python get-payment-id.py
```

This will list all available payment methods and their IDs.

## Input File Format

Your CSV/Excel file should have these columns (fuzzy matching supported):

| Column Name | Aliases | Required | Description |
|-------------|---------|----------|-------------|
| Database Name | `databaseName`, `database`, `db`, `name` | Yes | Name of the database |
| Quantity | `quantity`, `qty`, `count`, `number` | No | Number of instances (default: 1) |
| Dataset Size (GB) | `datasetSizeInGB`, `memoryGB`, `sizeGB` | Yes | Memory size in GB |
| Throughput (ops/sec) | `throughputOpsSec`, `throughput`, `opsSec` | No | Operations per second |
| Replication | `replication`, `replicated`, `enableReplication` | No | Enable replication (true/false) |
| OSS Cluster API | `ossClusterAPI`, `support_oss_cluster_api` | No | Support OSS Cluster API |
| Modules | `modules`, `redis_modules` | No | Comma-separated list |

### Example CSV

```csv
Database Name,Quantity,Dataset Size (GB),Throughput (ops/sec),Replication,Modules
prod-cache,3,10,5000,true,"RedisJSON,RedisSearch"
dev-cache,2,5,2000,false,
staging-cache,1,8,3000,true,RedisJSON
```

### Example Excel

See sample files in `input/samples/` directory.

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Access container shell
docker-compose exec redis-automation-api /bin/bash
```

### Manual Docker Commands

```bash
# Build image
docker build -t redis-automation-api:latest .

# Run container
docker run -d \
  -p 9000:9000 \
  --env-file rest-api/.env \
  --name redis-automation-api \
  redis-automation-api:latest

# View logs
docker logs -f redis-automation-api

# Stop and remove
docker stop redis-automation-api
docker rm redis-automation-api
```

### Docker Container Details

- **Base Image**: Python 3.11 slim
- **Server**: Gunicorn with 4 workers
- **Port**: 9000 (configurable via `PORT` env var)
- **Health Check**: Automatic health monitoring
- **Upload Limit**: 16MB max file size
- **Timeout**: 120 seconds per request

## Development

### Project Structure

```
redis-cloud-deployment-automation/
├── rest-api/
│   ├── app.py              # Flask API application
│   ├── create-db.py        # Redis Cloud provisioning logic
│   ├── get-payment-id.py   # Payment method helper
│   ├── .env                # Environment configuration
│   └── example.env         # Environment template
├── input/
│   ├── re_stats_json.py    # CSV → JSON converter
│   ├── re_stats_tfvars.py  # CSV → Terraform converter
│   ├── helper.py           # Shared utilities
│   ├── requirements.txt    # Python dependencies
│   └── samples/            # Example input files
├── modules/redis/          # Terraform modules
│   ├── subscription.tf
│   ├── database.tf
│   ├── networking.tf
│   └── security.tf
├── bootstrap/              # Initial AWS setup
├── Dockerfile              # Container definition
├── docker-compose.yml      # Docker Compose config
├── requirements.txt        # API dependencies
├── Makefile               # Development commands
├── test-api.sh            # Bash test script
├── test-api.py            # Python test script
├── QUICKSTART.md          # Quick start guide
└── README.md              # This file
```

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv .virtualenv
source .virtualenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run API locally
cd rest-api
export FLASK_DEBUG=true
python app.py
```

### Running Tests

```bash
# Make sure API is running first
docker-compose up -d

# Run bash tests
./test-api.sh

# Run Python tests
python test-api.py

# Test with custom file
SAMPLE_FILE=my_file.xlsx ./test-api.sh
```

### Makefile Commands

```bash
make help      # Show all available commands
make build     # Build Docker image
make run       # Start the service
make stop      # Stop the service
make restart   # Restart the service
make logs      # View logs
make health    # Check health status
make test      # Run basic tests
make shell     # Open shell in container
make clean     # Remove everything
make dev       # Run in development mode locally
```

## Troubleshooting

### API Issues

**Issue: API not responding**
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f

# Restart
docker-compose restart
```

**Issue: "Missing required environment variables"**
```bash
# Verify .env file exists
ls -la rest-api/.env

# Check variables in container
docker-compose exec redis-automation-api env | grep REDIS_CLOUD
```

**Issue: "File too large"**
- Maximum file size is 16MB
- Split large Excel files or increase `MAX_CONTENT_LENGTH` in `rest-api/app.py`

**Issue: Health check failing**
```bash
# Check logs
docker logs redis-automation-api

# Verify port is accessible
curl http://localhost:9000/health

# Check if port is in use
lsof -i :9000
```

### Conversion Issues

**Issue: Column not found**
- The scripts use fuzzy matching
- Check your column names match the expected aliases
- Add new aliases in `input/helper.py` if needed

**Issue: Invalid file format**
- Only `.csv`, `.xlsx`, and `.xls` files are supported
- Ensure file is not corrupted

### Provisioning Issues

**Issue: Authentication failed**
- Verify `REDIS_CLOUD_ACCOUNT_KEY` and `REDIS_CLOUD_API_KEY` are correct
- Check that API keys have proper permissions

**Issue: Payment method not found**
- Run `python get-payment-id.py` to list available payment methods
- Update `REDIS_CLOUD_PAYMENT_METHOD_ID` in `.env`

**Issue: Region not available**
- Verify the region is supported by your Redis Cloud account
- Check `REDIS_CLOUD_PROVIDER` and `REDIS_CLOUD_REGION` combination

### Terraform Issues

**Issue: State lock**
```bash
# Remove lock if safe to do so
terraform force-unlock <lock-id>
```

**Issue: IAM permissions**
- Ensure your AWS credentials have necessary permissions
- Verify you can assume the created IAM role

## Best Practices

### Security
1. **Never commit credentials** - Use `.env` files and add them to `.gitignore`
2. **Use IAM roles** - For Terraform, use role assumption instead of user credentials
3. **Enable encryption** - S3 state bucket is encrypted by default
4. **HTTPS in production** - Use reverse proxy (nginx, Traefik) for API
5. **Rate limiting** - Consider adding rate limiting for production API

### State Management (Terraform)
```bash
# Never commit these files
*.tfstate
*.tfstate.*
.terraform/
*.tfplan
terraform.log
```

### Naming Conventions
- Database names in `terraform.auto.tfvars.json` are managed via `rediscloud_subscription_database`
- The initial seed DB from `creation_plan` will be adopted/renamed by Terraform

### Modules
- If no modules are defined per database, defaults (RedisJSON, RediSearch) are applied automatically
- Module names are case-sensitive

## Production Deployment

For production use:

1. **Use HTTPS**: Put API behind reverse proxy
2. **Set strong secrets**: Generate unique API keys
3. **Enable monitoring**: Add logging and metrics (Prometheus, Grafana)
4. **Scale workers**: Adjust Gunicorn workers in `Dockerfile`
5. **Add rate limiting**: Prevent API abuse
6. **Backup configurations**: Store `.env` securely (AWS Secrets Manager, etc.)
7. **Use managed Redis**: Consider Redis Cloud for production workloads

### Example nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for provisioning operations
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

## Error Handling

The API returns standard HTTP status codes:

- `200 OK` - Successful request
- `400 Bad Request` - Invalid input (missing file, wrong format, etc.)
- `413 Payload Too Large` - File exceeds 16MB limit
- `500 Internal Server Error` - Processing failure

**Error Response Format:**
```json
{
  "error": "Error message",
  "details": "Detailed error information"
}
```

## Prerequisites

- **Python**: 3.9+ (tested with 3.11)
- **Docker**: For containerized deployment
- **Terraform**: If using IaC path (`brew install terraform`)
- **Redis Cloud Account**: With API credentials
- **AWS Account**: If using Terraform with S3 backend

## Support & Resources

- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup
- **AWS IAM Best Practices**: [AWS Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- **Redis Cloud API**: [Official Documentation](https://docs.redis.com/latest/rc/api/)
- **Terraform Redis Provider**: [Registry](https://registry.terraform.io/providers/RedisLabs/rediscloud/latest/docs)

## License

This project is part of the Redis Cloud Deployment Automation toolkit.

---

**Need help?**
- Check logs: `docker-compose logs -f`
- Run tests: `./test-api.sh` or `python test-api.py`
- Review [QUICKSTART.md](QUICKSTART.md) for common workflows

#!/usr/bin/env python3
"""
Redis Cloud Deployment Automation API

This Flask application exposes REST endpoints for:
1. Converting CSV/Excel files to Redis Cloud JSON payloads
2. Converting CSV/Excel files to Terraform tfvars
3. Provisioning Redis Cloud resources via REST API

Endpoints:
- POST /api/convert/json - Convert CSV/Excel to Redis API JSON
- POST /api/convert/tfvars - Convert CSV/Excel to Terraform tfvars
- POST /api/provision - Provision Redis Cloud resources
- GET /health - Health check endpoint
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import logging

# Add input directory to Python path to import the conversion scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "input"))

# Import the conversion modules
import re_stats_json
import re_stats_tfvars

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'redis-cloud-automation-api',
        'version': '1.0.0'
    }), 200


@app.route('/api/convert/json', methods=['POST'])
def convert_to_json():
    """
    Convert CSV/Excel file to Redis Cloud API JSON payloads

    Form data:
    - file: CSV or Excel file
    - output_type: 'databases', 'subscription', or 'combined' (default: 'combined')

    Returns:
    - JSON payload suitable for Redis Cloud REST API
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use CSV or Excel files'}), 400

        # Get output type parameter
        output_type = request.form.get('output_type', 'combined')
        if output_type not in ['databases', 'subscription', 'combined']:
            return jsonify({'error': 'Invalid output_type. Use: databases, subscription, or combined'}), 400

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_input = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_input)

        try:
            # Create temporary output files
            temp_db = os.path.join(app.config['UPLOAD_FOLDER'], 'databases.json')
            temp_sub = os.path.join(app.config['UPLOAD_FOLDER'], 'subscription.json')
            temp_combined = os.path.join(app.config['UPLOAD_FOLDER'], 'redis_payloads.json')

            # Call the re_stats_json script
            cmd = [
                sys.executable,
                str(Path(__file__).parent.parent / "input" / "re_stats_json.py"),
                '--input', temp_input,
                '--out-databases', temp_db,
                '--out-subscription', temp_sub,
                '--out-combined', temp_combined
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Conversion output: {result.stdout}")

            # Read and return the requested output
            if output_type == 'databases':
                with open(temp_db, 'r') as f:
                    data = json.load(f)
            elif output_type == 'subscription':
                with open(temp_sub, 'r') as f:
                    data = json.load(f)
            else:  # combined
                with open(temp_combined, 'r') as f:
                    data = json.load(f)

            # Clean up temporary files
            for temp_file in [temp_db, temp_sub, temp_combined]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            return jsonify(data), 200

        finally:
            # Clean up input file
            if os.path.exists(temp_input):
                os.remove(temp_input)

    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion failed: {e.stderr}")
        return jsonify({
            'error': 'Conversion failed',
            'details': e.stderr
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/convert/tfvars', methods=['POST'])
def convert_to_tfvars():
    """
    Convert CSV/Excel file to Terraform tfvars JSON

    Form data:
    - file: CSV or Excel file
    - emit_hcl: 'true' or 'false' (default: 'false')

    Returns:
    - JSON tfvars suitable for Terraform
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use CSV or Excel files'}), 400

        # Get emit_hcl parameter
        emit_hcl = request.form.get('emit_hcl', 'false').lower() == 'true'

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_input = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_input)

        try:
            # Create temporary output file
            temp_output = os.path.join(app.config['UPLOAD_FOLDER'], 'terraform.auto.tfvars.json')

            # Call the re_stats_tfvars script
            cmd = [
                sys.executable,
                str(Path(__file__).parent.parent / "input" / "re_stats_tfvars.py"),
                '--input', temp_input,
                '--output', temp_output
            ]

            if emit_hcl:
                cmd.append('--emit-hcl')

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Conversion output: {result.stdout}")

            # Read the output
            with open(temp_output, 'r') as f:
                data = json.load(f)

            # Clean up temporary output file
            if os.path.exists(temp_output):
                os.remove(temp_output)

            response = {'tfvars': data}

            # If HCL was requested, include it in the response
            if emit_hcl and result.stdout:
                response['hcl'] = result.stdout

            return jsonify(response), 200

        finally:
            # Clean up input file
            if os.path.exists(temp_input):
                os.remove(temp_input)

    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion failed: {e.stderr}")
        return jsonify({
            'error': 'Conversion failed',
            'details': e.stderr
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/provision', methods=['POST'])
def provision_redis():
    """
    Provision Redis Cloud resources

    JSON body:
    - databases: Array of database configurations
    - subscription: Subscription configuration with creation_plan

    Environment variables required:
    - REDIS_CLOUD_ACCOUNT_KEY
    - REDIS_CLOUD_API_KEY
    - REDIS_CLOUD_ACCOUNT_ID
    - REDIS_CLOUD_PROVIDER
    - REDIS_CLOUD_REGION
    - REDIS_CLOUD_PAYMENT_METHOD_ID

    Returns:
    - Provisioning result with subscription and database IDs
    """
    try:
        # Validate required environment variables
        required_env_vars = [
            'REDIS_CLOUD_ACCOUNT_KEY',
            'REDIS_CLOUD_API_KEY',
            'REDIS_CLOUD_ACCOUNT_ID',
            'REDIS_CLOUD_PROVIDER',
            'REDIS_CLOUD_REGION',
            'REDIS_CLOUD_PAYMENT_METHOD_ID'
        ]

        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            return jsonify({
                'error': 'Missing required environment variables',
                'missing': missing_vars
            }), 400

        # Get JSON payload
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        payload = request.get_json()

        if not payload:
            return jsonify({'error': 'Empty JSON payload'}), 400

        # Validate payload structure
        if 'databases' not in payload and 'subscription' not in payload:
            return jsonify({
                'error': 'Payload must contain either "databases" or "subscription" key'
            }), 400

        # Save payload to temporary file
        temp_payload = os.path.join(app.config['UPLOAD_FOLDER'], 'provision_payload.json')
        with open(temp_payload, 'w') as f:
            json.dump(payload, f, indent=2)

        try:
            # Call the create-db.py script
            cmd = [
                sys.executable,
                str(Path(__file__).parent / "create-db.py")
            ]

            # Pass JSON via stdin
            with open(temp_payload, 'r') as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    capture_output=True,
                    text=True,
                    check=True
                )

            logger.info(f"Provisioning output: {result.stdout}")

            # Parse the output (create-db.py may print JSON or text)
            try:
                output_data = json.loads(result.stdout)
                return jsonify({
                    'status': 'success',
                    'result': output_data
                }), 200
            except json.JSONDecodeError:
                # If output is not JSON, return as text
                return jsonify({
                    'status': 'success',
                    'message': result.stdout
                }), 200

        finally:
            # Clean up temporary file
            if os.path.exists(temp_payload):
                os.remove(temp_payload)

    except subprocess.CalledProcessError as e:
        logger.error(f"Provisioning failed: {e.stderr}")
        return jsonify({
            'error': 'Provisioning failed',
            'details': e.stderr,
            'stdout': e.stdout
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/convert-and-provision', methods=['POST'])
def convert_and_provision():
    """
    Combined endpoint: Convert CSV/Excel to JSON and provision Redis Cloud resources

    Form data:
    - file: CSV or Excel file

    Returns:
    - Provisioning result
    """
    try:
        # First, convert to JSON
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use CSV or Excel files'}), 400

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_input = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_input)

        try:
            # Convert to JSON
            temp_combined = os.path.join(app.config['UPLOAD_FOLDER'], 'redis_payloads_provision.json')

            cmd_convert = [
                sys.executable,
                str(Path(__file__).parent.parent / "input" / "re_stats_json.py"),
                '--input', temp_input,
                '--out-combined', temp_combined
            ]

            subprocess.run(cmd_convert, capture_output=True, text=True, check=True)

            # Now provision using the generated JSON
            cmd_provision = [
                sys.executable,
                str(Path(__file__).parent / "create-db.py")
            ]

            with open(temp_combined, 'r') as f:
                result = subprocess.run(
                    cmd_provision,
                    stdin=f,
                    capture_output=True,
                    text=True,
                    check=True
                )

            logger.info(f"Provisioning output: {result.stdout}")

            # Clean up
            if os.path.exists(temp_combined):
                os.remove(temp_combined)

            try:
                output_data = json.loads(result.stdout)
                return jsonify({
                    'status': 'success',
                    'result': output_data
                }), 200
            except json.JSONDecodeError:
                return jsonify({
                    'status': 'success',
                    'message': result.stdout
                }), 200

        finally:
            if os.path.exists(temp_input):
                os.remove(temp_input)

    except subprocess.CalledProcessError as e:
        logger.error(f"Operation failed: {e.stderr}")
        return jsonify({
            'error': 'Operation failed',
            'details': e.stderr
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file size limit exceeded"""
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    logger.info(f"Starting Redis Cloud Automation API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

import json
import os
import io
import urllib.parse
import boto3
import pandas as pd
import datetime

# AWS S3 Client initialization
s3_client = boto3.client('s3')

# Bucket names will come from environment variables in AWS
PROCESSED_BUCKET = os.environ.get('PROCESSED_BUCKET', 'my-processed-bucket')
DLQ_BUCKET = os.environ.get('DLQ_BUCKET', 'my-dlq-bucket')


def validate_record(record):
    """
    Validation Rules:
    1. Must contain all required keys: transaction_id, customer_id, amount, timestamp
    2. amount must be a number greater than 0
    """
    required_fields = ['transaction_id', 'customer_id', 'amount', 'timestamp']
    
    # 1. Check for missing fields
    for field in required_fields:
        if field not in record or record[field] is None:
            return False, f"Missing required field: '{field}'"
    
    # 2. Check amount validity
    try:
        amount = float(record['amount'])
        if amount <= 0:
            return False, f"Invalid amount: {amount}. Must be greater than 0."
    except (ValueError, TypeError):
        return False, f"Amount '{record['amount']}' is not a valid number."
        
    return True, None


def lambda_handler(event, context):
    """
    AWS Lambda entry point triggered by S3 file upload.
    """
    for record in event['Records']:
        # Extract bucket and file key from the S3 event notification
        bucket_name = record['s3']['bucket']['name']
        object_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        
        # Read the file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read().decode('utf-8')
        
        # Parse JSON input
        raw_data = json.loads(content)
        if isinstance(raw_data, dict):
            raw_data = [raw_data]

        valid_records = []
        dlq_records = []

        # Validate each record in the file
        for item in raw_data:
            is_valid, reason = validate_record(item)
            if is_valid:
                valid_records.append(item)
            else:
                # Attach diagnostics to bad records
                item['_error_reason'] = reason
                item['_source_file'] = object_key
                dlq_records.append(item)

        # Partition by date for fast SQL querying (year=YYYY/month=MM/day=DD)
        now = datetime.datetime.utcnow()
        partition_path = f"year={now.strftime('%Y')}/month={now.strftime('%m')}/day={now.strftime('%d')}"
        file_base_name = os.path.basename(object_key).rsplit('.', 1)[0]

        # ---------------------------------------------------
        # 1. Process Valid Records -> Convert to Parquet -> Save
        # ---------------------------------------------------
        if valid_records:
            df = pd.DataFrame(valid_records)
            df['amount'] = df['amount'].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Convert Pandas DataFrame to Parquet bytes in memory
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, engine='pyarrow')
            
            out_key = f"processed/{partition_path}/{file_base_name}.parquet"
            s3_client.put_object(
                Bucket=PROCESSED_BUCKET,
                Key=out_key,
                Body=parquet_buffer.getvalue()
            )
            print(f"Successfully processed {len(valid_records)} valid records to s3://{PROCESSED_BUCKET}/{out_key}")

        # ---------------------------------------------------
        # 2. Process Bad Records -> JSON DLQ -> Save
        # ---------------------------------------------------
        if dlq_records:
            dlq_key = f"dlq/{partition_path}/failed_{file_base_name}.json"
            s3_client.put_object(
                Bucket=DLQ_BUCKET,
                Key=dlq_key,
                Body=json.dumps(dlq_records, indent=2)
            )
            print(f"Quarantined {len(dlq_records)} invalid records to s3://{DLQ_BUCKET}/{dlq_key}")

    return {
        "statusCode": 200,
        "body": json.dumps("Processing complete")
    }
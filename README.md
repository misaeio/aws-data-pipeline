# AWS Serverless Data Processing Pipeline

A data pipeline built with Python and AWS that processes uploaded CSV files, removes bad or duplicate records, saves clean files back to S3, and lets you query the results with SQL in Athena.

## How It Works

    [Raw CSV Upload]
           │
           ▼
    ┌─────────────────────┐
    │   Amazon S3 (Raw)   │
    └──────────┬──────────┘
               │ S3 Upload Event
               ▼
    ┌─────────────────────┐      ┌──────────────────────┐
    │     AWS Lambda      │─────▶│  Amazon CloudWatch   │
    │    (Python ETL)     │      │   (Logs and Errors)  │
    └──────────┬──────────┘      └──────────────────────┘
               │
               ▼
    ┌─────────────────────┐      ┌──────────────────────┐
    │  Amazon S3 (Clean)  │◀─────│    Amazon Athena     │
    └─────────────────────┘      │    (SQL Queries)     │
                                 └──────────────────────┘

1. A user uploads a raw CSV file to an Amazon S3 bucket.
2. S3 detects the new file and triggers an AWS Lambda function.
3. Lambda runs a Python script using Boto3 to download and read the CSV.
4. The script cleans text fields, converts numbers, checks for missing values, and removes duplicate rows.
5. Lambda saves the clean data to a separate processed folder in S3 while keeping the original raw file untouched.
6. Amazon Athena runs SQL queries directly on the clean S3 files without needing a separate database server.
7. Amazon CloudWatch records logs and errors for every run.

## Tools Used

* Python 3 and Boto3
* Amazon S3 for raw and clean file storage
* AWS Lambda for running the Python script
* Amazon Athena for SQL queries
* AWS IAM for permissions
* Amazon CloudWatch for logs and monitoring
* GitHub Actions and pytest for automated tests

## Permissions and Monitoring

The Lambda function uses an IAM role with only the permissions it needs to read raw files, write clean files, and send logs to CloudWatch. CloudWatch tracks each run so errors and failed files are easy to debug.

## Testing

Automated tests run through GitHub Actions every time code is pushed. The pytest suite checks data cleaning, type conversion, missing fields, and duplicate removal.

    pytest

## Example SQL Query

    SELECT
        customer_id,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_amount
    FROM transactions
    GROUP BY customer_id;

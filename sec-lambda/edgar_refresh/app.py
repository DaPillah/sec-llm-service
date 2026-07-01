import requests
import requests.exceptions
import botocore.exceptions
import boto3
import os
import json

USER_AGENT = "Justin okedaramola1@gmail.com"
SEC_URL = "https://www.sec.gov/files/company_tickers.json"

def lambda_handler(event, context):
    try:
        bucket = os.environ["BUCKET_NAME"]

        # Download from SEC with specific error handling
        try:
            response = requests.get(
                SEC_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=30
            )
            if response.status_code == 403:
                print(f"SEC EDGAR 403 for {SEC_URL} - check User-Agent header")
                return {
                    "statusCode": 502,
                    "error": "SECAccessDenied",
                    "message": f"SEC EDGAR returned 403. Check User-Agent header."
                }
            elif response.status_code != 200:
                print(f"SEC EDGAR {response.status_code} for {SEC_URL}")
                return {
                    "statusCode": 502,
                    "error": "SECUnavailable",
                    "message": f"SEC EDGAR returned {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            print(f"SEC EDGAR network error: {e}")
            return {
                "statusCode": 502,
                "error": "SECUnavailable",
                "message": f"SEC EDGAR request failed: {str(e)}"
            }

        # Upload to S3 with specific error handling
        try:
            s3 = boto3.client("s3")
            s3.put_object(
                Bucket=bucket,
                Key="company_tickers.json",
                Body=response.content
            )
        except botocore.exceptions.ClientError as e:
            print(f"S3 upload error: {e}")
            return {
                "statusCode": 500,
                "error": "S3Error",
                "message": f"Failed to upload to S3: {str(e)}"
            }

        return {
            "statusCode": 200,
            "body": json.dumps("Successfully uploaded company_tickers.json to S3")
        }

    except Exception as e:
        print(f"Unhandled error in refresh function: {e}")
        return {
            "statusCode": 500,
            "error": "InternalError",
            "message": "An unexpected error occurred"
        }
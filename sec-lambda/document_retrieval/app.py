import boto3
import botocore.exceptions
import json
import os
import time
import requests
import requests.exceptions
from sec_edgar import SecEdgar

def lambda_handler(event, context):
    
    #  Input validation first
    required_fields = ["ticker", "period", "question", "year"]
    for field in required_fields:
        if field not in event:
            return {
                "statusCode": 400,
                "error": "ValidationError",
                "message": f"Missing required field: {field}"
            }

    ticker = event["ticker"]
    period = event["period"]
    question = event["question"]
    year = event["year"]

    #  Validate period
    valid_periods = ["Q1", "Q2", "Q3", "Q4", "FY"]
    if period not in valid_periods:
        return {
            "error": "ValidationError",
            "message": f"Invalid value for 'period': '{period}'. Must be one of: Q1, Q2, Q3, Q4, FY."
        }

    # Map period to form_type and quarter
    period_map = {
        "Q1": ("10-Q", 1),
        "Q2": ("10-Q", 2),
        "Q3": ("10-Q", 3),
        "Q4": ("10-Q", 4),
        "FY": ("10-K", None)
    }
    form_type, quarter = period_map[period]

    try:
        # Get bucket name
        bucket = os.environ["BUCKET_NAME"]

        # Read from S3
        try:
            s3 = boto3.client("s3")
            r = s3.get_object(Bucket=bucket, Key="company_tickers.json")
            raw_data = json.loads(r["Body"].read())
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            print(f"S3 error for ticker={ticker}: {e}")
            if error_code == "NoSuchBucket":
                return {
                    "statusCode": 500,
                    "error": "S3Error",
                    "message": f"S3 bucket not found: {bucket}"
                }
            elif error_code == "NoSuchKey":
                return {
                    "statusCode": 500,
                    "error": "S3Error",
                    "message": "company_tickers.json not found in S3. Run refresh function first."
                }
            raise  # re-raise if unknown S3 error

        # Create SecEdgar and look up ticker
        se = SecEdgar(data=raw_data)
        result = se.ticker_to_cik(ticker)
        if not result:
            return {
                "statusCode": 404,
                "error": "TickerNotFound",
                "message": f"Ticker '{ticker}' not found in SEC EDGAR"
            }
        company = result[0]
        cik = result[1]

        # Get filing with SEC EDGAR error handling
        try:
            if form_type == "10-Q":
                filing = se.quarterly_filing(cik, year, quarter)
            else:
                filing = se.annual_filing(cik, year)
        except requests.exceptions.RequestException as e:
            print(f"SEC EDGAR network error for ticker={ticker} year={year}: {e}")
            return {
                "statusCode": 502,
                "error": "SECUnavailable",
                "message": f"SEC EDGAR request failed: {str(e)}"
            }

        if not filing:
            return {
                "statusCode": 404,
                "error": "FilingNotFound",
                "message": f"No {form_type} filing found for {ticker} {period} {year}"
            }

        # Get document with SEC EDGAR error handling
        try:
            doc = se.get_doc(company, form_type=form_type, accession=filing["accessionNumber"])
        except requests.exceptions.RequestException as e:
            print(f"SEC EDGAR document fetch error for ticker={ticker}: {e}")
            return {
                "statusCode": 502,
                "error": "SECUnavailable",
                "message": f"Failed to retrieve document: {str(e)}"
            }

        if not doc:
            return {
                "statusCode": 404,
                "error": "DocumentNotFound",
                "message": f"Could not retrieve document for {ticker}"
            }

        # Call Bedrock with specific error handling
        try:
            bedrock = boto3.client("bedrock-runtime", region_name="us-east-2")
            start = time.time()
            response = bedrock.invoke_model(
                modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{question}\n\nHere is the SEC {form_type} filing:\n\n{doc}"
                        }
                    ]
                })
            )
            latency_ms = int((time.time() - start) * 1000)

        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            print(f"Bedrock error for ticker={ticker} period={period}: {e}")
            if error_code == "ThrottlingException":
                return {
                    "statusCode": 429,
                    "error": "BedrockThrottled",
                    "message": "Bedrock throttled the request. Retry after backoff."
                }
            return {
                "statusCode": 502,
                "error": "BedrockError",
                "message": f"Bedrock API error: {str(e)}"
            }

        # Parse Bedrock response
        try:
            response_body = json.loads(response["body"].read())
            claude_response = response_body["content"][0]["text"]
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Bedrock response parse error for ticker={ticker}: {e}")
            return {
                "statusCode": 500,
                "error": "BedrockParseError",
                "message": "Failed to parse Bedrock response"
            }

        # Return structured response
        return {
            "answer": claude_response,
            "meta": {
                "model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                "input_tokens": response_body["usage"]["input_tokens"],
                "output_tokens": response_body["usage"]["output_tokens"],
                "latency_ms": latency_ms
            }
        }

    except Exception as e:
        # catch-all for anything missed
        print(f"Unhandled error for ticker={ticker} period={period} year={year}: {e}")
        return {
            "statusCode": 500,
            "error": "InternalError",
            "message": "An unexpected error occurred"
        }
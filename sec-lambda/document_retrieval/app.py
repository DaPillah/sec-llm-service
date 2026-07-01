import boto3
import json
import os
from sec_edgar import SecEdgar
import time

def lambda_handler(event, context):
    try:
        # get bucket name from environment variable
        bucket = os.environ["BUCKET_NAME"]

        # read company_tickers.json from S3
        s3 = boto3.client("s3")
        r = s3.get_object(Bucket=bucket, Key="company_tickers.json")
        raw_data = json.loads(r["Body"].read())

        # create SecEdgar object with S3 data
        se = SecEdgar(data=raw_data)

        # get and validate event fields
        ticker = event["ticker"]
        period = event["period"]
        question = event["question"]
        year = event["year"]

        # validate period
        valid_periods = ["Q1", "Q2", "Q3", "Q4", "FY"]
        if period not in valid_periods:
            return {
                "error": "ValidationError",
                "message": f"Invalid value for 'period': '{period}'. Must be one of: Q1, Q2, Q3, Q4, FY."
            }

        # map period to form_type and quarter
        period_map = {
            "Q1": ("10-Q", 1),
            "Q2": ("10-Q", 2),
            "Q3": ("10-Q", 3),
            "Q4": ("10-Q", 4),
            "FY": ("10-K", None)
        }
        form_type, quarter = period_map[period]  

        # look up company by ticker
        result = se.ticker_to_cik(ticker)  
        if not result:
            return {
                "error": "ValidationError",
                "message": f"Ticker '{ticker}' not found"
            }
        company = result[0]  
        cik = result[1]      

        # get the specific filing by year/quarter
        if form_type == "10-Q":
            filing = se.quarterly_filing(cik, year, quarter)
        else:
            filing = se.annual_filing(cik, year)

        if not filing:
            return {
                "statusCode": 404,
                "body": json.dumps(f"No {form_type} filing found for {ticker} {period} {year}")
            }

        # get actual document text using accession number
        doc = se.get_doc(company, form_type=form_type, accession=filing["accessionNumber"])
        if not doc:
            return {
                "statusCode": 404,
                "body": json.dumps(f"Could not retrieve document for {ticker}")
            }

        # send to Bedrock with latency measurement
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

        # parse Bedrock response
        response_body = json.loads(response["body"].read())
        claude_response = response_body["content"][0]["text"]

        # return structured response matching contract
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
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error: {str(e)}")
        }
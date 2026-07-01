import requests
import boto3
import os
import json

USER_AGENT = "Justin okedaramola1@gmail.com"

#lambda handler function
def lambda_handler(event, context):
    try:
        bucket = os.environ["BUCKET_NAME"]
        s3 = boto3.client('s3') 
        link = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(link, headers={"User-Agent": USER_AGENT})
        

        s3.put_object(
                Bucket=bucket,
                Key="company_tickers.json",  
                Body=response.content        
            )
            
        #return success
        return {
            "statusCode": 200,
            "body": json.dumps("Successfully uploaded company_tickers.json to S3")
        }
    
    #return error if something goes wrong
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error: {str(e)}")
        }

import boto3
import json

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

def ask_claude(question):
    bedrock = boto3.client(
        "bedrock-runtime",
        region_name="us-east-2"
    )
    
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": question
                }
            ]
        })
    )
    
    response_body = json.loads(response["body"].read())
    answer = response_body["content"][0]["text"]
    print(answer)

ask_claude("What was Apple's total net sales for Q2 2026?")
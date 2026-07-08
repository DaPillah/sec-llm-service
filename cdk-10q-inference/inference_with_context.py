import boto3
import json
import sys
import requests


from sec_edgar import SecEdgar

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
QUESTION = "What was Apple's total net sales for Q2 2026 (quarter ended March 29, 2026)?"

def get_filing_text():
    se = SecEdgar("https://www.sec.gov/files/company_tickers.json")
    return se.get_doc("Apple Inc.")

def ask_claude_with_context(question, filing_text):
    
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
                    "content": f"""Using the information below, answer the following question. Question: {question} Document:{filing_text}"""
                }
            ]
        })
    )
    
    response_body = json.loads(response["body"].read())
    answer = response_body["content"][0]["text"]
    return answer



filing_text = get_filing_text()
response = ask_claude_with_context(QUESTION, filing_text)
print(response)
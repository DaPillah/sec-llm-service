from exceptions import ValidationError
from exceptions import TickerNotFoundError
from exceptions import FilingNotFoundError
from exceptions import InvokeError
from exceptions import LambdaContractError

import time
import boto3
from botocore.exceptions import ClientError
import logging
from pipeline import validate_request, retrieve_filing, extract_filing

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
MODEL_CONTEXT_WINDOW_TOKENS = 200_000
FILING_TOKEN_BUDGET = int(MODEL_CONTEXT_WINDOW_TOKENS * 0.8)


def invoke_model(question, ticker, period, year, text):
    prompt = f"""Using only the SEC filing text provided below, answer the following question. If the answer is not contained in the filing, say so explicitly.

Question: {question}

Filing ({ticker} {period} {year}):
{text}"""

    bedrock = boto3.client("bedrock-runtime", region_name="us-east-2")

    start = time.perf_counter()
    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            inferenceConfig={"maxTokens": 1000}
        )
    except ClientError as e:
        raise InvokeError(f"Bedrock Converse API call failed: {e}")
    except Exception as e:
        raise InvokeError(f"Unexpected error calling Bedrock: {e}")

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    answer = response["output"]["message"]["content"][0]["text"]
    input_tokens = response["usage"]["inputTokens"]
    output_tokens = response["usage"]["outputTokens"]

    return {
        "answer": answer,
        "meta": {
            "model": MODEL_ID,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": elapsed_ms
        }
    }


def process_request(payload):

    logger.info(f"Received payload: {payload}")

    validate_request(payload)
    logger.info("Validation passed")

    html = retrieve_filing(payload["ticker"], payload["year"], payload["period"])
    logger.info(f"Retrieved filing HTML, length={len(html)}")

    text = extract_filing(html, FILING_TOKEN_BUDGET)
    logger.info(f"Extracted text, length={len(text)}")

    result = invoke_model(payload["question"], payload["ticker"], payload["period"], payload["year"], text)
    logger.info(f"Model invocation complete, latency_ms={result['meta']['latency_ms']}")

    return result


def core_handler(event, context):
    try:
        result = process_request(event)
        logger.info("Request completed successfully")
        return {"ok": True, "data": result}
    except ValidationError as e:
        logger.warning(f"400 {e.__class__.__name__}: {e}")
        return {"ok": False, "error": e.__class__.__name__, "message": str(e), "status": 400}
    except (TickerNotFoundError, FilingNotFoundError) as e:
        logger.warning(f"404 {e.__class__.__name__}: {e}")
        return {"ok": False, "error": e.__class__.__name__, "message": str(e), "status": 404}
    except LambdaContractError as e:
        logger.error(f"500 {e.__class__.__name__}: {e}")
        return {"ok": False, "error": e.__class__.__name__, "message": str(e), "status": 500}
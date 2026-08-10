from exceptions import ValidationError
from exceptions import TickerNotFoundError
from exceptions import FilingNotFoundError
from exceptions import InvokeError
from exceptions import ExtractError
from exceptions import LambdaContractError

from extractor import FilingTextExtractor
from sec_edgar import SecEdgar
import time
import boto3
from botocore.exceptions import ClientError
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REQUIRED_FIELDS = ["question", "ticker", "year", "period"]
VALID_PERIODS = set(["Q1", "Q2", "Q3", "Q4", "FY"])
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
MODEL_CONTEXT_WINDOW_TOKENS = 200_000
FILING_TOKEN_BUDGET = int(MODEL_CONTEXT_WINDOW_TOKENS * 0.8)

def validate_request(event):
    missing = []
    for field in REQUIRED_FIELDS:
        if field not in event:
            missing.append(field)

    if missing:
        raise ValidationError(missing_fields=missing)

    if event["period"] not in VALID_PERIODS:
        raise ValidationError(message="incorrect period inputted (must be Q1, Q2, Q3, Q4, or FY )")
    
    if not isinstance(event["year"], int):
        raise ValidationError(message="incorrect year inputted (must be an integer)")
    
    ticker = event["ticker"]
    if not ticker or not ticker.isupper():
        raise ValidationError(message="incorrect ticker inputted (must be a non-empty, all-uppercase string)")
    
    question = event["question"]
    if not question:
        raise ValidationError(message="question input is empty; write something meaningful in question")
    

def retrieve_filing(ticker, year, period):

    se = SecEdgar("https://www.sec.gov/files/company_tickers.json")
    result = se.ticker_to_cik(ticker)
    if result is None:
        raise TickerNotFoundError(f"Ticker '{ticker}' not found in SEC EDGAR company database")

    cik = result[1]

    if period == "FY":
        form_type = "10-K"
        filing_data = se.annual_filing(cik, year)
    else:
        form_type = "10-Q"
        quarter = int(period[1:])
        filing_data = se.quarterly_filing(cik, year, quarter)

    if filing_data is None:
        raise FilingNotFoundError(f"No filing found for {ticker} {period} {year}")

    html = se.get_doc(ticker, form_type, accession=filing_data["accessionNumber"])
    return html

def extract_filing(file):
    if not file:
        raise ExtractError("No filing text available to extract")

    extract = FilingTextExtractor(FILING_TOKEN_BUDGET)
    extract.feed(file)
    return extract.get_text()



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

    text = extract_filing(html)
    logger.info(f"Extracted text, length={len(text)}")

    result = invoke_model(payload["question"], payload["ticker"], payload["period"], payload["year"], text)
    logger.info(f"Model invocation complete, latency_ms={result['meta']['latency_ms']}")

    return result

def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }

def http_handler(event, context):
    logger.info(f"Received request: {event.get('rawPath')} {event.get('requestContext', {}).get('http', {}).get('method')}")

    try:
        body = json.loads(event["body"])
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        logger.warning(f"400 BadRequest: could not parse body ({e})")
        return _response(400, {"error": "BadRequest", "message": "Request body must be valid JSON"})

    try:
        result = process_request(body)
        logger.info("200 OK")
        return _response(200, result)

    except ValidationError as e:
        logger.warning(f"400 {e.__class__.__name__}: {e}")
        return _response(400, {"error": e.__class__.__name__, "message": str(e)})

    except (TickerNotFoundError, FilingNotFoundError) as e:
        logger.warning(f"404 {e.__class__.__name__}: {e}")
        return _response(404, {"error": e.__class__.__name__, "message": str(e)})

    except LambdaContractError as e:
        logger.error(f"500 {e.__class__.__name__}: {e}")
        return _response(500, {"error": e.__class__.__name__, "message": str(e)})

    except Exception as e:
        logger.error(f"500 InternalError: {e}", exc_info=True)
        return _response(500, {"error": "InternalError", "message": "An unexpected error occurred"})
    
    
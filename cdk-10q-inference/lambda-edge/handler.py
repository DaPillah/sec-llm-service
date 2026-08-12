import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REQUIRED_FIELDS = ["question", "ticker", "year", "period"]
CORE_FUNCTION_NAME = os.environ["CORE_FUNCTION_NAME"]
RAG_FUNCTION_NAME = os.environ["RAG_FUNCTION_NAME"]

lambda_client = boto3.client("lambda")


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def edge_handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    logger.info(f"Request from sub={claims.get('sub')} email={claims.get('email')}")

    try:
        payload = json.loads(event["body"])
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        logger.warning(f"400 BadRequest: could not parse body ({e})")
        return _response(400, {"error": "BadRequest", "message": "Request body must be valid JSON"})

    target_function = CORE_FUNCTION_NAME

    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        logger.warning(f"400 ValidationError: missing {missing}")
        return _response(400, {
            "error": "ValidationError",
            "message": f"Missing required fields: {', '.join(missing)}",
            "missing_fields": missing,
        })

    try:
        response = lambda_client.invoke(
            FunctionName=target_function,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode(),
        )
    except Exception as e:
        logger.error(f"502 InvokeFailed: {e}", exc_info=True)
        return _response(502, {"error": "InvokeFailed", "message": "Could not reach the inference service"})

    if "FunctionError" in response:
        detail = response["Payload"].read().decode()
        logger.error(f"502 CoreFunctionError: {detail}")
        return _response(502, {"error": "CoreFunctionError", "message": "The inference service failed"})

    
    result = json.loads(response["Payload"].read())

    if result.get("ok"):
        logger.info("200 OK")
        return _response(200, result["data"])

    status = result.get("status", 500)
    logger.warning(f"{status} {result.get('error')}: {result.get('message')}")
    return _response(status, {"error": result.get("error"), "message": result.get("message")})
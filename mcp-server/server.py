import json
import logging
import os
import sys
import argparse
import boto3
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

VALID_PERIODS = {"Q1", "Q2", "Q3", "Q4", "FY"}
LAMBDA_FUNCTION_NAME = os.environ["SEC_LAMBDA_FUNCTION_NAME"]

lambda_client = boto3.client("lambda")
mcp = FastMCP("sec-filing-server")




parser = argparse.ArgumentParser(description="SEC filing MCP server")
parser.add_argument(
    "--transport",
    default="stdio",
    choices=["stdio", "sse", "streamable-http"],
    help="Transport protocol (default: stdio)",
)
parser.add_argument("--port", type=int, default=8080, help="Port for HTTP transports")
args, _ = parser.parse_known_args()

mcp = FastMCP("sec-filing-server", port=args.port)


@mcp.tool()
def query_sec_filing(question: str, ticker: str, year: int, period: str) -> str:
    """Answer a natural-language question about a public company's SEC filing.

    Retrieves the actual 10-Q (quarterly) or 10-K (annual) filing from SEC EDGAR
    and analyzes its text to answer the question. Use this when the user asks
    about a specific company's reported financials, disclosures, risks, or
    business results for a given fiscal quarter or year.

    Args:
        question: The natural-language question to answer about the filing.
        ticker: Stock ticker symbol in uppercase, e.g. "AAPL".
        year: Four-digit fiscal year, e.g. 2026.
        period: Fiscal period: "Q1", "Q2", "Q3", "Q4", or "FY" (annual, 10-K).
    """
    if period not in VALID_PERIODS:
        logger.warning(f"Invalid period: {period}")
        raise ValueError(
            f"Invalid period '{period}'. Must be one of: Q1, Q2, Q3, Q4, FY"
        )

    payload = {
        "question": question,
        "ticker": ticker,
        "year": year,
        "period": period,
    }

    logger.info(f"Invoking {LAMBDA_FUNCTION_NAME} for {ticker} {period} {year}")

    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode(),
    )

    if "FunctionError" in response:
        detail = response["Payload"].read().decode()
        logger.error(f"Core Lambda crashed: {detail}")
        raise RuntimeError("The SEC filing service failed to process the request")

    result = json.loads(response["Payload"].read())

    if not result.get("ok"):
        message = result.get("message", "Unknown error")
        logger.warning(f"{result.get('error')}: {message}")
        raise RuntimeError(message)

    data = result["data"]
    logger.info(f"Answer returned ({data['meta']['input_tokens']} input tokens)")
    return data["answer"]


if __name__ == "__main__":
    mcp.run(transport=args.transport)
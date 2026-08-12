from exceptions import LambdaContractError
from exceptions import TickerNotFoundError
from exceptions import RetrieveError
from exceptions import FilingNotFoundError
from exceptions import ExtractError
from exceptions import InvokeError
from exceptions import ValidationError
from extractor import FilingTextExtractor
from sec_edgar import SecEdgar
import logging


logger = logging.getLogger()
REQUIRED_FIELDS = ["question", "ticker", "year", "period"]
VALID_PERIODS = set(["Q1", "Q2", "Q3", "Q4", "FY"])

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

def extract_filing(file, max_tokens):
    if not file:
        raise ExtractError("No filing text available to extract")
    extract = FilingTextExtractor(max_tokens)
    extract.feed(file)
    return extract.get_text()
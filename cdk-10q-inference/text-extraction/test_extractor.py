from extractor import FilingTextExtractor
from sec_edgar import SecEdgar


def get_filing_text(company):
    se = SecEdgar("https://www.sec.gov/files/company_tickers.json")
    return se.get_doc(company)


# --- Test filings across multiple companies ---
companies = ["Apple Inc.", "NVIDIA CORP", "Alphabet Inc."]

for company in companies:
    html = get_filing_text(company)

    extractor = FilingTextExtractor(max_tokens=10000)
    extractor.feed(html)
    text = extractor.get_text()

    print(f"--- {company} ---")
    print(f"Raw HTML chars: {len(html)}")
    print(f"Extracted chars: {len(text)}")
    print(f"Reduction: {(1 - len(text) / len(html)) * 100:.1f}%")

    # Test spot-check cover page and a financial-statement section
    print(text[:300])
    idx = text.find("Net sales")
    if idx != -1:
        print(text[max(0, idx - 100):idx + 400])
    print()

# --- Test paragraph-boundary truncation ---
print("=== Truncation: paragraph boundary ===")
extractor_small = FilingTextExtractor(max_tokens=500)
extractor_small.feed(html)  # reuse Alphabet's html from the loop above
short_text = extractor_small.get_text()
print(f"Chars: {len(short_text)}")
print(repr(short_text[-100:]))
print()

# --- Test sentence-level fallback (single oversized paragraph) ---
print("=== Truncation: sentence fallback ===")
fallback_extractor = FilingTextExtractor(max_tokens=50)
fallback_extractor.output = (
    "This is one giant sentence with no paragraph breaks at all. " * 20
)
fallback_text = fallback_extractor.get_text()
print(repr(fallback_text))
print(f"Chars: {len(fallback_text)}")
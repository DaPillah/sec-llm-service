"""
Tests for SecEdgar's fiscal year/quarter resolution (_get_quarters,
_estimate_fiscal_year, quarterly_filing, annual_filing).

Every filing fixture below (accession number, filingDate, reportDate) is a
real SEC EDGAR filing, pulled from https://data.sec.gov/submissions/CIK<cik>.json.
Expected (fiscal_year, quarter) values are each independently verifiable
against the company's own public quarterly reporting -- see the citation on
each block. This file makes no live network calls; SecEdgar._get_filings /
requests.get are mocked or bypassed everywhere.
"""
from unittest.mock import MagicMock, patch

import pytest

import sec_edgar as sec_edgar_module
from sec_edgar import SecEdgar


def make_filings(rows, fiscal_year_end):
    """rows: list of (filing_date, form, report_date, accession_num, primary_doc)"""
    filings = {
        "date": [],
        "form": [],
        "reportDate": [],
        "accessionNumber": [],
        "primaryDocument": [],
        "fiscalYearEnd": fiscal_year_end,
    }
    for filing_date, form, report_date, accession_num, primary_doc in rows:
        filings["date"].append(filing_date)
        filings["form"].append(form)
        filings["reportDate"].append(report_date)
        filings["accessionNumber"].append(accession_num)
        filings["primaryDocument"].append(primary_doc)
    return filings


@pytest.fixture
def sec():
    """A SecEdgar instance built without a real network call."""
    with patch.object(sec_edgar_module.requests, "get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: {})
        return SecEdgar("https://example.invalid/company_tickers.json")


# ---------------------------------------------------------------------------
# Real filing fixtures, one per company, chosen for diverse fiscal calendars.
# ---------------------------------------------------------------------------

# Apple Inc. (CIK 0000320193), fiscal year ends late September.
# Spans FY2022 (fully bracketed by two 10-Ks) and FY2023 (still open --
# no FY2023 10-K in this window, so resolution falls back to
# _estimate_fiscal_year). FY2023's Q2/Q3 are the exact filings that the old
# calendar-month-bucketing algorithm misclassified: Apple's 4-4-5-week fiscal
# calendar put reportDate one day into April/July instead of March/June.
# Ground truth: Apple's own quarterly earnings releases.
#   Q1 FY2022 (report 2021-12-25): reported 2022-01-27, "Apple reports first quarter results" ($123.9B revenue)
#   Q1 FY2023 (report 2022-12-31): reported 2023-02-02, revenue $117.2B
#   Q2 FY2023 (report 2023-04-01): reported 2023-05-04, revenue $94.8B
#   Q3 FY2023 (report 2023-07-01): reported 2023-08-03, revenue $81.8B
AAPL_FYE = "0926"
AAPL_ROWS = [
    ("2023-08-04", "10-Q", "2023-07-01", "0000320193-23-000077", "aapl-20230701.htm"),
    ("2023-05-05", "10-Q", "2023-04-01", "0000320193-23-000064", "aapl-20230401.htm"),
    ("2023-02-03", "10-Q", "2022-12-31", "0000320193-23-000006", "aapl-20221231.htm"),
    ("2022-10-28", "10-K", "2022-09-24", "0000320193-22-000108", "aapl-20220924.htm"),
    ("2022-07-29", "10-Q", "2022-06-25", "0000320193-22-000070", "aapl-20220625.htm"),
    ("2022-04-29", "10-Q", "2022-03-26", "0000320193-22-000059", "aapl-20220326.htm"),
    ("2022-01-28", "10-Q", "2021-12-25", "0000320193-22-000007", "aapl-20211225.htm"),
    ("2021-10-29", "10-K", "2021-09-25", "0000320193-21-000105", "aapl-20210925.htm"),
]

# NVIDIA Corp. (CIK 0001045810), fiscal year ends late January.
# FY2025 fully bracketed; FY2026 Q1 left open (fallback + "+1 bump" together).
# Ground truth: NVIDIA's own quarterly earnings releases.
#   Q1 FY2025 (report 2024-04-28): reported 2024-05-22, revenue $26.0B
#   Q1 FY2026 (report 2025-04-27): reported 2025-05-28, revenue $44.1B
NVDA_FYE = "0131"
NVDA_ROWS = [
    ("2025-05-28", "10-Q", "2025-04-27", "0001045810-25-000116", "nvda-20250427.htm"),
    ("2025-02-26", "10-K", "2025-01-26", "0001045810-25-000023", "nvda-20250126.htm"),
    ("2024-11-20", "10-Q", "2024-10-27", "0001045810-24-000316", "nvda-20241027.htm"),
    ("2024-08-28", "10-Q", "2024-07-28", "0001045810-24-000264", "nvda-20240728.htm"),
    ("2024-05-29", "10-Q", "2024-04-28", "0001045810-24-000124", "nvda-20240428.htm"),
    ("2024-02-21", "10-K", "2024-01-28", "0001045810-24-000029", "nvda-20240128.htm"),
]

# Walmart Inc. (CIK 0000104169), fiscal year ends January 31 -- adjacent to
# the calendar-year boundary, and to NVIDIA's own January fiscal year end,
# so this cross-validates the "+1 bump" against a second, unrelated company.
# Ground truth: Walmart's own quarterly earnings releases.
#   Q1 FY2025 (report 2024-04-30): reported 2024-05-16
WMT_FYE = "0131"
WMT_ROWS = [
    ("2025-03-14", "10-K", "2025-01-31", "0000104169-25-000021", "wmt-20250131.htm"),
    ("2024-12-06", "10-Q", "2024-10-31", "0000104169-24-000178", "wmt-20241031.htm"),
    ("2024-08-30", "10-Q", "2024-07-31", "0000104169-24-000141", "wmt-20240731.htm"),
    ("2024-06-07", "10-Q", "2024-04-30", "0000104169-24-000105", "wmt-20240430.htm"),
    ("2024-03-15", "10-K", "2024-01-31", "0000104169-24-000056", "wmt-20240131.htm"),
]

# Alphabet Inc. (CIK 0001652044), fiscal year end December 31 -- calendar
# year. fiscal_start == 1 here, which must structurally disable the "+1
# bump" entirely (weakness #3's core concern). Includes an open Q1 with no
# following 10-K, so the fallback path is exercised for a Dec-FYE company too.
GOOGL_FYE = "1231"
GOOGL_ROWS = [
    ("2026-04-30", "10-Q", "2026-03-31", "0001652044-26-000048", "goog-20260331.htm"),
    ("2025-02-05", "10-K", "2024-12-31", "0001652044-25-000014", "goog-20241231.htm"),
    ("2024-10-30", "10-Q", "2024-09-30", "0001652044-24-000118", "goog-20240930.htm"),
    ("2024-07-24", "10-Q", "2024-06-30", "0001652044-24-000079", "goog-20240630.htm"),
    ("2024-04-26", "10-Q", "2024-03-31", "0001652044-24-000053", "goog-20240331.htm"),
    ("2024-01-31", "10-K", "2023-12-31", "0001652044-24-000022", "goog-20231231.htm"),
]

# Microsoft Corp. (CIK 0000789019), fiscal year ends June 30 -- a fiscal
# start month (July) with no special-cased boundary behavior of its own.
MSFT_FYE = "0630"
MSFT_ROWS = [
    ("2024-07-30", "10-K", "2024-06-30", "0000950170-24-087843", "msft-20240630.htm"),
    ("2024-04-25", "10-Q", "2024-03-31", "0000950170-24-048288", "msft-20240331.htm"),
    ("2024-01-30", "10-Q", "2023-12-31", "0000950170-24-008814", "msft-20231231.htm"),
    ("2023-10-24", "10-Q", "2023-09-30", "0000950170-23-054855", "msft-20230930.htm"),
]

# Costco Wholesale Corp. (CIK 0000909832), a genuine 52/53-week fiscal year:
# quarter-end is "the Sunday nearest a target date", so reportDate shifts
# around from year to year (Nov 23 vs Nov 24, Feb 15 vs Feb 16, ...) instead
# of landing on a fixed calendar date. Ground truth cross-checked directly
# against SEC's XBRL company-facts fy/fp fields for these exact accessions
# (data.sec.gov/api/xbrl/companyfacts/CIK0000909832.json, dei:EntityCommonStockSharesOutstanding).
COST_FYE = "0830"
COST_ROWS = [
    ("2025-10-08", "10-K", "2025-08-31", "0000909832-25-000101", "cost-20250831.htm"),
    ("2025-06-05", "10-Q", "2025-05-11", "0000909832-25-000033", "cost-20250511.htm"),
    ("2025-03-13", "10-Q", "2025-02-16", "0000909832-25-000015", "cost-20250216.htm"),
    ("2024-12-19", "10-Q", "2024-11-24", "0000909832-24-000079", "cost-20241124.htm"),
    ("2024-10-09", "10-K", "2024-09-01", "0000909832-24-000049", "cost-20240901.htm"),
]

# Johnson & Johnson (CIK 0000200406) uses a genuine 52-week fiscal year
# ending "the Sunday nearest December 31" -- depending on the year, that
# lands in either late December or the first few days of January. Its own
# 10-K cover page (dei:DocumentFiscalYearFocus) confirms the report with
# reportDate 2022-01-02 is actually fiscal year 2021, not 2022. This is a
# known, accepted limitation (see the comment in annual_filing for why)
# rather than something the code corrects for.
JNJ_FYE = "0103"
JNJ_ROWS = [
    ("2023-02-16", "10-K", "2023-01-01", "0000200406-23-000016", "jnj-20230101.htm"),
    ("2022-02-17", "10-K", "2022-01-02", "0000200406-22-000022", "jnj-20220102.htm"),
]


# ---------------------------------------------------------------------------
# _estimate_fiscal_year: the calendar-month fallback used only when no later
# 10-K exists yet to bracket a 10-Q against.
# ---------------------------------------------------------------------------

def test_estimate_fiscal_year_december_fye_never_bumps(sec):
    # fiscal_month=12 -> fiscal_start=1 -> "fiscal_start > 1" is always False,
    # so a Dec-FYE (calendar year) company must never get the "+1" bump.
    for month in range(1, 13):
        report_date = f"2025-{month:02d}-15"
        assert sec._estimate_fiscal_year(report_date, 12) == "2025"


def test_estimate_fiscal_year_january_fye_boundary(sec):
    # fiscal_month=1 -> fiscal_start=2 (Feb). January itself is the LAST
    # month of the fiscal year and must stay in the current calendar year;
    # February is the FIRST month of the next fiscal year and must bump.
    assert sec._estimate_fiscal_year("2025-01-15", 1) == "2025"
    assert sec._estimate_fiscal_year("2025-02-01", 1) == "2026"


def test_estimate_fiscal_year_generic_bump(sec):
    # fiscal_month=9 (Apple's) -> fiscal_start=10 (Oct).
    assert sec._estimate_fiscal_year("2025-09-30", 9) == "2025"   # Sept: still old FY
    assert sec._estimate_fiscal_year("2025-10-01", 9) == "2026"   # Oct: new FY starts


# ---------------------------------------------------------------------------
# _get_quarters: positional (not calendar-month) quarter assignment.
# ---------------------------------------------------------------------------

def test_get_quarters_apple_bracketed_fiscal_year(sec):
    filings = make_filings(AAPL_ROWS, AAPL_FYE)
    quarters = sec._get_quarters(filings)

    assert quarters["0000320193-22-000007"] == ("2022", 1)
    assert quarters["0000320193-22-000059"] == ("2022", 2)
    assert quarters["0000320193-22-000070"] == ("2022", 3)


def test_get_quarters_apple_445_calendar_regression(sec):
    """Regression test: report dates 2023-04-01 and 2023-07-01 spill one day
    into the "wrong" calendar month under Apple's 4-4-5-week fiscal
    calendar. The old month-bucketing algorithm classified these as Q3/Q4;
    they are actually Q2/Q3 (Apple's own Aug 2023 earnings release covers
    "the third quarter" for the period ended July 1, 2023)."""
    filings = make_filings(AAPL_ROWS, AAPL_FYE)
    quarters = sec._get_quarters(filings)

    assert quarters["0000320193-23-000006"] == ("2023", 1)
    assert quarters["0000320193-23-000064"] == ("2023", 2)
    assert quarters["0000320193-23-000077"] == ("2023", 3)


def test_get_quarters_nvidia_bracketed_and_fallback(sec):
    filings = make_filings(NVDA_ROWS, NVDA_FYE)
    quarters = sec._get_quarters(filings)

    assert quarters["0001045810-24-000124"] == ("2025", 1)
    assert quarters["0001045810-24-000264"] == ("2025", 2)
    assert quarters["0001045810-24-000316"] == ("2025", 3)
    # no FY2026 10-K in this fixture yet -> resolved via the fallback path
    assert quarters["0001045810-25-000116"] == ("2026", 1)


def test_get_quarters_walmart_january_boundary(sec):
    filings = make_filings(WMT_ROWS, WMT_FYE)
    quarters = sec._get_quarters(filings)

    assert quarters["0000104169-24-000105"] == ("2025", 1)
    assert quarters["0000104169-24-000141"] == ("2025", 2)
    assert quarters["0000104169-24-000178"] == ("2025", 3)


def test_get_quarters_alphabet_calendar_year_never_bumps(sec):
    filings = make_filings(GOOGL_ROWS, GOOGL_FYE)
    quarters = sec._get_quarters(filings)

    assert quarters["0001652044-24-000053"] == ("2024", 1)
    assert quarters["0001652044-24-000079"] == ("2024", 2)
    assert quarters["0001652044-24-000118"] == ("2024", 3)
    # open quarter, resolved via fallback -- must stay 2026, never bump to 2027
    assert quarters["0001652044-26-000048"] == ("2026", 1)


def test_get_quarters_microsoft_june_fye(sec):
    filings = make_filings(MSFT_ROWS, MSFT_FYE)
    quarters = sec._get_quarters(filings)

    assert quarters["0000950170-23-054855"] == ("2024", 1)
    assert quarters["0000950170-24-008814"] == ("2024", 2)
    assert quarters["0000950170-24-048288"] == ("2024", 3)


def test_get_quarters_costco_52_53_week_fiscal_year(sec):
    """Costco's quarter-end date shifts by a day or two year over year
    (Nov 23 vs Nov 24, Feb 15 vs Feb 16, ...) because it's a genuine
    52/53-week fiscal calendar. Positional counting is indifferent to this
    -- unlike calendar-month bucketing, it never has to guess which month a
    shifting date "belongs" to."""
    filings = make_filings(COST_ROWS, COST_FYE)
    quarters = sec._get_quarters(filings)

    assert quarters["0000909832-24-000079"] == ("2025", 1)
    assert quarters["0000909832-25-000015"] == ("2025", 2)
    assert quarters["0000909832-25-000033"] == ("2025", 3)


def test_annual_filing_jnj_boundary_known_limitation(sec, monkeypatch):
    """Documents the known, accepted limitation described in annual_filing:
    JNJ's fiscal year end can land in early January instead of late
    December, and reportDate's raw calendar year mislabels those. The
    January-landing 10-K here (reportDate 2022-01-02) is JNJ's real fiscal
    2021 10-K, but annual_filing(cik, 2021) won't find it -- it's only
    reachable, incorrectly, as "2022"."""
    filings = make_filings(JNJ_ROWS, JNJ_FYE)
    monkeypatch.setattr(sec, "_get_filings", lambda cik: filings)

    assert sec.annual_filing("0000200406", 2021) is None
    result = sec.annual_filing("0000200406", 2022)
    assert result["accessionNumber"] == "0000200406-22-000022"


# ---------------------------------------------------------------------------
# quarterly_filing / annual_filing: end-to-end lookup by (year, quarter).
# _get_filings is bypassed (it's covered separately below) so these tests
# isolate the resolution + selection logic.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "rows, fye, cik, year, quarter, expected_accession",
    [
        (AAPL_ROWS, AAPL_FYE, "0000320193", 2022, 1, "0000320193-22-000007"),
        (AAPL_ROWS, AAPL_FYE, "0000320193", 2023, 2, "0000320193-23-000064"),
        (AAPL_ROWS, AAPL_FYE, "0000320193", 2023, 3, "0000320193-23-000077"),
        (NVDA_ROWS, NVDA_FYE, "0001045810", 2025, 3, "0001045810-24-000316"),
        (GOOGL_ROWS, GOOGL_FYE, "0001652044", 2024, 2, "0001652044-24-000079"),
        (COST_ROWS, COST_FYE, "0000909832", 2025, 2, "0000909832-25-000015"),
    ],
)
def test_quarterly_filing_returns_correct_accession(
    sec, monkeypatch, rows, fye, cik, year, quarter, expected_accession
):
    filings = make_filings(rows, fye)
    monkeypatch.setattr(sec, "_get_filings", lambda cik: filings)

    result = sec.quarterly_filing(cik, year, quarter)

    assert result is not None
    assert result["accessionNumber"] == expected_accession
    assert result["cik"] == cik


def test_quarterly_filing_no_match_returns_none(sec, monkeypatch):
    filings = make_filings(AAPL_ROWS, AAPL_FYE)
    monkeypatch.setattr(sec, "_get_filings", lambda cik: filings)

    assert sec.quarterly_filing("0000320193", 2019, 1) is None


@pytest.mark.parametrize(
    "rows, fye, cik, year, expected_accession",
    [
        (AAPL_ROWS, AAPL_FYE, "0000320193", 2021, "0000320193-21-000105"),
        (AAPL_ROWS, AAPL_FYE, "0000320193", 2022, "0000320193-22-000108"),
        (NVDA_ROWS, NVDA_FYE, "0001045810", 2024, "0001045810-24-000029"),
        (WMT_ROWS, WMT_FYE, "0000104169", 2025, "0000104169-25-000021"),
        (COST_ROWS, COST_FYE, "0000909832", 2025, "0000909832-25-000101"),
    ],
)
def test_annual_filing_returns_correct_accession(
    sec, monkeypatch, rows, fye, cik, year, expected_accession
):
    filings = make_filings(rows, fye)
    monkeypatch.setattr(sec, "_get_filings", lambda cik: filings)

    result = sec.annual_filing(cik, year)

    assert result is not None
    assert result["accessionNumber"] == expected_accession


def test_annual_filing_no_match_returns_none(sec, monkeypatch):
    filings = make_filings(AAPL_ROWS, AAPL_FYE)
    monkeypatch.setattr(sec, "_get_filings", lambda cik: filings)

    assert sec.annual_filing("0000320193", 2019) is None


# ---------------------------------------------------------------------------
# _get_filings: confirms reportDate is actually extracted from the raw SEC
# submissions response shape (it previously wasn't fetched at all).
# ---------------------------------------------------------------------------

def test_get_filings_extracts_report_date(sec):
    raw_response = {
        "fiscalYearEnd": "0926",
        "filings": {
            "recent": {
                "form": ["10-Q"],
                "filingDate": ["2026-01-30"],
                "reportDate": ["2025-12-27"],
                "accessionNumber": ["0000320193-26-000006"],
                "primaryDocument": ["aapl-20251227.htm"],
                "primaryDocDescription": ["10-Q"],
            }
        },
    }
    with patch.object(sec_edgar_module.requests, "get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: raw_response)
        filings = sec._get_filings("0000320193")

    assert filings["reportDate"] == ["2025-12-27"]

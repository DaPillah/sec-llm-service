import requests
from datetime import datetime

# This project only covers standard 10-K/10-Q filers. Companies that change
# their fiscal year end file a 10-KT (transition-period annual report)
# instead of a 10-K around the change -- that's out of scope here, so a
# 10-KT is simply not recognized as an annual report at all.
class SecEdgar():
    def __init__(self, file):
        self.namedict = {}
        self.tickerdict = {}
        self.headers = {"user-agent" : "okedaramola1@gmail.com"}

        r = requests.get(file, headers=self.headers)
        self.data = r.json()
        self.cik_json_to_dict()


    def cik_json_to_dict(self):
        self.namedict = {}
        self.tickerdict = {}
        for company in self.data.values():
            name = company['title']
            cik = str(company['cik_str']).zfill(10)
            ticker = company['ticker']

            self.namedict[name.lower()] = (name, cik, ticker)
            self.tickerdict[ticker.lower()] = (name, cik, ticker)
        
    def recent_filing(self, company):
        '''searching through either name or tik'''
        result = self.name_to_cik(company)
        if not result:
            result = self.ticker_to_cik(company)
        if not result:  
            print(f"Company '{company}' not found")
            return None

        cik = result[1]
        filings = self._get_filings(cik)

        return (filings, cik)

    

    def get_doc(self, company, form_type="10-Q", accession=None): #works for any form type
        if accession:
            if not hasattr(self, 'filings_dict') or accession not in self.filings_dict:
                self._get_latest_filing(company, form_type)
            data = self.filings_dict[accession]
        else:
            data = self._get_latest_filing(company, form_type)

        if not data:
            return None

        cik = data["cik"].lstrip("0")
        accession_num = data["accessionNumber"].replace("-", "")
        doc = data["primaryDocument"]

        link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_num}/{doc}"
        r = requests.get(link, headers=self.headers)
        return r.text
    

    def annual_filing(self, cik, year):
        # reportDate is the fiscal-period-end date itself, so its calendar
        # year is the fiscal year label directly.
        #
        # Known limitation: a company whose fiscal year is a genuine
        # 52/53-week calendar anchored right at the Dec31/Jan1 boundary
        # (e.g. Johnson & Johnson, CIK 0000200406) can have its fiscal
        # year end land in early January some years instead of late
        # December, which this simple year-of-reportDate rule mislabels by
        # one year. This is accepted rather than fixed: correctly
        # resolving it requires fetching each such filing's own
        # authoritative fiscal-year label from SEC (no way to tell, from
        # fiscalYearEnd alone, whether a given January-ending filer needs
        # the adjustment -- NVIDIA and Walmart also end in January but
        # never need it), which was judged not worth the added complexity
        # for how rare this pattern is.
        filings = self._get_filings(cik)

        for i, date in enumerate(filings["date"]):
            if filings["form"][i] == "10-K":
                report_date = filings["reportDate"][i]
                if report_date and report_date.split("-")[0] == str(year):
                    accession_num = filings["accessionNumber"][i]
                    doc = filings["primaryDocument"][i]

                    return {
                            "date": date,
                            "accessionNumber": accession_num,
                            "primaryDocument": doc,
                            "cik": cik
                    }

        print(f"No 10-K found for year {year}")
        return None


    def quarterly_filing(self, cik, year, quarter):
        filings = self._get_filings(cik)
        quarter_map = self._get_quarters(filings)

        for i, date in enumerate(filings["date"]):
            if filings["form"][i] == "10-Q":
                accession_num = filings["accessionNumber"][i]
                if quarter_map.get(accession_num) == (str(year), quarter):
                    doc = filings["primaryDocument"][i]
                    return {
                            "date": date,
                            "accessionNumber": accession_num,
                            "primaryDocument": doc,
                            "cik": cik
                    }

        print(f"No 10-Q found for year {year} quarter {quarter}")
        return None

    def get_fiscal_year_end(self, cik):
        """Returns the month and day a company's fiscal year ends"""
        filings = self._get_filings(cik)
        fiscal_year_end = filings["fiscalYearEnd"]
        month = int(str(fiscal_year_end)[:2])
        day = int(str(fiscal_year_end)[2:])
        return month, day

    def name_to_cik(self, name):
        return self.namedict.get(name.lower())
    
    def ticker_to_cik(self, tick):
        return self.tickerdict.get(tick.lower())
    
    ###Private Helpers###
    def _get_filings(self, cik):
        link = f"https://data.sec.gov/submissions/CIK{cik}.json"
        response = requests.get(link, headers=self.headers)
        data = response.json()
        return {
            "form": data["filings"]["recent"]["form"],
            "date": data["filings"]["recent"]["filingDate"],
            "reportDate": data["filings"]["recent"]["reportDate"],
            "accessionNumber": data["filings"]["recent"]["accessionNumber"],
            "primaryDocument": data["filings"]["recent"]["primaryDocument"],
            "primaryDocDescription": data["filings"]["recent"]["primaryDocDescription"],
            "fiscalYearEnd": data.get("fiscalYearEnd", "1231"),
        }
    
    def _get_latest_filing(self, company, form_type="10-Q"):
        result = self.recent_filing(company)
        if not result:
            return None

        filings, cik = result

        self.filings_dict = {}
        for i, form in enumerate(filings["form"]):
            if form == form_type:  
                accession = filings["accessionNumber"][i]
                no_dash_accession = accession.replace("-", "")
                self.filings_dict[accession] = {
                    "date": filings["date"][i],
                    "accessionNumber": no_dash_accession,
                    "primaryDocument": filings["primaryDocument"][i],
                    "primaryDocDescription": filings["primaryDocDescription"][i],
                    "cik": cik
                }

        if not self.filings_dict:
            print(f"No {form_type} filings found for {company}")
            return None

        latest_accession = max(self.filings_dict, key=lambda x: self.filings_dict[x]["date"]) #gets latest file
        return self.filings_dict[latest_accession]




    def _get_quarters(self, filings):
        """Maps each 10-Q accession number to (fiscal_year, quarter).

        Quarter number is assigned by position (1st/2nd/3rd 10-Q filed since
        the prior 10-K) rather than bucketing reportDate by calendar month.
        Month-bucketing breaks for filers on a 4-4-5-week fiscal calendar
        (e.g. Apple, NVIDIA), whose quarter-end date occasionally spills a
        day into the "wrong" calendar month relative to fiscal_month.
        """
        fiscal_month = int(str(filings["fiscalYearEnd"])[:2])

        ten_qs = []
        ten_k_years = []
        for i in range(len(filings["form"])):
            report_date = filings["reportDate"][i]
            if not report_date:
                continue
            if filings["form"][i] == "10-Q":
                ten_qs.append((report_date, filings["accessionNumber"][i]))
            elif filings["form"][i] == "10-K":
                ten_k_years.append((report_date, report_date.split("-")[0]))
        ten_k_years.sort(key=lambda entry: entry[0])

        groups = {}
        for report_date, accession_num in ten_qs:
            # a 10-Q belongs to the fiscal year of the next 10-K filed after it
            next_fiscal_year = next(
                (fy for report, fy in ten_k_years if report > report_date), None
            )
            fiscal_year = next_fiscal_year or self._estimate_fiscal_year(report_date, fiscal_month)
            groups.setdefault(fiscal_year, []).append((report_date, accession_num))

        quarter_map = {}
        for fiscal_year, entries in groups.items():
            for position, (_, accession_num) in enumerate(sorted(entries), start=1):
                quarter_map[accession_num] = (fiscal_year, position)
        return quarter_map

    def _estimate_fiscal_year(self, report_date, fiscal_month):
        """Calendar-month fallback for a 10-Q in the current, still-open
        fiscal year, where no later 10-K exists yet to anchor against."""
        parsed_date = datetime.strptime(report_date, "%Y-%m-%d")
        fiscal_start = (fiscal_month % 12) + 1

        if fiscal_start > 1 and parsed_date.month >= fiscal_start:
            return str(parsed_date.year + 1)
        return str(parsed_date.year)


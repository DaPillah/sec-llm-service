import requests
from bs4 import BeautifulSoup

class SecEdgar():
    def __init__(self, file=None, data=None):
        self.namedict = {}
        self.tickerdict = {}
        self.headers = {"user-agent" : "okedaramola1@gmail.com"}

        if data:
            self.data = data  # use pre-fetched data directly
        elif file:
            r = requests.get(file, headers=self.headers)
            self.data = r.json()
        else:
            raise ValueError("Either file URL or data must be provided")
        
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
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.get_text(separator='\n', strip=True) #removes useless HTML formatting
    

    def annual_filing(self, cik, year):
        ''' NOTE: year filtering uses filing date year, not fiscal year
                  Future improvement: detect fiscal year end and adjust year matching accordingly for companies with 
                  non-standard fiscal years (e.g. Apple's fiscal year ends in September)'''
        filings = self._get_filings(cik)

        for i, date in enumerate(filings["date"]):
            if filings["form"][i] == "10-K":
                f_year = filings["date"][i].split("-")[0]
                if str(year) == f_year:
                    accession_num = filings["accessionNumber"][i]
                    doc = filings["primaryDocument"][i]

                    return {
                            "date": date,
                            "accessionNumber": accession_num.replace,
                            "primaryDocument": doc,
                            "cik": cik
                    } 
        
        print(f"No 10-K found for year {year}")
        return None
            

    def quarterly_filing(self, cik, year, quarter):
        filings = self._get_filings(cik)
        fiscal_year_end = filings["fiscalYearEnd"]
        fiscal_month = int(str(fiscal_year_end)[:2])  # get company's filing ending month

        for i, date in enumerate(filings["date"]):
            if filings["form"][i] == "10-Q":
                f_year, f_quarter = self._get_quarter(date, fiscal_month) # convert to year/quarter system
                if (f_year, f_quarter) == (str(year), quarter):
                    accession_num = filings["accessionNumber"][i]
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


    def _get_quarter(self, date, fiscal_month):
        #converts the given filing date to company's year/quarter system
        parts = date.split("-")
        year = parts[0]
        month = int(parts[1])

        # calculate which month the fiscal year starts
        fiscal_start = (fiscal_month % 12) + 1

        # dynamically build quarters based on fiscal year start
        quarters = {}
        for q in range(1, 5):
            months = set()
            for m in range(3):
                month_num = ((fiscal_start - 1 + (q-1)*3 + m) % 12) + 1
                months.add(month_num)
            quarters[q] = months

        for quarter, months in quarters.items():
            if month in months:
                return (year, quarter)
        return None
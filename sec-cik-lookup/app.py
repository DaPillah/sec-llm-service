import requests

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
        #searching through either name or tik
        result = self.name_to_cik(company)
        if not result:
            result = self.ticker_to_cik(company)
        if not result:  
            print(f"Company '{company}' not found")
            return None

        cik = result[1]
        filings = self._get_filings(cik)

        return (filings, cik)

    def get_latest_10q(self, company):    
        result = self.recent_filing(company)
        if not result:
            return None

        #unpack tuple
        filings, cik = result

        #building Q-10 dictionary
        self.q10 = {}
        for i, form in enumerate(filings["form"]):
            if form == "10-Q":
                accession = filings["accessionNumber"][i]
                no_dash_accesssion = accession.replace("-", "")  
                self.q10[accession] = {
                                  "date":filings["date"][i],
                                  "accessionNumber": no_dash_accesssion,
                                  "primaryDocument":filings["primaryDocument"][i],
                                  "primaryDocDescription":filings["primaryDocDescription"][i],
                                  "cik": cik
                }

        if not self.q10:
            print(f"No 10-Q filings found for {company}")
            return None

        latest_accession = max(self.q10, key=lambda x: self.q10[x]["date"])
        return self.q10[latest_accession]
    

    def get_10q_doc(self, company, accession=None):
        if accession:
            if not hasattr(self, 'q10') or accession not in self.q10:
                self.get_latest_10q(company) #make sure q10 is populated
            data = self.q10[accession]
        else:
            data = self.get_latest_10q(company)

        cik = data["cik"].lstrip("0") #remove leading 0's
        accession_num = data["accessionNumber"]
        doc = data["primaryDocument"]

        link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_num}/{doc}"
        r = requests.get(link, headers=self.headers)

        return r.text
    
    def annual_filing(self, cik, year):
        filings = self._get_filings(cik)

        for i, date in enumerate(filings["date"]):
            if filings["form"][i] == "10-K":
                f_year = filings["date"][i].split("-")[0]
                if str(year) == f_year:
                    accession_num = filings["accessionNumber"][i]
                    doc = filings["primaryDocument"][i]

                    return {
                            "date": date,
                            "accessionNumber": accession_num.replace("-", ""),
                            "primaryDocument": doc,
                            "cik": cik
                    } 
        
        print(f"No 10-K found for year {year}")
        return None
            
        

    def quarterly_filing(self, cik, year, quarter):
        filings = self._get_filings(cik)

        for i, date in enumerate(filings["date"]):
            if filings["form"][i] == "10-Q":
                f_year, f_quarter = self._get_quarter(date)
                if (f_year, f_quarter) == (str(year), quarter):
                    accession_num = filings["accessionNumber"][i]
                    doc = filings["primaryDocument"][i]
                    return {
                            "date": date,
                            "accessionNumber": accession_num.replace("-", ""),
                            "primaryDocument": doc,
                            "cik": cik
                    }
        
        print(f"No 10-Q found for year {year} quarter {quarter}")
        return None

    def _get_filings(self, cik):
        link = f"https://data.sec.gov/submissions/CIK{cik}.json"
        response = requests.get(link, headers=self.headers)
        data = response.json()
        return {
            "form": data["filings"]["recent"]["form"],
            "date": data["filings"]["recent"]["filingDate"],
            "accessionNumber": data["filings"]["recent"]["accessionNumber"],
            "primaryDocument": data["filings"]["recent"]["primaryDocument"],
            "primaryDocDescription": data["filings"]["recent"]["primaryDocDescription"]
        }
        
    def _get_quarter(self, date):
        parts = date.split("-")
        year = parts[0]
        month = int(parts[1])

        quarters = { 
                    1: {1, 2, 3},
                     2: {4, 5, 6},
                     3: {7, 8, 9},
                     4: {10, 11, 12},
        }

        for quarter, months in quarters.items():
            if month in months:
                return (year, quarter)
        return None


    def name_to_cik(self, name):
        return self.namedict.get(name.lower())
    
    def ticker_to_cik(self, tick):
        return self.tickerdict.get(tick.lower())

        
        

se = SecEdgar("https://www.sec.gov/files/company_tickers.json")

# CIK Lookups
se.name_to_cik("Apple Inc.")          # name → CIK
se.ticker_to_cik("AAPL")             # ticker → CIK

# Filing Retrieval
se.recent_filing("Apple Inc.")        # all recent filings
se.get_latest_10q("Apple Inc.")       # latest 10-Q metadata
se.get_10q_doc("Apple Inc.")          # latest 10-Q document content

# Specific Filings by Date
se.annual_filing("0000320193", 2023)      # 10-K for specific year
se.quarterly_filing("0000320193", 2023, 2) # 10-Q for specific year + quarter
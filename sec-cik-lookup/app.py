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
        if not result:  # ← add this
            print(f"Company '{company}' not found")
            return None

        cik = result[1]

        link = f"https://data.sec.gov/submissions/CIK{cik}.json"


        response = requests.get(link, headers=self.headers)
 

        self.submission_data = response.json()

        self.filings = {"form":self.submission_data["filings"]["recent"]["form"],
                        "date":self.submission_data["filings"]["recent"]["filingDate"],
                        "accessionNumber":self.submission_data["filings"]["recent"]["accessionNumber"] 
                        }
        return self.filings

    def get_latest_10q(self, company):    
        self.recent_filing(company)

        #building Q-10 dictionary
        self.q10 = {}
        for i, form in enumerate(self.filings["form"]):
            if form == "10-Q":
                accession = self.filings["accessionNumber"][i]
                self.q10[accession] = {
                                  "date":self.filings["date"][i],
                                  "accessionNumber": accession
                                 }

        latest_accession = max(self.q10, key=lambda x: self.q10[x]["date"])
        return self.q10[latest_accession]

        
        


    def name_to_cik(self, name):
        return self.namedict.get(name.lower())
    
    def ticker_to_cik(self, tick):
        return self.tickerdict.get(tick.lower())

        
        

se = SecEdgar("https://www.sec.gov/files/company_tickers.json")
print(se.get_latest_10q("Apple Inc."))
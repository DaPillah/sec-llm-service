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
                        "accessionNumber":self.submission_data["filings"]["recent"]["accessionNumber"],
                        "primaryDocument": self.submission_data["filings"]["recent"]["primaryDocument"], 
                        "primaryDocDescription":self.submission_data["filings"]["recent"]["primaryDocDescription"], 
        }
        return (self.filings, cik)

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

        
        


    def name_to_cik(self, name):
        return self.namedict.get(name.lower())
    
    def ticker_to_cik(self, tick):
        return self.tickerdict.get(tick.lower())

        
        

se = SecEdgar("https://www.sec.gov/files/company_tickers.json")
print(se.get_10q_doc("Apple Inc."))
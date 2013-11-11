import json
from pyquery import PyQuery as pq
import requests
import codecs
from xml.dom.minidom import parseString
from bs4 import BeautifulSoup
import csv
from datetime import datetime

class MintConnection():
    def __init__(self, email, password, debugging=False, write_text=False):
        self.email = email
        self.password = password
        self.debugging = debugging
        self.write_text = write_text
        self.token = None
        self.reported_last_date = None

    def login(self):
        self.session = requests.Session()
        data = {"username": self.email, "password": self.password, "task": "L", "nextPage": ""}
        if not self.debugging:
            response = self.session.post("https://wwws.mint.com/loginUserSubmit.xevent", data=data).text
            if self.write_text:
                with open("debug_login.html","w") as f:
                    f.write(response.encode("UTF-8"))
        else:
            with codecs.open('debug_login.html', encoding='utf-8') as f:
                response = f.read()

        if "javascript-token" not in response.lower():
            raise Exception("Mint.com login failed")

        # 2: Grab token.
        d = pq(response.encode("utf-8"))
        self.token = d("input#javascript-token")[0].value

    def get_accounts(self):
        if self.token == None or self.session == None:
            self.login()
        # 3. Issue service request.
        request_id = "115485" # magic number? random number?
        data = {"input": json.dumps([
            {"args": {
                "types": [
                    #"BANK",
                    #"CREDIT",
                    "INVESTMENT",
                    #"LOAN",
                    #"MORTGAGE",
                    #"OTHER_PROPERTY",
                    #"REAL_ESTATE",
                    #"VEHICLE",
                    #"UNCLASSIFIED"
                ]
            },
            "id": request_id,
            "service": "MintAccountService",
            "task": "getAccountsSorted"}
        ])}

        if not self.debugging:
            response = self.session.post("https://wwws.mint.com/bundledServiceController.xevent?token="+self.token,
                                         data=data).text
            if self.write_text:
                with open("debug_accounts.html","w") as f:
                    f.write(response)
        else:
            with open("debug_accounts.html","r") as f:
                response = f.read()
        try:
            response = json.loads(response)["response"]
            accounts = response[request_id]["response"]
        except ValueError:
            raise Exception("Connection with Mint failed. JSON object could not be decoded. " +
                            "This could be due to incorrect username and password")
        return accounts

    def get_investment_account_Ids(self):
        return [el["accountId"] for el in self.get_accounts()]

    def get_holdings(self, account_nr):
        if self.session == None:
            self.login()
        if not self.debugging:
            response2 = self.session.get("https://wwws.mint.com/investment.event?accountId=3570177").text
            if self.write_text:
                with open("debug_investment.html","w") as f:
                    f.write(response2)
        else:
            with open("debug_investment.html","r") as f:
                response2 = f.read()

        soup = BeautifulSoup(response2)
        p = soup.select('input[name="json-import-node"]')[0]["value"]
        p = p.lstrip("json = ")
        p = p.rstrip(";")
        json_object = json.loads(p)
        descriptions = [el["description"] for el in json_object[str(account_nr)]["holdings"].values()]
        values = [el["value"] for el in json_object[str(account_nr)]["holdings"].values()]
        symbols = [el["symbol"] for el in json_object[str(account_nr)]["holdings"].values()]
        holdings = []
        self.reported_last_date = json_object["lastDate"]
        for idx, description in enumerate(descriptions):
            this_holding = Holding(symbol=symbols[idx],
                                   description=description,
                                   value=values[idx])
            holdings.append(this_holding)
        return holdings

class Holding():
    asset_allocation_library = {}

    def __init__(self, symbol, description, value):
        if Holding.asset_allocation_library == {}:
            self.read_asset_allocation_library()
        self.description = description
        if self.description=='CASH':
            self.symbol = u'CASH'
        else:
            self.symbol = symbol
        self.value = value
        try:
            self.allocation_class = Holding.asset_allocation_library[self.symbol]
        except KeyError:
            raise Exception("Don't know symbol '%s'. Please add to asset allocation library." % self.symbol)

    @staticmethod
    def read_asset_allocation_library():
        Holding.asset_allocation_library = {}
        with open('asset_allocation_library.csv', 'rU') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                if row[0]!="":
                    Holding.asset_allocation_library[row[0]] = row[1]

class Portfolio():
    asset_allocation_model = {}

    def __init__(self):
        if Portfolio.asset_allocation_model == {}:
            self.read_asset_allocation_model()
        self.holdings = []
        self.last_updated = ""

    @staticmethod
    def read_asset_allocation_model():
        Portfolio.asset_allocation_model = {}
        with open('asset_allocation_model.csv', 'rU') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                if row[0] != "":
                    Portfolio.asset_allocation_model[row[0]] = {"fraction": float(row[1]),
                                                                "default": row[2]}

    def add_holdings(self, holdings):
        self.holdings.extend(holdings)

    def get_symbols(self):
        return [el.symbol for el in self.holdings]

    def total_value(self):
        return sum(el.value for el in self.holdings)

    def value_by_asset(self):
        value_by_asset_dict = {}
        total_value = 0
        for asset_type in self.asset_allocation_model.keys():
            asset_value = sum(holding.value for holding in self.holdings if holding.allocation_class == asset_type)
            total_value += asset_value
            value_by_asset_dict[asset_type] = asset_value
        if total_value != self.total_value():
            raise Exception("Not all asset allocation types are represented in the asset allocation model")
        return value_by_asset_dict

    def value_by_symbol(self):
        value_by_symbol_dict = {}
        total_value = 0
        for symbol in self.get_symbols():
            asset_value = sum(holding.value for holding in self.holdings if holding.symbol == symbol)
            total_value += asset_value
            value_by_symbol_dict[symbol] = asset_value
        if total_value != self.total_value():
            raise Exception("Not all asset allocation types are represented in the asset allocation model")
        return value_by_symbol_dict

    def percentage_by_asset(self):
        value_by_asset = self.value_by_asset()
        total_value = self.total_value()
        percentage_by_asset = {k: v/total_value for (k, v) in value_by_asset.items()}
        allocation_sum = sum(v for v in percentage_by_asset.values())
        if allocation_sum != 1.0:
            raise Exception("Asset allocation does not sum up to 1")
        return percentage_by_asset

    def percentage_deviation_by_asset(self):
        percentage_by_asset = self.percentage_by_asset()
        m = Portfolio.asset_allocation_model
        deviation_by_asset = {k: m[k]["fraction"] - v for (k, v) in percentage_by_asset.items()}
        allocation_sum = sum(v for v in deviation_by_asset.values())
        if allocation_sum > 0.0001:
            raise Exception("Deviation of asset allocation does not sum up to 0")
        return deviation_by_asset

    def rebalance_portfolio(self):
        portfolio_deviation = self.percentage_deviation_by_asset()
        total_value = self.total_value()
        assets_touched = [(abs(v), k) for (k,v) in portfolio_deviation.items() if
                          abs(v) > 0.05 or abs(v * total_value) > 2000]

        assets_touched = [k for (v,k) in sorted(assets_touched, reverse=True)]

        for k in assets_touched:
            v = portfolio_deviation[k]
            if v < 0:
                print "SELL %.2f$ of %s" % (abs(v * total_value), k)
            else:
                print "BUY %.2f$ of %s" % (v * total_value, k)

    def consolidate_holdings(self):
        all_symbols = self.get_symbols()
        unique_symbols = set(all_symbols)
        new_holdings = []
        for unique_symbol in unique_symbols:
            indices = [idx for idx, el in enumerate(all_symbols) if el == unique_symbol]
            first_holding = self.holdings[indices[0]]
            if len(indices)==1:
                new_holdings.append(first_holding)
            else:
                sum_value = sum(self.holdings[el].value for el in indices)
                agg_holding = Holding(symbol=first_holding.symbol,
                                      description=first_holding.description,
                                      value=sum_value)
                new_holdings.append(agg_holding)
        self.holdings = new_holdings

    def write_to_log(self):
        fixed_header = ["Date", "Last Updated", "Total Value"]
        try:
            with open('allocation_log.csv', 'rU') as logfile:
                header = logfile.readline().strip('\n').split(",")
        except IOError:
            header = fixed_header + Portfolio.asset_allocation_model.keys()
            header_string = ",".join(header)
            with open('allocation_log.csv','w') as logfile:
                logfile.write(header_string + "\n")
        value_by_asset = self.value_by_asset()
        value_list = [value_by_asset[el] for el in header if not el in fixed_header]
        value_list = [datetime.now(),  self.last_updated, self.total_value()] + value_list
        value_string = ",".join([str(el) for el in value_list])
        with open('allocation_log.csv','a') as csvfile:
            csvfile.write(value_string + '\n')
import ally
import os
import requests
from requests_oauthlib import OAuth1
from xml.etree import ElementTree

os.environ["ALLY_CONSUMER_KEY"]="your_key"
os.environ["ALLY_CONSUMER_SECRET"]="your_secret"
os.environ["ALLY_OAUTH_TOKEN"]="your_token"
os.environ["ALLY_OAUTH_SECRET"]="your_oauth_secret"
os.environ['ALLY_ACCOUNT_NBR']="your_acct_no"

class AllyTrader(object):
	def __init__(self):
		self.KEY=os.environ["ALLY_CONSUMER_KEY"]
		self.SECRET=os.environ["ALLY_CONSUMER_SECRET"]
		self.TOKEN=os.environ["ALLY_OAUTH_TOKEN"]
		self.OATH_SECRET=os.environ["ALLY_OAUTH_SECRET"]
		self.ACCT=os.environ['ALLY_ACCOUNT_NBR']
		self.a = ally.Ally()

	def get_option_info(self,ticker,date,daterel,strk,strkrel):
		# Takes ticker, date, date relation (eq,gt,lt)-equal, greater/less than,
		#strike price, and strk price relation
		#Returns desired information about the option
		url = 'https://api.tradeking.com/v1/market/options/search.xml?symbol='\
		+ticker+'&query=xdate-'+daterel+'%3A'+date+'%20AND%20strikeprice-'+strkrel+'%3A'+strk
		auth = OAuth1(self.KEY,self.SECRET,self.TOKEN,self.OATH_SECRET)
		resp = requests.get(url, auth=auth)
		if resp.status_code != 200:
		    # This means something went wrong.
			raise Exception(resp.status_code)
		root = ElementTree.fromstring(resp.content)
		optioninfo=[]
		for quote in root[1]:
			qt = {}
			qt['bid'] = quote.find('bid').text
			qt['ask'] = quote.find('ask').text
			qt['last'] = quote.find('last').text
			qt['vol'] = quote.find('vl').text
			exp_date = quote.find('xdate').text
			qt['exp_date'] = exp_date[:4]+'/'+exp_date[4:6]+'/'+exp_date[6:]
			qt['str_price'] = quote.find('strikeprice').text
			optioninfo.append(qt)
		return optioninfo

	def get_acc_history(self):
		trans_history =self.a.account_history(
			account=self.ACCT,
			type="all",
		    range="current_week"
		)
		return trans_history

	def market_buy(self,ticker,q):
		# moved to another self.executed dict
		market_buy = ally.order.Order(
		     timespan   = ally.order.Timespan('day'),
		     type = ally.order.Buy(),
		     price = ally.order.Market(),
		     instrument = ally.instrument.Equity(ticker),
		     quantity = ally.order.Quantity(q)
		 )
	def market_sell(self,ticker,q):

		market_sell = ally.order.Order(
		    timespan = ally.order.Timespan('day'),
		    type = ally.order.Sell(),
		    price = ally.order.Market(),
		    instrument = ally.instrument.Equity(ticker),
		    quantity = ally.order.Quantity(q)
		)

	def execute_order(self,id):

		exec_status = self.a.submit_order(
		    # specify order created, see above
		    order=market_sell,
		    # Can dry-run using preview=True, defaults to True
		    # Must specify preview=False to actually execute
		    preview=False,
		)

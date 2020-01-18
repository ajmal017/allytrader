from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import datetime
from allytrader import AllyTrader
import time
import sys
import talib
import os

# All ints passed as ints not strings

class Strat(object):
    def __init__(self):
        self.key = 'your_alphavantage_key_here'
        self.ts = TimeSeries(self.key, output_format='pandas')
        self.ti = TechIndicators(self.key,output_format='pandas')
        self.secinfo = {}

    def dt64_to_dt(self,date):
        # Takes in the numpy dt64 and returns a dt object
        timestamp = ((date - np.datetime64('1970-01-01T00:00:00'))
                     / np.timedelta64(1, 's'))
        return datetime.datetime.utcfromtimestamp(timestamp)

    def get_daily_ts(self,ticker):
        # Gets 5min intraday from alpha vantage, unless has an existing updated one stored within last 6.5h
        # That way, will still be updated if I try on the last minute of any trading day if was called at its start
        if self.secinfo.get(ticker) and self.is_up_to_date(ticker,390):
            return self.secinfo[ticker][0]
        else:
            data,inf = self.ts.get_daily(symbol=ticker,outputsize='full')
            # Store data in dict to avoid API calls if possible, include timestamp to know when update needed
            data.index = data.index.map(self.dt64_to_dt)
            self.secinfo[ticker] = (data, datetime.datetime.now())
            return data

    def get_intraday_ts(self,ticker,interv):
        # Gets 5min intraday from alpha vantage, unless has an existing updated one stored
        strint = str(interv)
        if self.secinfo.get(ticker+strint+'min') and self.is_up_to_date(ticker+strint+'min',5):
            return self.secinfo[ticker+strint+'min'][0]
        else:
            data,inf = self.ts.get_intraday(symbol=ticker,interval=strint+'min',outputsize='full')
            # Store data in dict to avoid API calls if possible, include timestamp to know when update needed
            data.index = data.index.map(self.dt64_to_dt)
            self.secinfo[ticker+strint+'min'] = (data, datetime.datetime.now())
            return data

    def get_ts_for_day(self,ticker,interv,offset=0):
        data = self.get_intraday_ts(ticker,interv)
        tod = datetime.datetime.now().date()-datetime.timedelta(days=offset)
        todaydata = data[data.index.date==tod]
        return todaydata

    def get_curr_price_chng(self,ticker,offset=0):
        # Returns the percent price change since beginning of day
        if self.secinfo.get(ticker+'price_change') and self.is_up_to_date(ticker+'price_change',5):
            return self.secinfo[ticker+'price_change'][0]

        else:
        # Alpha vantage doesn't have a way to select just current day's price, so
        # Get 5 min intraday and select first entry, calculate % difference
            todaydata = self.get_ts_for_day(ticker,5,offset)
            price_change = (todaydata['4. close'].values[-1]-todaydata['4. close'].values[0])/todaydata['4. close'].values[0]
            self.secinfo[ticker+'price_change'] = (price_change, datetime.datetime.now())
            return price_change

    def get_quote(self,ticker):
        # Gets quote from alpha vantage, unless has an existing updated one stored
        if self.secinfo.get(ticker+'quote') and self.is_up_to_date(ticker+'quote',5):
            return self.secinfo[ticker+'quote'][0]
        else:
            data = self.ts.get_quote_endpoint(symbol=ticker)
            # Store data in dict to avoid API calls if possible, include timestamp to know when update needed
            self.secinfo[ticker+'quote'] = (data, datetime.datetime.now())
            return data

    def get_curr_price_vol(self,ticker):
        # returns current price and volume of stock

        data = self.get_quote(ticker)
        price = float(data[0]['05. price'].values[0])
        vol = float(data[0]['06. volume'].values[0])
        self.secinfo[ticker+'price_vol'] = (price,vol,datetime.datetime.now())

        return (price,vol)

    def is_up_to_date(self,info,recency):
        # Takes type of info (ticker+price_change,quote,price_vol,etc), and recency in minutes
        # Checks whether data has been updated in the last 5 min
        return datetime.datetime.now()-self.secinfo[info][-1]<=datetime.timedelta(minutes =recency)


    def has_bodyless_sticks(self,ticker,offset=0):
        # Checks if and how many bodyless sticks the stock has since day start
        if self.secinfo.get(ticker+'bodyless') and self.is_up_to_date(ticker+'bodyless',5):
            return self.secinfo[ticker+'bodyless'][0]

        else:
        # Alpha vantage doesn't have a way to select just current day's price, so
        # Get 5 min intraday and select first entry, calculate % difference
            todaydata = self.get_ts_for_day(ticker,5,offset=offset)
            body = (todaydata['4. close'].values-todaydata['1. open'].values)/todaydata['1. open'].values
            noofbodyless = len([b for b in body if abs(b)<1.0e-4])
            too_many_bodyless = noofbodyless>=2
            self.secinfo[ticker+'bodyless'] = (too_many_bodyless, datetime.datetime.now())
            return too_many_bodyless

    def get_intra_sma(self,ticker,interv,period, plot=False,offset=0):
        # Takes ticker, period, and interval as strings, and returns the daily sma as pd series for noof offset days ago
        strint,strper=str(interv),str(period)
        tod = (datetime.datetime.now()-datetime.timedelta(days=offset)).date()
        strtod = tod.strftime("%Y/%m/%d")
        # Check if updated data already exists in dict
        if self.secinfo.get(ticker+strint+'m_sma_'+strper+'p_'+strtod) and \
        self.is_up_to_date(ticker+strint+'m_sma_'+strper+'p_'+strtod,5):
            return self.secinfo[ticker+strint+'m_sma_'+strper+'p_'+strtod][0]

        else:
            close = self.get_intraday_ts(ticker,interv)['4. close']
            sma = talib.SMA(close, timeperiod=period)
            todsma = sma[sma.index.date==tod]
            smadf = pd.DataFrame({'SMA':todsma})
            self.secinfo[ticker+strint+'m_sma_'+strper+'p_'+strtod]=(smadf,datetime.datetime.now())
        if plot:
            plt.figure(figsize=(20,6))
            plt.plot(todaydata)
            plt.show()

        else:
            pass
        return smadf

    def get_daily_sma(self,ticker, period=20,plot=False):
        # Takes ticker, interval, period, plot, returns the sma as pd series for longer period
        strper=str(period)
        # Check if updated data exists in dict
        if self.secinfo.get(ticker+'daily_sma_'+strper+'p') and \
        self.is_up_to_date(ticker+'daily_sma_'+strper+'p',5):
            return self.secinfo[ticker+'daily_sma_'+strper+'p'][0]

        else:
            close = self.get_daily_ts(ticker)['4. close']
            sma = talib.SMA(close, timeperiod=period)
            self.secinfo[ticker+'daily_sma_'+strper+'p']=(sma,datetime.datetime.now())

        if plot:
            plt.figure(figsize=(20,6))
            plt.plot(sma)
            plt.show()
        return sma

    def check_sticks_sma(self,ticker,tolerance=80,mov=True,offset=0):
        # Checks if tolerance% of sticks for given day are above/below the SMA (depending on mov:1up,0down)
        # True if fe. 80% sticks are above sma on an upward trend
        data = self.get_ts_for_day(ticker,5,offset)
        sma = self.get_intra_sma(ticker,5,8)
        datalen = len(data)
        newdata = pd.concat([data,sma],axis = 1)
        if mov:
            sticks = newdata['4. close']-newdata['SMA']
            return len(sticks[sticks>0])>=0.01*tolerance*datalen
        else:
            sticks = newdata['SMA']-newdata['1. open']
            return len(sticks[sticks>0])>=0.01*tolerance*datalen

    def check_noof_plbcks(self, ticker,tolerance=80,mov=True,offset=0):
        # Returns true if pullbacks account for fe. 1-tolerance% or less of all 5min movements
        data = self.get_ts_for_day(ticker,5,offset)
        datalen = len(data)
        if mov:
            mvmnt = data['4. close']-data['1. open']
            return len(mvmnt[mvmnt>0])>=0.01*tolerance*datalen
        else:
            mvmnt = data['1. open']-newdata['4. close']
            return len(mvmnt[mvmnt>0])>=0.01*tolerance*datalen

    def check_sizeof_plbcks(self,ticker,tolerance=3,mov=True,offset=0):
        #Returns true if each pullback ends no lower than the hit tolerance periods ago
        data = self.get_ts_for_day(ticker,5,offset)
        datalen = len(data)
        if mov:
            myser = data['1. open'].shift(periods=tolerance)
            data=data.iloc[tolerance:].assign(before=myser.iloc[tolerance:])
            checkdata = data[data['4. close']<data['before']]
            return len(checkdata)==0
        else:
            myser = data['1. open'].shift(periods=tolerance)
            data=data.iloc[tolerance:].assign(before=myser.iloc[tolerance:])
            checkdata = data[(data['4. close']>data['before'])]
            return len(checkdata)==0

    def get_opt_info(self):
    # Expand to pass as params the ticker, date, other things that interest us
        atr = AllyTrader()
        res = atr.get_option_info()
        return res

    def analyze_stonks(self,l,offset=0):
        # Takes a list of stock tickers, prints dict of strategy stats for each,
        # The count of 5 is due to alpha vantage hits limitations
        dict = {}
        counter= 0
        
        for s in l:
            if counter != 5:
                try:
                    d={'prc_chng':st.get_curr_price_chng(s,offset=offset),\
                    'bodyless_sticks':st.has_bodyless_sticks(s,offset=offset),\
                    'sticks_sma':st.check_sticks_sma(s,offset=offset),\
                    'noof_plbcks':st.check_noof_plbcks(s,offset=offset),\
                    'sizeof_plbcks':st.check_sizeof_plbcks(s,offset=offset)}
                    print("Got stats for", s)
                    dict[s] = d
                    counter += 1
                except:
                    print("could not get data for ",s)
                    print(sys.exc_info()[0])
            else:
                print("sleeping")
                time.sleep(60)
                counter = 0

        for k,v in zip(dict.keys(),dict.values()):
            print(k,":",v,'\n')



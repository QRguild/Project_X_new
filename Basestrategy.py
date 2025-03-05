import os
import sys

# sys.path.append(os.path.dirname(os.getcwd()))

from Data2 import Data
from kiteconnect import KiteConnect
import logging
from kiteconnect import KiteTicker
from Bardata import BarData
from datetime import datetime, timedelta, date, time
import csv
import pandas as pd
import numpy as np
import math


class BaseStrategy(Data):
    
    with open('/Users/sushrutkagde/Documents/ZerodhaAPI/api_key.txt','r') as file:
        api_key=file.read()
    with open('/Users/sushrutkagde/Documents/ZerodhaAPI/api_secret.txt','r') as file:
        api_secret=file.read()
    
    def __init__(self,exchange):
        super().__init__(exchange)
        self.kite = KiteConnect(api_key=BaseStrategy.api_key)
        self.diff = []
        return
    
    def write_order(self,symbol,type,price,quantity):
        # write the order to a csv file for reference
        # current_folder = os.getcwd()
        # order = [{'variety':'regular','exchange':self.exchange,'tradingsymbol':trading_symbol,'transaction_type':'BUY','quantity':quantity,'order_type':'LIMIT','price':order_price,'product':'NRML'}]
        # margin = self.kite.order_margins(order)
        margin=0
        folder_path = "/Users/sushrutkagde/Documents/ZerodhaAPI/options_data/data/"+str(date.today())+"/"
        file = "Traded_orders.csv"
        file_path = os.path.join(folder_path,file)

        file_exist = os.path.isfile(file_path)
        with open(file_path,mode='a',newline='') as file:
            writer = csv.writer(file)

             # Write header only if file does not exist
            if not file_exist:
                 writer.writerow(['exchange_timestamp','trading_symbol','order_type','Price','quantity','margin_required'])

             # Write the data rows
            writer.writerow([self.curr_tick[-1].exchange_timestamp,symbol,type,price,quantity,margin])

        print("placed order")
        return
    
    def place_buy_order(self,trading_symbol,quantity):
        # get the best price from the order book
        order_price = self.get_best_price(trading_symbol=trading_symbol,transaction_type='sell')
        print("got best price")

        # place order to kite 
        if self.curr_time >= datetime.now().replace(hour=14,minute=30,second=0):
            self.kite.place_order(variety='regular',exchange=self.exchange,tradingsymbol=trading_symbol,transaction_type='BUY',quantity=quantity,order_type='LIMIT',price=order_price,product='NRML')

        # write the order to a csv file for reference
        self.write_order(trading_symbol,"BUY",order_price,quantity)
        return
    
    def place_sell_order(self,trading_symbol,quantity):
        # get the best price from the order book
        order_price = self.get_best_price(trading_symbol=trading_symbol,transaction_type='buy')

        # order = [{'variety':'regular','exchange':self.exchange,'tradingsymbol':trading_symbol,'transaction_type':'SELL','quantity':quantity,'order_type':'LIMIT','price':order_price,'product':'NRML'}]
        # margin = self.kite.order_margins(order)
        margin = 0 

        # place order to kite
        if self.curr_time >= datetime.now().replace(hour=14,minute=30,second=0):
            self.kite.place_order(variety='regular',exchange=self.exchange,tradingsymbol=trading_symbol,transaction_type='SELL',quantity=quantity,order_type='LIMIT',price=order_price,product='NRML')

        # write the order to a csv file for reference
        self.write_order(trading_symbol,"SELL",order_price,quantity)
        return
    
    def get_atm_strike(self):
        index_value = self.get_index_value()
        # function to be made using the vwap script
        strikes_list = list(self.syn_future.keys())
        strike_gap = (strikes_list[1]-strikes_list[0])
        atm_strike = round(index_value/strike_gap)*strike_gap
        print("got atm strike")
        return atm_strike
 
    def get_best_price(self,trading_symbol : str,transaction_type : str):
        # strike_list = [self.strike_ltp[symbol].strike for symbol in self.strike_ltp if self.strike_ltp[symbol].trading_symbol==trading_symbol]
        # # strike = self.trading_symbol.loc[self.trading_symbol['tradingsymbol']==trading_symbol,'strike'].values[0]
        # strike = strike_list[0]

        # self.position_strike = strike
        # option = str(strike)+trading_symbol[-2:]
        # best_price = self.strike_ltp[option].depth[transaction_type][0]['price']
        best_price = self.option_contracts[trading_symbol].depth[transaction_type][0]['price']
        return best_price
    
    def get_trading_symbol(self,strike):
        trading_symbol_list = [self.strike_ltp[symbol].trading_symbol for symbol in self.strike_ltp if self.strike_ltp[symbol].strike==strike]
        return trading_symbol_list
    
    def get_index_value(self):
        value_index = ''
        while value_index=='':
            with open('/Users/sushrutkagde/Documents/ZerodhaAPI/indices/index.txt','r') as file:
                value_index=file.read()
                try:
                    value_index = float(value_index)
                except:
                    value_index=''
        return value_index
    
    def order_status(self,order_id):
        return
    
    def order_history(self):
        return

    def get_pnl(self):
        folder_path = "/Users/sushrutkagde/Documents/ZerodhaAPI/options_data/data/"+str(date.today())+"/"
        file = "Traded_orders.csv"
        file_path = os.path.join(folder_path,file)
        pnl={}
        df = pd.read_csv(file_path)
        df['pnl'] = 0

        for trades in df.iterrows():
            if trades[1]['trading_symbol'] not in pnl.keys():
                pnl[trades[1]['trading_symbol']] = 0
            if trades[1]['order_type']=='BUY':
                pnl[trades[1]['trading_symbol']] -= trades[1]['quantity']*trades[1]['Price']
            else:
                pnl[trades[1]['trading_symbol']] += trades[1]['quantity']*trades[1]['Price']
            df.loc[trades[0],'pnl'] = pnl[trades[1]['trading_symbol']]

        df.to_csv(file_path,index=False)
        
        if self.is_long:
            for option in self.traded_symbol:
                if option[-2:]=='CE':
                    pnl[option] += (self.option_contracts[option].synthetic_price - self.option_contracts[option].strike)
                elif self.option_contracts[option].synthetic_price > self.option_contracts[option].strike:
                    pnl[option] += (self.option_contracts[option].strike - self.option_contracts[option].synthetic_price)

        if self.is_short:
            for option in self.traded_symbol:
                if option[-2:]=='PE':
                    pnl[option] += (self.option_contracts[option].strike - self.option_contracts[option].synthetic_price)
                elif self.option_contracts[option].synthetic_price < self.option_contracts[option].strike:
                    pnl[option] += (self.option_contracts[option].synthetic_price-self.option_contracts[option].strike)

        print("PnL for today:",sum(pnl.values()))
        for key in pnl.keys():
            print(key,":",pnl[key])
        
        df.to_csv(file_path,index=False)

        return

    def generate_session(self,request_token):
        self.kite.generate_session(request_token=request_token,api_secret=BaseStrategy.api_secret)
        return

    def login_url(self):
        print(self.kite.login_url())
        request_token = input('Enter request token: ')
        self.generate_session(request_token)
        return 

    


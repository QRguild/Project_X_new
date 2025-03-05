from kiteconnect import KiteConnect
import logging
from kiteconnect import KiteTicker
from Bardata import BarData
from datetime import datetime, timedelta, date
import os
import csv
import pandas as pd
import numpy as np
import math

class Data:
    with open('/Users/sushrutkagde/Documents/Trading platform/api_key.txt','r') as file:
        api_key=file.read()
    with open('/Users/sushrutkagde/Documents/Trading platform/access_token.txt','r') as file:
        access_token=file.read()
    
    def __init__(self,config : dict) -> None:
        self.index_symbol = config['trading_symbol']
        self.exchange = config['exchange']
        self.instrument_token = []
        self.kite = KiteConnect(api_key=Data.api_key)
        self.instruments = pd.DataFrame(self.kite.instruments(exchange=self.exchange)) 
        with open('/Users/sushrutkagde/Documents/Trading platform/strategy_new/index.txt','r') as file:
            self.currect_price = float(file.read())
        self.strike_gap = config['strike_gap']*5
        self.update_instrument()
        self.kws = KiteTicker(api_key=Data.api_key,access_token=Data.access_token)
        self.options_contracts = {}         # stores the option contracts
        self.synthetic_future = {}         
        return

    def update_instrument(self):
        expiry = self.instruments.loc[self.instruments['name']==self.index_symbol,'expiry']
        expiry = sorted(expiry)
        weekly = expiry[0]
        self.instrument_token = self.instruments.loc[(self.instruments['name']==self.index_symbol)&(self.instruments['expiry']==weekly)&((self.instruments['strike']>self.currect_price-self.strike_gap)&(self.instruments['strike']<=self.currect_price+self.strike_gap)),'instrument_token'].tolist()
        return
    
    def set_instrument(self):
        
        return
    
    def write_diff_data(self,diff,avg_future_price,timestamp):
        
        return

    
    def syn_future(self,strike):
        # calculates the synthetic future price using put call parity
        contract_list = [bar for bar in self.options_contracts.values() if bar.strike==strike]
        if len(contract_list)<2:
            return None
        
        call_option = next((bar for bar in contract_list if bar.trading_symbol[-2:]=='CE'),None)
        put_option = next((bar for bar in contract_list if bar.trading_symbol[-2:] == 'PE'), None)
        
        print(call_option.trading_symbol,put_option.trading_symbol)
        # C-P+S
        self.synthetic_future[strike] = strike + call_option.last_price - put_option.last_price
        return self.synthetic_future[strike]


    def get_vwap(self):
        
        return 

    def on_tick(self,ws,ticks):
        
        self.curr_time = datetime.now()
    
        close = ticks[0]
        print(close)

        trading_symbol = self.trading_symbol.loc[self.trading_symbol['instrument_token']==close['instrument_token'],'tradingsymbol'].values
        close['trading_symbol'] = trading_symbol[0]
        strike = self.trading_symbol.loc[self.trading_symbol['instrument_token']==close['instrument_token'],'strike'].values
        close['strike'] = strike[0]
        bar = BarData(**close)
        self.option_contracts[bar.trading_symbol] = bar
        
        return
    
    def on_connect(self,ws,response):
        ws.subscribe(self.instrument_token)
        ws.set_mode(ws.MODE_FULL,self.instrument_token)
        return
    
    def on_close(self,ws,code,reason):
        ws.stop()
        return
    
    def webstream(self):
        self.kws.on_ticks = self.on_tick
        self.kws.on_connect = self.on_connect
        self.kws.on_close = self.on_close
        return
    
    def connect(self):
        self.kws.connect()
        return
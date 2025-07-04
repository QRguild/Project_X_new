import sys
import os
sys.path.append(os.path.abspath(".."))
from datetime import datetime,date
import logging
from threading import *
import threading
from queue import Queue
from kiteconnect import KiteTicker, KiteConnect
import time
from collections import defaultdict, deque
import csv
import os
import pandas as pd
from Bardata import BarData
import dotenv
from dotenv import load_dotenv,set_key
import numpy as np

load_dotenv()

class oi_strategy(Thread):

    api_key = os.getenv('api_key')
    access_token = os.getenv('access_token')

    def __init__(self,config):
        self.kws = KiteTicker(api_key=oi_strategy.api_key,access_token=oi_strategy.access_token)
        self.kite = KiteConnect(api_key=oi_strategy.api_key)
        print(oi_strategy.api_key,oi_strategy.access_token)


        self.ticks_queue = Queue()
        self.instrument_tokens=[]
        self.call_tokens = []
        self.put_tokens = []
        self.update_instrument_tokens(config['symbol'])
        self.current_ticks = {token:None for token in self.instrument_tokens}
        self.lock = threading.Lock()
        self.oi_ratio = []
        self.minute_wise_oi_ratio = []
        self.current_oi_ratio = 0

        self.log_file = str(date.today())+'_oi_ratio_log.txt'
        self.current_ticks = {}
        self.position = False

        self.moving_average_oi_ratio = []

        return
    
    def login(self):
        print(self.kite.login_url())
        request_token = input("Enter the request token: ")
        data = self.kite.generate_session(request_token, api_secret=os.getenv('api_secret'))
        return
    
    def on_connect(self,ws,response):
        print("WebSocket connected!")
        ws.subscribe(self.instrument_tokens)
        ws.set_mode(ws.MODE_FULL, self.instrument_tokens)
        return
    
    def on_ticks(self,ws,ticks):
        # for tick in ticks:
        self.ticks_queue.put(ticks)
        return
    
    def calculate_oi_ratio(self):
        call_oi=0
        put_oi=0
        # for i in tick:
        #     self.current_ticks[i['instrument_token']] = i
        #     if i['instrument_token'] in self.call_tokens:
        #         call_oi+=i['oi']
        #     elif i['instrument_token'] in self.put_tokens:
        #         put_oi+=i['oi']
        for t in self.call_tokens:
            call_oi+=self.current_ticks[t]['oi']
        for t in self.put_tokens:
            put_oi+=self.current_ticks[t]['oi']

        oi_ratio = -call_oi/put_oi
        return oi_ratio,call_oi,put_oi
    
    def process_ticks(self):
        while True:
            try:
                tick = self.ticks_queue.get(timeout=1)
                with self.lock:
                    # print(tick)
                    for t in tick:
                        self.current_ticks[t['instrument_token']] = t

                    # ticks also stored through this function
                    self.current_oi_ratio,coi,poi = self.calculate_oi_ratio()
                    # print(self.current_oi_ratio)
                    self.oi_ratio.append(self.current_oi_ratio)
                    ma = np.mean(self.oi_ratio[-200:])
                    self.moving_average_oi_ratio.append(ma)

                    if len(self.minute_wise_oi_ratio)==0:
                        self.minute_wise_oi_ratio.append(ma)
                    
                    with open(self.log_file,'a') as file:
                        file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{str(self.current_oi_ratio)},{str(coi)},{str(poi)}\n")

            except Exception as e:
                print(f"Error processing tick: {e}")
        return
    

    def calculate_oi_change(self):
        prev_oi = self.minute_wise_oi_ratio[-2]
        current_oi = self.minute_wise_oi_ratio[-1]
        change = (current_oi - prev_oi)/prev_oi * 100
        print(change)
        return change
    
    def check_conditions(self):
        change = self.calculate_oi_change()
        with open('oi_ratio_change_log.txt','a') as file:
            file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{str(change)}\n")
        if change > 0.05 and self.position:
            try:
                self.place_order(long=False)
                self.position = True
            except Exception as e:
                # continue
                print(e)
        elif change < -0.05 and self.position:
            try:
                self.place_order(long=True)
                self.position = True
            except Exception as e:
                # continue
                print(e)

        return
    
    def place_order(self,long):
        atm_strike = self.current_ticks[256265]['last_price']

        nearest_strike = self.instruments['strike'].iloc[(self.instruments['strike'] - atm_strike).abs().argmin()]
        filtered = self.instruments[(self.instruments['strike'] == nearest_strike)&(self.instruments['name']=='NIFTY')]
        expiries = sorted(filtered['expiry'].unique())
        expiry = expiries[0]
        final = filtered[filtered['expiry'] == expiry]
        trading_symbols = final['tradingsymbol'].values
        tokens = final['instrument_token'].values
        for contract in final.itertuples():
            if long:
                if contract.tradingsymbol[-2:]=='CE':
                    best_price = self.current_ticks[contract.instrument_token]['depth']['sell'][0]['price']
                    self.kite.place_order(variety='regular',exchange='NFO',tradingsymbol=contract.tradingsymbol,transaction_type='BUY',quantity=contract.lot_size,order_type='LIMIT',price=best_price,product='NRML')
                    with open('orders_oi_strategy.txt','a') as file:
                        file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{str(contract.tradingsymbol)},BUY,{contract.lot_size}\n")
                else:
                    best_price = self.current_ticks[contract.instrument_token]['depth']['buy'][0]['price']
                    self.kite.place_order(variety='regular',exchange='NFO',tradingsymbol=contract.tradingsymbol,transaction_type='SELL',quantity=contract.lot_size,order_type='LIMIT',price=best_price,product='NRML')
                    with open('orders_oi_strategy.txt','a') as file:
                        file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{str(contract.tradingsymbol)},SELL,{contract.lot_size}\n")
            
            else:
                if contract.tradingsymbol[-2:]=='CE':
                    best_price = self.current_ticks[contract.instrument_token]['depth']['buy'][0]['price']
                    self.kite.place_order(variety='regular',exchange='NFO',tradingsymbol=contract.tradingsymbol,transaction_type='SELL',quantity=contract.lot_size,order_type='LIMIT',price=best_price,product='NRML')
                    with open('orders_oi_strategy.txt','a') as file:
                        file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{str(contract.tradingsymbol)},SELL,{contract.lot_size}\n")
                else:
                    best_price = self.current_ticks[contract.instrument_token]['depth']['sell'][0]['price']
                    self.kite.place_order(variety='regular',exchange='NFO',tradingsymbol=contract.tradingsymbol,transaction_type='BUY',quantity=contract.lot_size,order_type='LIMIT',price=best_price,product='NRML')
                    with open('orders_oi_strategy.txt','a') as file:
                        file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{str(contract.tradingsymbol)},BUY,{contract.lot_size}\n")
        
        return
    
    def update_instrument_tokens(self,symbol):
        self.instruments = pd.DataFrame(self.kite.instruments('NFO'))
        filtered_instruments = self.instruments[self.instruments['name'] == symbol]

        call_tokens = filtered_instruments[filtered_instruments['instrument_type'] == 'CE']
        put_tokens = filtered_instruments[filtered_instruments['instrument_type'] == 'PE']
        expiries = sorted(call_tokens['expiry'].unique())
        expiry_codes = {i:expiries[i] for i in range(4)}

        print(expiry_codes)

        for expiry_code in expiry_codes:
            tkn = call_tokens[call_tokens['expiry'] == expiry_codes[expiry_code]]['instrument_token'].values
            for token in tkn:
                self.call_tokens.append(int(token))

        for expiry_code in expiry_codes:
            tkn = put_tokens[put_tokens['expiry'] == expiry_codes[expiry_code]]['instrument_token'].values
            for token in tkn:
                self.put_tokens.append(int(token))

        self.instrument_tokens = self.call_tokens + self.put_tokens + [256265]

        # unfiltered_instruments = instruments[instruments['name'] == symbol]['instrument_token'].values
        # for token in unfiltered_instruments:
        #     self.instrument_tokens.append(int(token))
        # print(self.instrument_tokens)
        return

    def on_close(self,ws,code,reason):
        ws.stop()
        return

    def start(self):
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect
        self.kws.on_close = self.on_close

        tick_thread = threading.Thread(target=self.process_ticks)
        tick_thread.daemon = True
        tick_thread.start()


        self.kws.connect(threaded=True)
        
        try:
            while True:
                time.sleep(60)
                self.minute_wise_oi_ratio.append(self.moving_average_oi_ratio[-1])
                self.check_conditions()
        except KeyboardInterrupt:
            self.kws.close()
            tick_thread.join()
            print("WebSocket connection closed.")
            
    

        return



sample={'symbol':'NIFTY'}
strategy = oi_strategy(sample)
# strategy.login()
strategy.start()
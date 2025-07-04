from datetime import datetime,date
import logging
import threading
from queue import Queue
from kiteconnect import KiteTicker, KiteConnect
import time
from datetime import date, datetime, timedelta
from collections import defaultdict, deque
import csv
import os
import pandas as pd
from Bardata import BarData
import dotenv
from dotenv import load_dotenv,set_key
import argparse
from black_scholes_model import option_greeks
load_dotenv()


class DeltaStrategy():

    def __init__(self, config):
        self.config = config
        self.api_key = os.getenv('api_key')
        self.access_token = os.getenv('access_token')
        self.kws = KiteTicker(self.api_key, self.access_token)
        self.kite = KiteConnect(api_key=self.api_key)
        self.instruments = pd.DataFrame(self.kite.instruments(self.config['exchange']))

        self.index_tokens = {'NIFTY':256265, 'SENSEX': 265}
        self.instrument_tokens = [self.index_tokens[self.config['trading_symbol']]]

        self.latest_ticks = {self.index_tokens[self.config['trading_symbol']]: None}
        self.strikes = {}
        self.trading_symbols = {}
        self.expiry = None


        self.tick_queue = Queue()
        self.lock = threading.Lock()

        self.iv = {}
        self.delta = {}
        self.gamma = {}


        return

    def process_ticks(self):
        while True:
            try:
                tick = self.tick_queue.get(timeout=1)
                with self.lock:
                    # Process the tick data
                    if tick['instrument_token'] in self.index_tokens.values():
                        self.latest_ticks[tick['instrument_token']] = tick
                        continue
                    
                    # print(tick)
                    tick['trading_symbol'] = self.trading_symbols[tick['instrument_token']]
                    # current_time = tick['last_trade_time']
                    time_to_expiry = (self.expiry - tick['last_trade_time']).total_seconds() / (365*86400)  # Convert to days

                    iv, delta, gamma = option_greeks(
                        spot=self.latest_ticks[self.index_tokens[self.config['trading_symbol']]]['last_price'],
                        strike=self.strikes[tick['instrument_token']],
                        dte=time_to_expiry,
                        rate=0.06,  # Example risk-free rate
                        option_type='CE' if 'CE' in tick['trading_symbol'] else 'PE',
                        option_price=tick['last_price']
                    )

                    self.iv[self.trading_symbols[tick['instrument_token']]] = float(iv)
                    self.delta[tick['trading_symbol']] = float(delta)
                    self.gamma[tick['trading_symbol']] = float(gamma)

                    tick['iv'] = iv
                    tick['delta'] = delta
                    tick['gamma'] = gamma

                    self.latest_ticks[tick['instrument_token']] = tick

                    
                    pass

            except Exception as e:
                print(f"Error processing tick: {e}")   
                pass 
    
    def update_trading_symbol(self):
        expiry = sorted(self.instruments.loc[self.instruments['name']==self.config['trading_symbol'],'expiry'])
        weekly = expiry[0]
        self.expiry = datetime.combine(weekly,datetime.min.time()) + timedelta(hours=15,minutes=30)

        self.lot_size = self.instruments.loc[(self.instruments['name']==self.config['trading_symbol']),'lot_size'].values[0]
        instrument_tokens = self.instruments.loc[(self.instruments['name']==self.config['trading_symbol'])&(self.instruments['expiry']==weekly)&((self.instruments['strike']>self.latest_ticks[self.index_tokens[self.config['trading_symbol']]]['last_price']-(5*self.config['strike_gap']))&(self.instruments['strike']<=self.latest_ticks[self.index_tokens[self.config['trading_symbol']]]['last_price']+(5*self.config['strike_gap'])))&(self.instruments['instrument_type']!='FUT'),'instrument_token'].tolist()
        self.instrument_tokens.extend(instrument_tokens)
        print(self.instrument_tokens)

        for token in self.instrument_tokens:
            if token in self.index_tokens.values():
                continue
            self.trading_symbols[token] = self.instruments.loc[self.instruments['instrument_token']==token,'tradingsymbol'].values[0]
            self.strikes[token] = float(self.instruments.loc[self.instruments['instrument_token']==token,'strike'].values[0])

    def on_ticks(self, ws, ticks):
        
        if self.latest_ticks[self.index_tokens[self.config['trading_symbol']]] is not None and len(self.instrument_tokens)<2:
            self.update_trading_symbol()
            ws.subscribe(self.instrument_tokens)
            ws.set_mode(ws.MODE_FULL, self.instrument_tokens)

        for tick in ticks:
            self.tick_queue.put(tick)
        return
    
    def on_connect(self,ws,response):
        """Callback when WebSocket connects."""
        print("WebSocket connected!")
        ws.subscribe(self.instrument_tokens)
        ws.set_mode(ws.MODE_FULL, self.instrument_tokens)
        return
    

    def start(self):
        """Start the WebSocket connection."""
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect

        # Start the tick processing thread
        tick_thread = threading.Thread(target=self.process_ticks)
        tick_thread.daemon = True
        tick_thread.start()

        # Start the WebSocket connection
        print("Connecting websocket")
        self.kws.connect(threaded=True)

        try:
            while True:
                time.sleep(10)  # Keep the main thread alive
                # print(self.iv)
                print(self.delta)
                # print(self.gamma)
        except KeyboardInterrupt:
            logging.info("Stopping the reactor...")
            self.running = False

        return
    
config = {    
    'exchange': 'NFO',
    'trading_symbol': 'NIFTY',
    'strike_gap': 50,
}

sample = DeltaStrategy(config)
sample.start() 
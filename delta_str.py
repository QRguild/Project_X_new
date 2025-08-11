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
from threading_data import DataStream
load_dotenv()


class DeltaStrategy(DataStream):

    def __init__(self, config):
        # super().__init__(config)

        self.config = config
        self.api_key = os.getenv('api_key')
        self.access_token = os.getenv('access_token')
        self.kws = KiteTicker(self.api_key, self.access_token)
        self.kite = KiteConnect(api_key=self.api_key)
        self.instruments = pd.DataFrame(self.kite.instruments(self.config['exchange']))
        self.delta_range = config.get("delta_range", [0.2, 0.8])
        self.unrealized_pnl = {}

        self.index_tokens = {'NIFTY':256265, 'SENSEX': 265}
        self.instrument_tokens = [self.index_tokens[self.config['trading_symbol']]]
        print(f"Instrument tokens: {self.instrument_tokens}")

        self.latest_ticks = {self.index_tokens[self.config['trading_symbol']]: None}
        self.strikes = {}
        self.trading_symbols = {}
        self.expiry = None

        self.positions = {}
        self.data_queue = Queue()
        self.current_dir = os.getcwd()

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
                        tick['tradingsymbol'] = self.trading_symbols[tick['instrument_token']]
                        continue
                    
                    tick['tradingsymbol'] = self.trading_symbols[tick['instrument_token']]
                    # current_time = tick['last_trade_time']
                    time_to_expiry = (self.expiry - tick['last_trade_time']).total_seconds() / (365*86400)  # Convert to days

                    iv, delta, gamma, vega = option_greeks(
                        spot=self.latest_ticks[self.index_tokens[self.config['trading_symbol']]]['last_price'],
                        strike=self.strikes[tick['instrument_token']],
                        dte=time_to_expiry,
                        rate=0.07,  # Example risk-free rate
                        option_type='CE' if 'CE' in tick['tradingsymbol'] else 'PE',
                        option_price=tick['last_price']
                    )

                    
                    self.iv[self.trading_symbols[tick['instrument_token']]] = float(iv)
                    self.delta[self.trading_symbols[tick['instrument_token']]] = float(delta)
                    self.gamma[tick['tradingsymbol']] = float(gamma)

                    tick['iv'] = iv
                    tick['delta'] = delta
                    tick['gamma'] = gamma
                    tick['vega'] = vega
                    # print(tick['instrument_token'], tick['tradingsymbol'], iv, delta, gamma, vega)
                    self.data_queue.put(tick)
                    bar = BarData(**tick)

                    self.latest_ticks[bar.instrument_token] = bar

                    # self.update_positions()

                    
                    pass

            except Exception as e:
                print(f"Error processing tick: {e}")   
                pass 
    
    def update_positions(self):
        positions_to_update = {}
        for token, tick in self.latest_ticks.items():

            if tick.delta is not None and self.delta_range[0] <= tick.delta <= self.delta_range[1]:
                positions_to_update[token] = -1
            else:
                positions_to_update[token] = 1
        
        for token, position in positions_to_update.items():
            if token in self.positions and not self.positions[token] == position:
                print(f"Updating position for {token}: {self.positions[token]} -> {position}")
                # instru_token = [k for k, v in self.trading_symbols.items() if v == symbol][0]
                symbol=self.latest_ticks[token].tradingsymbol
                if self.positions[symbol] == -1 and position == 1:
                    self.place_order(self.ticks[instru_token],2,'BUY',self.ticks[instru_token].close)
                elif self.positions[symbol] == 1 and position == -1:
                    self.place_order(self.ticks[instru_token],2,'SELL',self.ticks[instru_token].close)

                self.positions[symbol] = position
            elif token not in self.positions:
                instru_token = [k for k, v in self.trading_symbols.items() if v == symbol][0]
                print(f"Adding new position for {symbol}: {position}")
                if position == -1:
                    # self.place_order(self.ticks[instru_token],1,'SELL',self.ticks[instru_token].close)
                    self.place_sell_order(self.latest_ticks[instru_token].tradingsymbol, self.lot_size, entry=True)
                    self.unrealized_pnl[symbol] = {}
                    self.unrealized_pnl[symbol]['pnl']=0
                    self.unrealized_pnl[symbol]['price'] = self.ticks[instru_token].close
                elif position == 1:
                    # self.place_order(self.ticks[instru_token],1,'BUY',self.ticks[instru_token].close)
                    self.place_buy_order(self.latest_ticks[instru_token].tradingsymbol, self.lot_size, entry=True)
                    self.unrealized_pnl[symbol] = {}
                    self.unrealized_pnl[symbol]['pnl']=0
                    self.unrealized_pnl[symbol]['price'] = self.ticks[instru_token].close
                self.positions[symbol] = position

        return
    
    def update_trading_symbol(self):
        expiry = sorted(self.instruments.loc[self.instruments['name']==self.config['trading_symbol'],'expiry'])
        weekly = expiry[0]
        self.expiry = datetime.combine(weekly,datetime.min.time()) + timedelta(hours=15,minutes=30)

        self.lot_size = self.instruments.loc[(self.instruments['name']==self.config['trading_symbol']),'lot_size'].values[0]
        instrument_tokens = self.instruments.loc[(self.instruments['name']==self.config['trading_symbol'])&(self.instruments['expiry']==weekly)&((self.instruments['strike']>self.latest_ticks[self.index_tokens[self.config['trading_symbol']]]['last_price']-(20*self.config['strike_gap']))&(self.instruments['strike']<=self.latest_ticks[self.index_tokens[self.config['trading_symbol']]]['last_price']+(20*self.config['strike_gap'])))&(self.instruments['instrument_type']!='FUT'),'instrument_token'].tolist()
        self.instrument_tokens.extend(instrument_tokens)
        print(self.instrument_tokens)

        for token in self.instrument_tokens:
            if token in self.index_tokens.values():
                self.trading_symbols[token] = self.config['trading_symbol']
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

        data_thread = threading.Thread(target=self.write_data)
        data_thread.daemon = True
        data_thread.start()

        # margin_thread = threading.Thread(target=self.get_margin)
        # margin_thread.daemon = True
        # margin_thread.start()

        # Start the WebSocket connection
        print("Connecting websocket")
        self.kws.connect(threaded=True)

        try:
            while True:
                time.sleep(10)  # Keep the main thread alive
                # print(self.iv)
                # print(self.delta)
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


# remember to comment out the data part
sample = DeltaStrategy(config)
sample.start() 
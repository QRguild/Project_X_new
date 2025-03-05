from datetime import datetime,date
import logging
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
# from threading_nifty import WeightedNiftyIndexVWAP
# from threading_sensex import WeightedSensexIndexVWAP
load_dotenv()

class DataStream:
    # with open('/Users/sushrutkagde/Documents/Trading platform/api_key.txt','r') as file:
    #     api_key=file.read()
    # with open('/Users/sushrutkagde/Documents/Trading platform/access_token.txt','r') as file:
    #     access_token=file.read()

    api_key = os.getenv('api_key')
    access_token = os.getenv('access_token')

    def __init__(self,config : dict):
        self.index_symbol = config['trading_symbol']
        self.exchange = config['exchange']
        self.strike_gap = config['strike_gap']*5
        self.kws = KiteTicker(DataStream.api_key, DataStream.access_token)
        self.instrument_tokens = []
        self.latest_prices = {token: 0 for token in self.instrument_tokens}
        self.lock = threading.Lock()
        self.current_dir = os.getcwd()
        self.index_value_file = os.path.join(self.current_dir, 'index.txt')
        with open(self.index_value_file,'r') as file:
            self.index_value = float(file.read())
        self.tick_queue = Queue()
        self.options_contracts = {}         # stores the option contracts
        self.synthetic_future = {} 
        self.kite = KiteConnect(api_key=DataStream.api_key)
        self.instruments = pd.DataFrame(self.kite.instruments(exchange=self.exchange)) 
        self.trading_symbols = {}
        self.strikes = {}
        self.data_queue = Queue()
        self.vwap_file = os.path.join(self.current_dir, 'vwap.txt')
        self.lot_size = None
        self.vwap = None

        self.current_sell_margin = {symbol : None for symbol in self.trading_symbols.values()}
        self.current_buy_margin = {symbol : None for symbol in self.trading_symbols.values()}

        self.update_instrument()
        if not self.instrument_tokens:
            raise ValueError("No instrument tokens found for subscription.")

        # self.vwap_nifty = WeightedNiftyIndexVWAP(api_key=DataStream.api_key,access_token=DataStream.access_token)



    def update_instrument(self):
        expiry = self.instruments.loc[self.instruments['name']==self.index_symbol,'expiry']
        expiry = sorted(expiry)
        weekly = expiry[0]
        self.lot_size = self.instruments.loc[(self.instruments['name']==self.index_symbol),'lot_size'].values[0]
        self.instrument_tokens = self.instruments.loc[(self.instruments['name']==self.index_symbol)&(self.instruments['expiry']==weekly)&((self.instruments['strike']>self.index_value-self.strike_gap)&(self.instruments['strike']<=self.index_value+self.strike_gap)),'instrument_token'].tolist()
        for token in self.instrument_tokens:
            self.trading_symbols[token] = self.instruments.loc[self.instruments['instrument_token']==token,'tradingsymbol'].values[0]
            self.strikes[token] = float(self.instruments.loc[self.instruments['instrument_token']==token,'strike'].values[0])
        return

    def on_ticks(self, ws, ticks):
        """Callback to handle incoming ticks."""
        for tick in ticks:
            self.tick_queue.put(tick)

    def on_connect(self, ws, response):
        """Callback when WebSocket connects."""
        print("WebSocket connected!")
        ws.subscribe(self.instrument_tokens)
        ws.set_mode(ws.MODE_FULL, self.instrument_tokens)  # Full mode for price and volume data

    def place_buy_order(self,tradingsymbol:str,quantity:int):
        return
    
    def place_sell_order(self,tradingsymbol:str,quantity:int):
        return
    
    def write_trade(self):
        return
    
    def get_best_price(self,trading_symbol : str,transaction_type : str):
        return

    def process_ticks(self):
        """Process incoming ticks and update historical data."""
        while True:
            try:
                tick = self.tick_queue.get(timeout=1)
                with self.lock:
                    tick['tradingsymbol'] = self.trading_symbols[tick['instrument_token']]
                    # print(tick['tradingsymbol'])
                    tick['strike'] = self.strikes[tick['instrument_token']]
                    tick['synthetic_future'] = self.syn_future(tick['strike'])
                    tick['vwap'] = self.get_vwap()

                    tick['sell_margin'] =  self.current_sell_margin[tick['tradingsymbol']]
                    tick['buy_margin'] =  self.current_buy_margin[tick['tradingsymbol']]

                    updated_tick = BarData(**tick)
                    self.options_contracts[updated_tick.tradingsymbol] = updated_tick    # Update the latest tick
                    self.data_queue.put(tick)

            except Exception as e:
                print(f"Error processing tick: {e}")

    def write_data(self):
        """Writes the option cantract data into csv files."""
        today = str(date.today())
        folder_name = 'options_data'
        folder_path = os.path.join(self.current_dir, folder_name)
        folder_path = os.path.join(folder_path,today)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Full file path
        while True:
            try:
                data = self.data_queue.get(timeout=1)
                with self.lock:
                    csv_file = data['tradingsymbol'] + today + '.csv'
                    file_path = os.path.join(folder_path, csv_file)
                    file_exist = os.path.exists(file_path)
                    with open(file_path,mode='a',newline='') as file:
                        writer = csv.DictWriter(file, fieldnames=data.keys())
                
                        # Write header only if file does not exist
                        if not file_exist:
                            writer.writeheader()
                        
                        # Write the data rows
                        writer.writerows([data])
                    
                # time.sleep(1)  # Update every second
            except Exception as e:
                print(f"Error writing data: {e}")

    def get_vwap(self):
        self.vwap=''
        while self.vwap=='':
            with open(self.vwap_file, 'r') as file:
                self.vwap = file.read()
                try:
                    self.vwap = float(self.vwap)
                except:
                    self.vwap = ''
        return self.vwap
    
    def get_margin(self):
        while True:
            try:
                # with self.lock:
                    if not len(self.trading_symbols) == 0:
                        for contract in self.trading_symbols.values():
                            margins = self.kite.order_margins([{"exchange": self.exchange,
                                                                "tradingsymbol": contract,
                                                                "transaction_type": "SELL",
                                                                "variety": "regular",
                                                                "product": "NRML",
                                                                "order_type": "MARKET",
                                                                "quantity": int(self.lot_size),} ,

                                                                {"exchange": self.exchange,
                                                                "tradingsymbol": contract,
                                                                "transaction_type": "BUY",
                                                                "variety": "regular",
                                                                "product": "NRML",
                                                                "order_type": "MARKET",
                                                                "quantity": int(self.lot_size),}
                                                                ])
                            self.current_sell_margin[contract] = margins[0]['total']
                            self.current_buy_margin[contract] = margins[1]['total']
                        
                        # print(self.current_sell_margin)
                        # print(self.current_buy_margin)

            except Exception as e:
                print(f"Error getting margin: {e}")
        
        return
    
    def login(self):
        print(self.kite.login_url())
        request_token = input("Enter the request token: ")
        data = self.kite.generate_session(request_token, api_secret=os.getenv('api_secret'))
        # self.kite.set_access_token(data["access_token"])
        # set_key('.env','access_token',data['access_token'])
        return


    def start(self):
        """Start the WebSocket connection and threads."""
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect


        tick_thread = threading.Thread(target=self.process_ticks)
        tick_thread.daemon = True
        tick_thread.start()

        data_thread_index = threading.Thread(target=self.write_data)
        data_thread_index.daemon = True
        data_thread_index.start()

        margin_thread = threading.Thread(target=self.get_margin)    
        margin_thread.daemon = True
        margin_thread.start()

        # vwap_thread = threading.Thread(target=self.vwap_nifty.get_vwap)

        # Connect WebSocket (blocking call)
        print("Connecting WebSocket...")
        self.kws.connect(threaded=True)

        # Keep the main thread running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Stopping the reactor...")
            self.running = False

    def syn_future(self,strike):
        # calculates the synthetic future price using put call parity
        contract_list = [bar for bar in self.options_contracts.values() if bar.strike==strike]
        if len(contract_list)<2:
            return None
        call_option = next((bar for bar in contract_list if bar.tradingsymbol[-2:]=='CE'),None)
        put_option = next((bar for bar in contract_list if bar.tradingsymbol[-2:] == 'PE'), None)

        # C-P+S
        self.synthetic_future[strike] = strike + call_option.last_price - put_option.last_price
        return self.synthetic_future[strike]


config = {
    'trading_symbol':'SENSEX',
    'exchange':'BFO',
    'strike_gap':100
}

# stream = DataStream(config)
# stream.login()

# print(stream.trading_symbols)
# stream.start()
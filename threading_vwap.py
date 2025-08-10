from threading import *
import threading
from queue import Queue
from kiteconnect import KiteTicker
import time
from collections import defaultdict, deque
import os
import csv
from datetime import datetime
import dotenv
from dotenv import load_dotenv
import logging

from datetime import datetime, timedelta

class WeightedIndexVWAP(Thread):
    def __init__(self, api_key, access_token,trading_symbol):
        super().__init__()
        self.kws = KiteTicker(api_key, access_token)
        self.index_weights = {'NIFTY':{6401: 0.57,
 3861249: 0.82,
 40193: 0.63,
 60417: 1.0,
 1510401: 2.96,
 4267265: 0.82,
 81153: 2.2,
 4268801: 1.03,
 98049: 1.01,
 1304833: 1.32,
 2714625: 4.37,
 4644609: 0.7,
 177665: 0.76,
 5215745: 0.85,
 225537: 0.66,
 232961: 0.69,
 315393: 0.94,
 1850625: 1.59,
 341249: 13.07,
 119553: 0.69,
 345089: 0.45,
 348929: 0.93,
 356865: 1.88,
 1270529: 8.95,
 424961: 3.59,
 1346049: 0.4,
 408065: 5.31,
 3001089: 0.95,
 492033: 3.0,
 2939649: 3.85,
 519937: 2.22,
 2815745: 1.42,
 2977281: 1.59,
 4598529: 0.76,
 633601: 0.9,
 3834113: 1.24,
 738561: 8.12,
 5582849: 0.65,
 1102337: 0.86,
 779521: 2.79,
 857857: 1.76,
 2953217: 3.46,
 878593: 0.61,
 884737: 1.32,
 895745: 1.2,
 3465729: 0.85,
 897537: 1.19,
 502785: 1.11,
 2952193: 1.26,
 969473: 0.7,
 256265: 0},
           'SENSEX' : {136427780: 1.08,
 128209924: 1.12,
 136247044: 3.42,
 136442372: 1.11,
 128008708: 2.49,
 136308228: 5.48,
 136263940: 1.84,
 128046084: 15.4,
 128178180: 2.17,
 136236548: 10.4,
 128064260: 1.24,
 128053508: 5.96,
 128224004: 3.94,
 128063236: 3.21,
 128130564: 4.27,
 128133124: 2.84,
 136320004: 1.67,
 128012548: 1.52,
 136334084: 1.63,
 136421892: 1.36,
 128083204: 10.61,
 128028676: 3.15,
 134327044: 1.81,
 128145924: 1.47,
 128120324: 1.36,
 136330244: 3.54,
 136385284: 1.05,
 128029188: 1.54,
 136329732: 1.49,
 139089924: 1.83,
 265: 0.0}
           }
        
        self.index_token = next(token for token in self.index_weights[trading_symbol].keys() if self.index_weights[trading_symbol][token]==0)
        self.weights = self.index_weights[trading_symbol]
        self.trading_symbol = trading_symbol
        self.instrument_tokens = list(self.weights.keys())
        self.latest_prices = {token: 0 for token in self.instrument_tokens}
        self.lock = threading.Lock()
        self.index_value = 0
        self.tick_queue = Queue()
        self.divisor = 0
        self.divisor_list = []
        self.vwap_index_value = 0
        # Historical data for last 30 minutes: {token: deque([(timestamp, price, volume)])}

        self.historical_data = defaultdict(lambda: deque(maxlen=12000))  # 1800 seconds (30 minutes)

    def on_ticks(self, ws, ticks):
        """Callback to handle incoming ticks."""
        for tick in ticks:
            self.tick_queue.put(tick)

    def on_connect(self, ws, response):
        """Callback when WebSocket connects."""
        print("WebSocket connected!")
        ws.subscribe(self.instrument_tokens)
        ws.set_mode(ws.MODE_FULL, self.instrument_tokens)  # Full mode for price and volume data

    def process_ticks(self):
        """Process incoming ticks and update historical data."""
        while True:
            try:
                tick = self.tick_queue.get(timeout=1)
                with self.lock:
                    token = tick['instrument_token']
                    price = tick['last_price']
                    volume = tick.get('volume_traded',0)  # Volume may not always be available

                    # Update latest prices
                    self.latest_prices[token] = price
                    # custom_time = 1748521000.672639

                    # Add to historical data (timestamped price and volume)
                    current_time = time.time()
                    
                    self.historical_data[token].append((current_time, price, volume))
            except Exception as e:
                print(f"Error processing tick: {e}")

    def calculate_weighted_index(self):
        """Calculate the current weighted index value."""
        while True:
            try:
                with self.lock:
                    weighted_sum = sum(self.latest_prices[token] * self.weights[token]
                                       for token in self.instrument_tokens)
                    # total_weight = sum(self.weights.values())
                    self.divisor = weighted_sum/self.latest_prices[self.index_token] if self.latest_prices[self.index_token] > 0 else 0
                    # print(self.latest_prices)
                    self.index_value = weighted_sum / self.divisor if self.divisor > 0 else 0
                # print(f"Current Weighted Nifty Index Value: {self.index_value:.2f}",self.divisor)
                time.sleep(0.5)  # Update every second
            except Exception as e:
                print(f"Error calculating weighted index: {e}")
                continue

    def calculate_vwap(self):
        """Calculate the VWAP of the weighted index for the last 30 minutes."""
        while True:
            try:
                with self.lock:
                    total_volume_weighted_price = 0
                    total_volume = 0

                    # Iterate over all tokens to calculate VWAP
                    # print(self.historical_data)
                    for token in self.instrument_tokens:
                        if self.weights[token] == 0:
                            self.index_token = token
                            self.index_value = self.latest_prices[token]
                            with open('index.txt','w') as file:
                                file.write(str(self.latest_prices[token]))
                            continue
                        current_time = time.time()
                        recent_data = [(price, volume) for t, price, volume in self.historical_data[token]
                                       if (current_time - t) <= 1800]  # Keep only last 30 minutes of data
                        # print(recent_data)
                        # if len(recent_data)>0:
                        #     print(recent_data)
                        
                        # Calculate VWAP components for this token
                        vp = 0
                        vol = 0
                        for price, volume in recent_data:
                            vp += price * volume
                            vol += volume 
                        total_volume_weighted_price += (vp/vol)*self.weights[token]

                    # Calculate VWAP of the weighted index
                    # print(total_volume_weighted_price/self.divisor)
                    self.vwap_index_value = total_volume_weighted_price/self.divisor

                # print(f"Last 30-Minute VWAP of Weighted Index: {vwap_index_value }")
                with open('vwap.txt','w') as file:
                    file.write(str(self.vwap_index_value))
                
                with open(self.filename,'a') as file:
                    writer = csv.writer(file)
                    writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),self.vwap_index_value])
                time.sleep(0.5)  
            except Exception as e:
                print(f"Error calculating VWAP: {e}")
                continue

    def initialise_csv(self):
        folder_name = os.path.join(os.getcwd(), 'vwap_data')
        self.filename = self.trading_symbol+'_vwap_'+time.strftime("%Y%m%d")+'.csv'
        self.filename = os.path.join(folder_name, self.filename)
        if not os.path.exists(self.filename):
            with open(self.filename,'w') as file:
                writer = csv.writer(file)
                writer.writerow(['timestamp','vwap'])

    def start(self):
        """Start the WebSocket connection and threads."""
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect

        tick_thread = threading.Thread(target=self.process_ticks)
        tick_thread.daemon = True
        tick_thread.start()

        calc_thread_index = threading.Thread(target=self.calculate_weighted_index)
        calc_thread_index.daemon = True
        calc_thread_index.start()

        calc_thread_vwap = threading.Thread(target=self.calculate_vwap)
        calc_thread_vwap.daemon = True
        calc_thread_vwap.start()

        # Connect WebSocket (blocking call)
        print("Connecting WebSocket")
        self.kws.connect(threaded=True)
        
        self.initialise_csv()

        # Keep the main thread running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Stopping the index calculation")
            self.running = False



# Usage
# load_dotenv()
# api_key = os.getenv('api_key')
# access_token = os.getenv('access_token')


# weighted_nifty_index_vwap = WeightedIndexVWAP('s4huxmt59th45biy','gW91rMnlF0nJn6qSd3eWd5MyKQ2QSg0y','NIFTY')   
# weighted_nifty_index_vwap.start()

# Usage

# weighted_nifty_index = WeightedNiftyIndex(api_key, access_token, weights)
# weighted_nifty_index.start()


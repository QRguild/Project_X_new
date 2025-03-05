from datetime import datetime
# from kiteconnect import KiteTicker
# from collections import deque
# import threading
# import numpy as np

# class CustomIndex:
#     def __init__(self, api_key, access_token, instrument_tokens, window_size=100):
#         self.kws = KiteTicker(api_key, access_token)
#         self.instrument_tokens = instrument_tokens
#         self.last_prices = {token: deque(maxlen=window_size) for token in instrument_tokens}
#         self.lock = threading.Lock()
#         self.index_value = 0

#     def on_ticks(self, ws, ticks):
#         with self.lock:
#             for tick in ticks:
#                 token = tick['instrument_token']
#                 if token in self.last_prices:
#                     self.last_prices[token].append(tick['last_price'])
#         self.calculate_index()

#     def on_connect(self, ws, response):
#         ws.subscribe(self.instrument_tokens)
#         ws.set_mode(ws.MODE_LTP, self.instrument_tokens)

#     def calculate_index(self):
#         with self.lock:
#             values = [np.mean(prices) for prices in self.last_prices.values() if prices]
#             self.index_value = np.mean(values) if values else 0

#     def start(self):
#         self.kws.on_ticks = self.on_ticks
#         self.kws.on_connect = self.on_connect
#         self.kws.connect(threaded=True)

#     def get_index_value(self):
#         return self.index_value

# # Usage
# api_key = "s4huxmt59th45biy"
# access_token = "CIsr4YrhJh1A27rroTRV3M3l30vlaAW7"
# weights = {6401: 0.64, 3861249: 0.92, 40193: 0.63, 60417: 1.3, 1510401: 3.03, 4267265: 1.18, 81153: 1.86, 4268801: 0.93, 98049: 0.88, 134657: 0.62, 2714625: 3.95, 140033: 0.64, 177665: 0.78, 5215745: 1.0, 225537: 0.71, 232961: 0.6, 315393: 0.9, 1850625: 1.64, 341249: 11.34, 119553: 0.66, 345089: 0.64, 348929: 0.95, 356865: 2.27, 1270529: 7.74, 424961: 4.16, 1346049: 0.82, 408065: 5.82, 3001089: 0.85, 492033: 2.35, 2939649: 3.73, 519937: 2.38, 2815745: 1.5, 2977281: 1.81, 4598529: 0.83, 633601: 1.0, 3834113: 1.38, 738561: 8.64, 5582849: 0.71, 1102337: 0.86, 779521: 2.62, 857857: 1.79, 2953217: 3.76, 878593: 0.67, 884737: 1.78, 895745: 1.21, 3465729: 0.86, 897537: 1.37, 502785: 1.45, 2952193: 1.16, 969473: 0.66}
# instrument_tokens = list(weights.keys())  # Example tokens, replace with your 50 Sensex 50 tokens

# custom_index = CustomIndex(api_key, access_token, instrument_tokens)
# custom_index.start()

# # To get the index value
# while True:
#     print(f"Custom Index Value: {custom_index.get_index_value()}")
#     # Add a sleep here to control how often you want to print the index value


# import threading
# from queue import Queue
# from kiteconnect import KiteTicker
# import numpy as np
# import time
import logging

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# class WeightedSensexIndex:
#     def __init__(self, api_key, access_token, weights):
#         self.kws = KiteTicker(api_key, access_token)
#         self.weights = weights
#         self.instrument_tokens = list(weights.keys())
#         self.latest_prices = {token: 0 for token in self.instrument_tokens}
#         self.lock = threading.Lock()
#         self.index_value = 0
#         self.tick_queue = Queue()
#         self.running = True

#     def on_ticks(self, ws, ticks):
#         for tick in ticks:
#             self.tick_queue.put(tick)

#     def on_connect(self, ws, response):
#         logging.info("Successfully connected. Response: %s", response)
#         ws.subscribe(self.instrument_tokens)
#         ws.set_mode(ws.MODE_LTP, self.instrument_tokens)

#     def on_close(self, ws, code, reason):
#         logging.info("Connection closed. Code: %s, Reason: %s", code, reason)

#     def on_error(self, ws, code, reason):
#         logging.error("Error occurred. Code: %s, Reason: %s", code, reason)

#     def process_ticks(self):
#         while self.running:
#             try:
#                 tick = self.tick_queue.get(timeout=1)
#                 with self.lock:
#                     self.latest_prices[tick['instrument_token']] = tick['last_price']
#             except Queue.Empty:
#                 continue
#             except Exception as e:
#                 logging.error("Error processing tick: %s", str(e))

#     def calculate_weighted_index(self):
#         while self.running:
#             try:
#                 with self.lock:
#                     weighted_sum = sum(self.latest_prices[token] * self.weights[token] 
#                                        for token in self.instrument_tokens)
#                     total_weight = sum(self.weights.values())
#                     self.index_value = (weighted_sum/self.latest_prices[265])
#                     print(total_weight,weighted_sum)
#                 logging.info("Current Weighted Sensex Index Value: %.2f", self.index_value)
#                 time.sleep(1)  # Calculate once per second
#             except Exception as e:
#                 logging.error("Error calculating index: %s", str(e))

#     def start(self):
#         self.kws.on_ticks = self.on_ticks
#         self.kws.on_connect = self.on_connect
#         self.kws.on_close = self.on_close
#         self.kws.on_error = self.on_error

#         tick_thread = threading.Thread(target=self.process_ticks)
#         tick_thread.daemon = True
#         tick_thread.start()

#         calc_thread = threading.Thread(target=self.calculate_weighted_index)
#         calc_thread.daemon = True
#         calc_thread.start()

#         self.kws.connect(threaded=True)

#         # Keep the main thread running
#         try:
#             while True:
#                 time.sleep(1)
#         except KeyboardInterrupt:
#             logging.info("Stopping the index calculation...")
#             self.running = False

import threading
from queue import Queue
from kiteconnect import KiteTicker
import time
from collections import defaultdict, deque
import csv
import os
from Bardata import BarData
from dotenv import load_dotenv


class WeightedSensexIndexVWAP:
    def __init__(self, api_key, access_token, weights):
        self.kws = KiteTicker(api_key, access_token)
        self.weights = weights
        self.instrument_tokens = list(weights.keys())
        self.latest_prices = {token: 0 for token in self.instrument_tokens}
        self.lock = threading.Lock()
        self.index_value = 0
        self.tick_queue = Queue()
        self.divisor = 0
        self.divisor_list = []
        # Historical data for last 30 minutes: {token: deque([(timestamp, price, volume)])}
        self.historical_data = defaultdict(lambda: deque(maxlen=1800))  # 1800 seconds (30 minutes)
        self.filename = 'sensex_vwap'+time.strftime("%Y%m%d")+'.csv'

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
                    total_weight = sum(self.weights.values())
                    self.divisor = weighted_sum/self.latest_prices[265] if self.latest_prices[265] > 0 else 0
                    # print(self.latest_prices)
                    self.index_value = weighted_sum / self.divisor if self.divisor > 0 else 0
                # print(f"Current Weighted Sensex Index Value: {self.index_value:.2f}")
                time.sleep(1)  # Update every second
            except Exception as e:
                print(f"Error calculating weighted index: {e}")

    def calculate_vwap(self):
        """Calculate the VWAP of the weighted index for the last 30 minutes."""
        while True:
            try:
                with self.lock:
                    total_volume_weighted_price = 0
                    total_volume = 0

                    # Iterate over all tokens to calculate VWAP
                    for token in self.instrument_tokens:
                        if token == 265:
                            continue
                        current_time = time.time()
                        # print(current_time)
                        recent_data = [(price, volume) for t, price, volume in self.historical_data[token]
                                       if current_time - t <= 1800]  # Keep only last 30 minutes of data

                        # Calculate VWAP components for this token
                        vp = 0
                        vol = 0
                        for price, volume in recent_data:
                            vp += price * volume
                            vol += volume 
                        total_volume_weighted_price += (vp/vol)*self.weights[token]

                    # Calculate VWAP of the weighted index
                    # print(total_volume_weighted_price/self.divisor)
                    vwap_index_value = total_volume_weighted_price/self.divisor

                # print(f"Last 30-Minute VWAP of Weighted Index: {vwap_index_value }")
                with open('vwap.txt','w') as file:
                    file.write(str(vwap_index_value))
                with open('index.txt','w') as file:
                    file.write(str(self.latest_prices[265]))
                # with open(self.filename,'a') as file:
                #     writer = csv.writer(file)
                #     writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),vwap_index_value])
                time.sleep(0.5)  
            except Exception as e:
                print(f"Error calculating VWAP: {e}")

    def initialise_csv(self):
        self.filename = 'sensex_vwap_'+time.strftime("%Y%m%d")+'.csv'
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
        print("Connecting WebSocket...")
        self.kws.connect(threaded=True)

        # Initialise CSV file
        # self.initialise_csv()

        # Keep the main thread running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Stopping the index calculation...")
            self.running = False

# Usage
load_dotenv()

api_key = os.getenv('api_key')
access_token = os.getenv('access_token')

weights = {136427780: 1.57,
 128209924: 1.45,
 136247044: 1.97,
 136442372: 1.83,
 128008708: 3.03,
 136308228: 6.13,
 136263940: 3.12,
 128046084: 8.37,
 128178180: 3.77,
 136236548: 5.82,
 136239876: 0.48,
 128053508: 5.08,
 128224004: 3.69,
 128063236: 2.51,
 128130564: 3.19,
 128133124: 2.36,
 136320004: 2.53,
 128202244: 1.41,
 136334084: 2.1,
 136421892: 1.79,
 128083204: 11.16,
 128028676: 4.49,
 134327044: 2.88,
 128145924: 1.76,
 128120324: 1.06,
 136330244: 9.87,
 136385284: 1.09,
 128029188: 1.98,
 136329732: 2.18,
 139089924: 1.34,
 265:0}

weighted_Sensex_index_vwap = WeightedSensexIndexVWAP(api_key, access_token, weights)
weighted_Sensex_index_vwap.start()

# Usage

# weighted_Sensex_index = WeightedSensexIndex(api_key, access_token, weights)
# weighted_Sensex_index.start()


from threading_data import DataStream
from Bardata import BarData
import threading

from datetime import time as dt_time
from datetime import datetime, date
import logging
import time
import os


class experiment(DataStream):
    def __init__(self, config):
        super().__init__(config)
        self.bps_difference = 0
        self.beta_adjusted_bps_differece = 0
        self.beta_factor = 0
        self.current_time = datetime.now()  # Current timestamp that will be updated with ticks
        self.closing_time = datetime.combine(datetime.now().date(), dt_time(15, 30))  # Market closing time at 15:30
        self.start_time = datetime.combine(datetime.now().date(), dt_time(14, 30))  # strategy start time
        self.bps_threshold = 1
        self.beta_adjusted_bps_threshold = 5


        self.long_orders = []
        self.short_orders = []

        self.is_long = 0
        self.is_short = 0

    def calculate_bps_difference(self):
        self.bps_difference = (((sum(self.synthetic_future.values()) / len(self.synthetic_future)) - (self.get_vwap()))/(sum(self.synthetic_future.values()) / len(self.synthetic_future))) * 10000
        return
    
    def calculate_beta_adjusted_bps_difference(self):
        self.beta_adjusted_bps_differece = self.bps_difference * self.beta_factor
        return
    
    def update_beta_factor(self):
        self.beta_factor = ((self.closing_time - self.current_time).total_seconds()/60)/30
        return

    def checkAllConditions(self):
        folder_name = 'options_data'
        folder_path = os.path.join(self.current_dir,folder_name,str(date.today()),'log.txt')
        with open('log.txt',"a") as file:
            file.write(f"Time: {self.current_time}, VWAP: {self.vwap}, BPS Diff: {self.bps_difference}, Beta Adj BPS: {self.beta_adjusted_bps_differece}, Beta: {self.beta_factor}\n")

        self.update_beta_factor()
        self.calculate_bps_difference()
        self.calculate_beta_adjusted_bps_difference()
        print(self.bps_difference,self.beta_adjusted_bps_differece)
        print(self.beta_factor)

        if self.current_time > self.start_time:
            self.check_long_entry()
            self.check_long_exit()
            self.check_short_entry()
            self.check_short_exit()


    def process_ticks(self):
        while True:
            try:
                tick = self.tick_queue.get(timeout=1)
                with self.lock:
                    tick['tradingsymbol'] = self.trading_symbols[tick['instrument_token']]
                    # print(tick['tradingsymbol'])
                    tick['strike'] = self.strikes[tick['instrument_token']]
                    tick['synthetic_future'] = self.syn_future(tick['strike'])
                    tick['vwap'] = self.get_vwap()

                    # tick['sell_margin'] =  self.current_sell_margin[tick['tradingsymbol']]
                    # tick['buy_margin'] =  self.current_buy_margin[tick['tradingsymbol']]

                    updated_tick = BarData(**tick)
                    self.options_contracts[updated_tick.tradingsymbol] = updated_tick    # Update the latest tick

                    self.current_time = datetime.now()
                    # if self.current_time > self.start_time:
                    self.checkAllConditions()

                    # self.data_queue.put(tick)

            except Exception as e:
                print(f"Error processing tick: {e}")

    def check_long_entry(self):

        if self.bps_difference < -self.bps_threshold and self.beta_adjusted_bps_differece < -self.beta_adjusted_bps_threshold:
            self.is_long += 1
            index_value=self.get_index_value()
            # atm_strike = round(index_value/100)*100
            syn_future_value = sum(self.synthetic_future.values()) / len(self.synthetic_future)
            strikes = list(self.strikes.values())
            atm_strike = float(min(strikes,key=lambda x:abs(x-syn_future_value)))

            for options in self.options_contracts.values():
                if options.strike == atm_strike and options.tradingsymbol[-2:] == 'CE':
                    self.place_buy_order(options.tradingsymbol,self.lot_size)
                    self.long_orders.append(options.tradingsymbol)
                if options.strike == atm_strike and options.tradingsymbol[-2:] == 'PE':
                    self.place_sell_order(options.tradingsymbol,self.lot_size)
                    self.long_orders.append(options.tradingsymbol)

        return
    
    def check_long_exit(self):
        if not self.is_long:
            return
        
        if self.bps_difference > 0 and self.beta_adjusted_bps_differece > 0:
            for order in self.long_orders:
                if order[-2:] == 'CE':
                    self.place_sell_order(order,self.lot_size)
                if order[-2:] == 'PE':
                    self.place_buy_order(order,self.lot_size)
            self.is_long = 0
        
        return
    
    def check_short_entry(self):
        if self.bps_difference > self.bps_threshold and self.beta_adjusted_bps_differece > self.beta_adjusted_bps_threshold:
            self.is_short += 1
            index_value=self.get_index_value()  
            syn_future_value = sum(self.synthetic_future.values()) / len(self.synthetic_future)
            strikes = list(self.strikes.values())
            atm_strike = float(min(strikes,key=lambda x:abs(x-syn_future_value)))
            # atm_strike = round(index_value/100)*100

            for options in self.options_contracts.values():
                if options.strike == atm_strike and options.tradingsymbol[-2:] == 'CE':
                    self.place_sell_order(options.tradingsymbol,self.lot_size)
                    self.short_orders.append(options.tradingsymbol)
                if options.strike == atm_strike and options.tradingsymbol[-2:] == 'PE':
                    self.place_buy_order(options.tradingsymbol,self.lot_size)
                    self.short_orders.append(options.tradingsymbol)
        return
    
    def check_short_exit(self):
        if not self.is_short:
            return
        

        if self.bps_difference < 0 and self.beta_adjusted_bps_differece < 0:
            for order in self.short_orders:
                if order[-2:] == 'CE':
                    self.place_buy_order(order,self.lot_size)
                if order[-2:] == 'PE':  
                    self.place_sell_order(order,self.lot_size)
            self.is_short = 0
        
        return
    
    def start(self):
        """Start the WebSocket connection and threads."""
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect


        tick_thread = threading.Thread(target=self.process_ticks)
        tick_thread.daemon = True
        tick_thread.start()

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

    

config = {
    'trading_symbol':'SENSEX',
    'exchange':'BFO',
    'strike_gap':100
}

sample = experiment(config)
sample.login()

# update for every index
sample.bps_threshold = 10
sample.beta_adjusted_bps_threshold = 20

sample.start()
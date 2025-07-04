from threading_data import DataStream
from Bardata import BarData

from datetime import datetime, time, date
from threading_vwap import WeightedIndexVWAP
import os


class experiment(DataStream):
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.bps_difference = 0
        self.beta_adjusted_bps_differece = 0
        self.beta_factor = 0
        self.current_time = datetime.now()  # Current timestamp that will be updated with ticks
        self.closing_time = datetime.combine(datetime.now().date(), time(15, 30))  # Market closing time at 15:30
        self.start_time = datetime.combine(datetime.now().date(), time(14, 30))  # strategy start time

        self.bps_threshold = 1
        self.beta_adjusted_bps_threshold = 5

        self.current_delta = 0

        self.pivots = {
            'NIFTY':{5:600,12:800,18:900,23:1200,28:1500},
            'SENSEX':{10:360,30:480,50:720,70:960,100:1200}
        }

        # self.vwap = WeightedIndexVWAP(api_key=self.api_key,access_token=self.access_token,trading_symbol=config['trading_symbol'])


        self.long_orders = []
        self.short_orders = []

        self.is_long = 0
        self.is_short = 0

    def calculate_bps_difference(self):
        self.bps_difference = (((sum(self.synthetic_future.values()) / len(self.synthetic_future)) - (self.get_vwap()))/(sum(self.synthetic_future.values()) / len(self.synthetic_future))) * 10000
        return
    
    def calculate_beta_adjusted_bps_difference(self):
        self.beta_adjusted_bps_differece = self.bps_difference / self.beta_factor
        return
    
    def update_beta_factor(self):
        self.beta_factor = ((self.closing_time - self.current_time).total_seconds()/60)/30
        return

    def checkAllConditions(self):
        folder_name = 'options_data'
        folder_path = os.path.join(self.current_dir,folder_name,str(date.today()),'log.txt')
        today = (date.today()).strftime("%Y-%m-%d")
        log_file = today+'_log.txt'
        with open(log_file,"a") as file:
            file.write(f"Time: {self.current_time}, VWAP: {self.vwap}, BPS Diff: {self.bps_difference}, Beta Adj BPS: {self.beta_adjusted_bps_differece}, Beta: {self.beta_factor}\n")

        self.update_beta_factor()
        self.calculate_bps_difference()
        self.calculate_beta_adjusted_bps_difference()
        # print(self.bps_difference,self.beta_adjusted_bps_differece)
        # print(self.beta_factor)


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

                    tick['sell_margin'] =  self.current_sell_margin[tick['tradingsymbol']]
                    tick['buy_margin'] =  self.current_buy_margin[tick['tradingsymbol']]

                    updated_tick = BarData(**tick)
                    self.options_contracts[updated_tick.tradingsymbol] = updated_tick    # Update the latest tick

                    self.current_time = datetime.now()
                    # if self.current_time > self.start_time:
                    self.checkAllConditions()

                    self.data_queue.put(tick)

            except Exception as e:
                print(f"Error processing tick: {e}")

    def check_long_entry(self):
        

        if self.bps_difference < -self.bps_threshold and self.beta_adjusted_bps_differece < -self.beta_adjusted_bps_threshold:
            index_value=self.get_index_value()
            # atm_strike = round(index_value/100)*100
            syn_future_value = sum(self.synthetic_future.values()) / len(self.synthetic_future)
            strikes = list(self.strikes.values())
            atm_strike = float(min(strikes,key=lambda x:abs(x-syn_future_value)))

            if self.pivots[self.config['trading_symbol']][self.beta_adjusted_bps_threshold]*10000 > self.current_delta:
                for options in self.options_contracts.values():
                    if options.strike == atm_strike and options.tradingsymbol[-2:] == 'CE':   #endswith function use
                        self.place_buy_order(options.tradingsymbol,self.lot_size,entry=True)
                        self.long_orders.append(options.tradingsymbol)
                    if options.strike == atm_strike and options.tradingsymbol[-2:] == 'PE':
                        self.place_sell_order(options.tradingsymbol,self.lot_size,entry=True)
                        self.long_orders.append(options.tradingsymbol)
                self.is_long += 1
                self.current_delta += (syn_future_value*self.lot_size)
                for threshold in self.pivots[self.config['trading_symbol']].keys():
                    if self.current_delta < self.pivots[self.config['trading_symbol']][threshold]*10000:
                        self.beta_adjusted_bps_threshold = threshold
                        break

        return
    
    def check_long_exit(self):
        if not self.is_long:
            return
        
        if self.bps_difference > 0 and self.beta_adjusted_bps_differece > 0:
            for order in self.long_orders:
                if order[-2:] == 'CE':
                    self.place_sell_order(order,self.lot_size,entry=False)
                    # self.long_orders.remove(order)
                if order[-2:] == 'PE':
                    self.place_buy_order(order,self.lot_size,entry=False)
                    # self.long_orders.remove(order)
            self.long_orders = []
            self.current_delta = 0
            self.beta_adjusted_bps_threshold = list(self.pivots[self.config['trading_symbol']].keys())[0]
            self.is_long = 0
        
        return
    
    def check_short_entry(self):
        if self.bps_difference > self.bps_threshold and self.beta_adjusted_bps_differece > self.beta_adjusted_bps_threshold:
            # index_value=self.get_index_value()  
            syn_future_value = sum(self.synthetic_future.values()) / len(self.synthetic_future)
            strikes = list(self.strikes.values())
            atm_strike = float(min(strikes,key=lambda x:abs(x-syn_future_value)))
            # atm_strike = round(index_value/100)*100
            if self.pivots[self.config['trading_symbol']][self.beta_adjusted_bps_threshold]*10000 > self.current_delta:
                for options in self.options_contracts.values():
                    if options.strike == atm_strike and options.tradingsymbol[-2:] == 'CE':
                        self.place_sell_order(options.tradingsymbol,self.lot_size,entry=True)
                        self.short_orders.append(options.tradingsymbol)
                    if options.strike == atm_strike and options.tradingsymbol[-2:] == 'PE':
                        self.place_buy_order(options.tradingsymbol,self.lot_size,entry=True)
                        self.short_orders.append(options.tradingsymbol)

                self.is_short += 1
                self.current_delta += (syn_future_value*self.lot_size)
                for threshold in self.pivots[self.config['trading_symbol']].keys():
                    if self.current_delta < self.pivots[self.config['trading_symbol']][threshold]*10000:
                        self.beta_adjusted_bps_threshold = threshold
                        break
        return
    
    def check_short_exit(self):
        if not self.is_short:
            return
        

        if self.bps_difference < 0 and self.beta_adjusted_bps_differece < 0:
            for order in self.short_orders:
                if order[-2:] == 'CE':
                    self.place_buy_order(order,self.lot_size,entry=False)
                    # self.short_orders.remove(order)
                if order[-2:] == 'PE':  
                    self.place_sell_order(order,self.lot_size,entry=False)
                    # self.short_orders.remove(order)

            self.short_orders = []
            self.current_delta = 0
            self.beta_adjusted_bps_threshold = list(self.pivots[self.config['trading_symbol']].keys())[0]
            self.is_short = 0
        
        return
    

config = {
    'trading_symbol':'NIFTY',
    'exchange':'NFO',
    'strike_gap':50
}

sample = experiment(config)
sample.login()

# update for every index
sample.bps_threshold = 4
sample.beta_adjusted_bps_threshold = 5

sample.start()

# Symbol,Cash, Prem, Beta0, Cash 0, Beta1, Cash 1, Beta2, Cash2, Beta3, Cash 3, Beta4, Cash 4, MaxVolPressure, ResMarRtio
# SENSEX,1200,5,10,360,30,480,50,720,70,960,100,1200,0.5,0.0001
# NIFTY,1500,1,5,600,12,800,18,900,23,1200,28,1500,0.5,0.0001
# NSEBANK,2000,1,10,1000,35,1500,45,1760,54,1900,63,2000,0.5,0.0001
# import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
from kiteconnect import KiteConnect
from queue import Queue
from Bardata import BarData
import os
import csv
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd
from threading import *
import threading
from abc import ABC, abstractmethod

def get_all_dates(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

# Generate list of date strings
    all_dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end - start).days + 1)]
    return all_dates

def get_minutewise_timestamp(date):
    start_dt = datetime.strptime(date + " 09:15:00", "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(date + " 15:30:00", "%Y-%m-%d %H:%M:%S")
    
    current_dt = start_dt
    timestamps = []
    
    while current_dt <= end_dt:
        timestamps.append(current_dt.strftime("%Y-%m-%d %H:%M:%S"))
        current_dt += timedelta(minutes=1)
    
    return timestamps

class BacktestEngine(ABC,Thread):
    def __init__(self, config: Dict[str, Any]):
        load_dotenv()
        self.kite = KiteConnect(os.getenv("api_key"), os.getenv("access_token"))
        self.config = config
        self.data_tokens = self.config.get('tokens', [])
        self.trading_symbols = {}  # tradingsymbols with key as instrument_token
        self.update_tokens()
        self.update_trading_symbols(self.data_tokens)
        self.instruments = pd.DataFrame
        self.data_queue = Queue()
        self.lock = threading.Lock()
        self.instruments = None  
        self.stop_event = threading.Event()

        self.traded_orders = {}  # (instrument_token) key, order price, quantity, pnl
        self.active_positions = {token:{'quantity':0,'price':0,'MarkToMarket':0} for token in self.data_tokens}  # instrument_token, quantity, current price, position
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.strategy_path = os.path.join(self.base_path, config['strategy_name'])
        self.setup_directories()

    def setup_directories(self):
        """Initialize directory structure and files"""
        os.makedirs(self.strategy_path, exist_ok=True)
        self.pnl_file = os.path.join(self.strategy_path, 'pnl_logger.csv')
        self.trades_file = os.path.join(self.strategy_path, 'trades.csv')
        
        if not os.path.exists(self.pnl_file):
            pd.DataFrame(columns=['timestamp', 'tradingsymbol', 'current_position', 'MarkToMarket']).to_csv(self.pnl_file, index=False)
        # else:
        #     os.remove(self.pnl_file)
        #     pd.DataFrame(columns=['timestamp', 'tradingsymbol', 'current_position', 'MarkToMarket']).to_csv(self.pnl_file, index=False)
        
        if not os.path.exists(self.trades_file):
            pd.DataFrame(columns=['timestamp', 'tradingsymbol', 'order_price', 'quantity', 'type', 'pnl']).to_csv(self.trades_file, index=False)
        # else:
        #     os.remove(self.trades_file)
        #     pd.DataFrame(columns=['timestamp', 'tradingsymbol', 'order_price', 'quantity', 'type', 'pnl']).to_csv(self.trades_file, index=False)


    def reset_files(self):
        """Reset the PnL and trades files"""
        if os.path.exists(self.pnl_file):
            os.remove(self.pnl_file)
        if os.path.exists(self.trades_file):
            os.remove(self.trades_file)
        
        self.setup_directories()
        
    def update_trading_symbols(self, token_list):
        exchanges = ['NFO', 'NSE', 'BSE', 'BFO']
        for exchange in exchanges:
            instruments = pd.DataFrame(self.kite.instruments(exchange))
            # self.instruments = instruments
            for token in token_list:
                try:
                    tradingsymbol = instruments[instruments['instrument_token'] == token]['tradingsymbol'].values[0]
                    self.trading_symbols[token] = tradingsymbol
                except IndexError:
                    # print(f"Token {token} not found in {exchange} instruments.")
                    continue
                except Exception as e:
                    print(f"Error processing token {token} in {exchange} instruments: {e}")
                    continue

    def update_tokens(self):
        self.data_tokens += self.get_NFO_tokens(
            tradingsymbols=self.config.get('NFO_symbols', []),
            expiry_codes=self.config.get('NFO_expiry_codes', []),  # 0 for nearest expiry, 1 for next expiry
            types=self.config.get('NFO_types', ['CE', 'PE'])  
        )
        self.data_tokens += self.get_NSE_tokens(
            tradingsymbols=self.config.get('NSE_symbols', [])
        )
        self.data_tokens += self.get_BSE_tokens(
            tradingsymbols=self.config.get('BSE_symbols', [])
        )
        self.data_tokens += self.get_BFO_tokens(
            tradingsymbols=self.config.get('BFO_symbols', []),
            expiry_codes=self.config.get('BFO_expiry_codes', []),  # 0 for nearest expiry, 1 for next expiry
            types=self.config.get('BFO_types', ['CE', 'PE'])  
        )
        # self.data_tokens += self.get_NSE_tokens(
        #     tradingsymbols=self.config['NSE_symbols']
        # )
        # self.data_tokens += self.get_BSE_tokens(
        #     tradingsymbols=self.config['BSE_symbols']
        # )
        # self.data_tokens += self.get_BFO_tokens(
        #     tradingsymbols=self.config['BFO_symbols'],
        #     expiry_codes=self.config['BFO_expiry_codes'],  # 1 for nearest expiry, 2 for next expiry
        #     types=self.config['BFO_types']  
        # )

        return

    def get_NFO_tokens(self,tradingsymbols,expiry_codes,types):
        if tradingsymbols is None or len(tradingsymbols) == 0:
            print("No trading symbols provided for NFO tokens.")
            return []
        # if expiry_codes is None or len(expiry_codes) == 0:
        #     print("No expiry codes provided for NFO tokens.")
        #     return []
        self.instruments_NFO = pd.DataFrame(self.kite.instruments('NFO'))
        
        # 0 is nearest expiry date, 1 is next expiry date
        tokens=[]
        for symbol in tradingsymbols:
            if symbol not in self.instruments_NFO['name'].values:
                print(f"Trading symbol {symbol} not found in NFO instruments.")
                continue
            
            instrument = self.instruments_NFO[(self.instruments_NFO['name'] == symbol)&(self.instruments_NFO['instrument_type'].isin(types))]
            # expiry_dates = sorted(pd.to_datetime(instrument['expiry'].unique()))
            # expiries = [date.strftime('%Y-%m-%d') for date in expiry_dates]
            if len(expiry_codes)>0:
                expiries = sorted(instrument['expiry'].unique())
                print(f"Expiries for {symbol}: {expiries}")
                # codes = {0: expiries[0], 1: expiries[1], 2: expiries[2]} if len(expiries) >= 3 else {0: expiries[0], 1: expiries[1]}

                codes = {i:expiries[i] for i in range(len(expiries))}
                print(f"Expiry codes for {symbol}: {codes}")
                for expiry_code in expiry_codes:
                    token = instrument[instrument['expiry'] == codes[expiry_code]]['instrument_token'].values
                    for t in token:
                        tokens.append(t)
                    if token.size > 0:
                        print(f"Found NFO token for {symbol} with expiry {expiry_code}: {token[0]}")
                    else:
                        print(f"No NFO token found for {symbol} with expiry {expiry_code}.")
            else:
                token = instrument['instrument_token'].values
                for t in token:
                    tokens.append(t)
                

        # if len(tokens)>0:
        #     print(tokens)
        #     self.update_trading_symbols(tokens,'NFO')
        
        return tokens
    
    def get_NSE_tokens(self,tradingsymbols):
        """Get NSE tokens for the given trading symbols"""

        if tradingsymbols is None or len(tradingsymbols) == 0:
            print("No trading symbols provided for NSE tokens.")
            return []
        self.instruments_NSE = pd.DataFrame(self.kite.instruments('NSE'))
        tokens = []
        for symbol in tradingsymbols:
            if symbol not in self.instruments_NSE['tradingsymbol'].values:
                print(f"Trading symbol {symbol} not found in NSE instruments.")
                continue
            
            instrument = self.instruments_NSE[self.instruments_NSE['tradingsymbol'] == symbol]
            token = instrument['instrument_token'].values[0]
            tokens.append(token)
            # if tokens.size > 0:
            #     print(f"Found NSE token for {symbol}: {tokens[0]}")
            # else:
            #     print(f"No NSE token found for {symbol}.")
        # if len(tokens)>0:
        #     self.update_trading_symbols(tokens,'NSE')
        return tokens
    
    def get_BSE_tokens(self,tradingsymbols):
        """Get BSE tokens for the given trading symbols"""  
        if tradingsymbols is None or len(tradingsymbols) == 0:
            print("No trading symbols provided for BSE tokens.")
            return []
        self.instruments_BSE = pd.DataFrame(self.kite.instruments('BSE'))
        tokens = []
        for symbol in tradingsymbols:
            if symbol not in self.instruments_NSE['tradingsymbol'].values:
                print(f"Trading symbol {symbol} not found in NSE instruments.")
                continue
            
            instrument = self.instruments_NSE[self.instruments_NSE['tradingsymbol'] == symbol]
            token = instrument['instrument_token'].values[0]
            tokens.append(token)
            if token.size > 0:
                print(f"Found NSE token for {symbol}: {token[0]}")
            else:
                print(f"No NSE token found for {symbol}.")
        # if len(tokens)>0:   
        #     self.update_trading_symbols(tokens,'BSE')
        return tokens
    
    def get_BFO_tokens(self,tradingsymbols,expiry_codes,types):
        """Get BFO tokens for the given trading symbols"""
        if tradingsymbols is None or len(tradingsymbols) == 0:
            print("No trading symbols provided for BFO tokens.")
            return []
        self.instruments_BFO = pd.DataFrame(self.kite.instruments('BFO'))
        tokens = []

        for symbol in tradingsymbols:
            if symbol not in self.instruments_BFO['name'].values:
                print(f"Trading symbol {symbol} not found in NFO instruments.")
                continue
            
            instrument = self.instruments_BFO[(self.instruments_BFO['name'] == symbol)&(self.instruments_BFO['instrument_type'].isin(types))]
            # expiry_dates = sorted(pd.to_datetime(instrument['expiry'].unique()))
            # expiries = [date.strftime('%Y-%m-%d') for date in expiry_dates]
            expiries = sorted(instrument['expiry'].unique())
            print(f"Expiries for {symbol}: {expiries}")
            # codes = {0: expiries[0], 1: expiries[1], 2: expiries[2]} if len(expiries) >= 3 else {0: expiries[0], 1: expiries[1]}
            codes = {i:expiries[i] for i in range(len(expiries))}
            print(f"Expiry codes for {symbol}: {codes}")
            for expiry_code in expiry_codes:
                token = instrument[instrument['expiry'] == codes[expiry_code]]['instrument_token'].values
                try:
                    for t in token:
                        tokens.append(t)
                except Exception as e:
                    print(f"Error processing token for {symbol} with expiry {expiry_code}: {e}")
                    continue
                if token.size > 0:
                    print(f"Found NFO token for {symbol} with expiry {expiry_code}: {token[0]}")
                else:
                    print(f"No NFO token found for {symbol} with expiry {expiry_code}.")
        
        # if len(tokens)>0:
        #     self.update_trading_symbols(tokens,'BFO')

        return tokens

    def get_data(self):
        time_ordered_bars = {}

        # all_dates = get_all_dates(self.config['start_date'], self.config['end_date'])

        # def extract_data(token_list,dt):
        #     # current_ticks = []
        #     print(f"Thread processing data for tokens: {token_list}")
        #     for token in token_list:
        #         day_data = self.kite.historical_data(
        #             instrument_token=token,
        #                 from_date=dt,
        #                 to_date=dt,
        #                 interval=self.config['interval'],
        #                 oi=True
        #             )
        #         for tick in day_data:
        #             tick['instrument_token'] = token
        #             bar = BarData(**tick)
        #             timestamp = bar.date.strftime('%Y-%m-%d %H:%M:%S')
        #             if timestamp not in time_ordered_bars:
        #                 time_ordered_bars[timestamp] = []
        #             time_ordered_bars[timestamp].append(bar)
        #             # current_ticks.append(bar)
        #     return
        
        # def split_list(lst, n):
        #     return [lst[i::n] for i in range(n)]
        
        # for date in all_dates:
        #     market_times = get_minutewise_timestamp(date)
            
        #     for timestamp in market_times:
        #         if timestamp not in time_ordered_bars:
        #             time_ordered_bars[timestamp] = []

        #     token_split = split_list(self.data_tokens,10)
        #     threads = []
        #     for token_list in token_split:
        #         thread = threading.Thread(target=extract_data, args=(token_list,date))
        #         threads.append(thread)
        #         thread.start()
            
        #     for thread in threads:
        #         thread.join()
            
        #     print("All threads are done")

            

            # self.data_queue.put((current_ticks[0].date, current_ticks))
                        
                        # if timestamp not in time_ordered_bars:
                        #     time_ordered_bars[timestamp] = []
                        # time_ordered_bars[timestamp].append(bar)

        # ordered_queue = Queue()
        for token in self.data_tokens:
            day_data = self.kite.historical_data(
                instrument_token=token,
                from_date=self.config['start_date'],
                to_date=self.config['end_date'],
                interval=self.config['interval'],
                oi=True
            )
            for tick in day_data:
                tick['instrument_token'] = token
                bar = BarData(**tick)
                timestamp = bar.date
                
                if timestamp not in time_ordered_bars:
                    time_ordered_bars[timestamp] = []
                time_ordered_bars[timestamp].append(bar)

        # ordered_queue = Queue()
        for timestamp in sorted(time_ordered_bars.keys()):
            self.data_queue.put((timestamp, time_ordered_bars[timestamp]))
        
        return 
    # ordered_queue
        # return ordered_queue

    def process_bars(self):
        # while not self.stop_event.is_set():
        #     try:
        #         with self.lock:
        #             timestamp,bars = self.data_queue.get(timeout=1)
        #             # timestamp, bars = data_queue.get()
        #             self.update_bars(bars)
        #             print(f"Processed bars for {timestamp}")
        #             # self.log_positions(timestamp)

        #     except Exception as e:
        #         print(f"Error processing bars: {e}")
        while not self.data_queue.empty():
            timestamp, bars = self.data_queue.get()
            self.update_bars(bars)
            self.log_positions(timestamp)

    def log_positions(self, timestamp):
        for token, position_data in self.active_positions.items():
            position_row = [
                timestamp,
                self.trading_symbols[token],
                position_data['quantity'],
                position_data['MarkToMarket']
            ]
            with open(self.pnl_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(position_row)

    # @abstractmethod
    def update_bars(self, new_bars: List[BarData]):
        print(f"Updating {new_bars[0].date} bars")
        for b in new_bars:
            print(f"Updating bar: {b.date} for instrument {b.instrument_token}")
            self.check_all_conditions()

    # @abstractmethod
    def check_all_conditions(self):
        # Implement your strategy conditions here
        pass

    def on_backtest_end(self):
        pass

    def place_order(self, tick: BarData, quantity: int, order_type: str, price: float):
        """Place an order based on the tick data"""

        if order_type in ['BUY','buy']:
            pnl = -(price) * quantity
        else:
            pnl = (price) * quantity
        
        if tick.instrument_token not in self.traded_orders:
            self.traded_orders[tick.instrument_token] = {}
        if order_type not in self.traded_orders[tick.instrument_token]:
            self.traded_orders[tick.instrument_token][order_type] = {}


        self.traded_orders[tick.instrument_token][order_type] = {
            'order_price': price,
            'quantity': quantity,
            'tradingsymbol': self.trading_symbols[tick.instrument_token],
            'type': order_type,
            'pnl': pnl
            # Placeholder for PNL calculation
        }

        order = [
            [tick.date, self.trading_symbols[tick.instrument_token], price, quantity, 
             order_type, self.traded_orders[tick.instrument_token][order_type]['pnl']]
        ]
        with open(self.trades_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(order)
        

        self.active_positions[tick.instrument_token]['quantity'] += quantity if order_type == 'BUY' else -quantity
        self.active_positions[tick.instrument_token]['price'] = price
        # self.active_positions[tick.instrument_token]['MarkToMarket'] += (-quantity*price) if order_type == 'BUY' else quantity*price

    def calculate_metrics(self):
        return {
            'sharpe_ratio': self.calculate_sharpe(),
            'max_drawdown': self.calculate_drawdown()
        }

    def calculate_sharpe(self):
        if not os.path.exists(self.trades_file):
            return None
        
        trade_data = pd.read_csv(self.trades_file)
        if trade_data.empty:
            return None
        
        trade_data['returns'] = trade_data['realized_pnl'].pct_change()
        print(f"Sharpe Ratio: {trade_data['realized_pnl'].mean() / trade_data['realized_pnl'].std()}")
        # trade_data.to_csv(self.trades_file, index=False)
        return trade_data['returns'].mean() / trade_data['returns'].std()

    def calculate_drawdown(self):
        if not os.path.exists(self.trades_file):
            return None
        
        pnl_data = pd.read_csv(self.trades_file)
        if pnl_data.empty:
            return None
        
        # pnl_data['cumulative_pnl'] = pnl_data['pnl'].cumsum()
        running_max = pnl_data['realized_pnl'].cummax()
        drawdown = (pnl_data['realized_pnl'] - running_max) / running_max
        print(f"Maximum Drawdown: {drawdown.min()}")
        return drawdown.min()
    
    def calculate_pnl(self):
        if not os.path.exists(self.trades_file):
            return None
        
        trades = pd.read_csv(self.trades_file)
        if trades.empty:
            return None

        realized_pnl = 0.0
        pnl_history = []
        long_queue = []   # stores (price, quantity) of buys
        short_queue = []  # stores (price, quantity) of sells (shorts)

        for trade in trades.itertuples():
            qty = trade.quantity
            price = trade.order_price
            side = trade.type.upper()  # "BUY" or "SELL"

            if side == "BUY":
                # First, cover any short positions
                while qty > 0 and short_queue:
                    short_price, short_qty = short_queue[0]
                    match_qty = min(qty, short_qty)
                    pnl = (short_price - price) * match_qty  # short: sell high, buy low
                    realized_pnl += pnl

                    if match_qty == short_qty:
                        short_queue.pop(0)
                    else:
                        short_queue[0] = (short_price, short_qty - match_qty)

                    qty -= match_qty

                # Remaining quantity is a new long position
                if qty > 0:
                    long_queue.append((price, qty))

            elif side == "SELL":
                # First, close any long positions
                while qty > 0 and long_queue:
                    long_price, long_qty = long_queue[0]
                    match_qty = min(qty, long_qty)
                    pnl = (price - long_price) * match_qty  # long: buy low, sell high
                    realized_pnl += pnl

                    if match_qty == long_qty:
                        long_queue.pop(0)
                    else:
                        long_queue[0] = (long_price, long_qty - match_qty)

                    qty -= match_qty

                # Remaining quantity is a new short position
                if qty > 0:
                    short_queue.append((price, qty))

            pnl_history.append(realized_pnl)

        trades['realized_pnl'] = pnl_history
        print("Total pnl : {}".format(realized_pnl))
        trades.to_csv(self.trades_file, index=False)
        # total_pnl = trades["realized_pnl"].iloc[-1]
        # print(f"Total PnL: {total_pnl}")

        return realized_pnl
    
    def plot_results(self):
        trades = pd.read_csv(self.trades_file)
        trades['timestamp'] = pd.to_datetime(trades['timestamp'])
        trades.set_index('timestamp', inplace=True)

        plt.figure(figsize=(14, 7))
        plt.plot(trades['realized_pnl'], label='Strategy PnL', color='blue')
        plt.title('Strategy PnL Over Time')
        plt.xlabel('Time')
        plt.ylabel('PnL')
        plt.legend()
        plt.grid()
        plt.show()
        return

    def run(self):
        """Main method to run the backtest"""
        # self.update_trading_symbols()
        self.get_data()
        self.process_bars()

        self.on_backtest_end()

        # processing_thread = threading.Thread(target=self.process_bars)
        # processing_thread.daemon = True
        # processing_thread.start()

        # if self.get_data():
        #     self.stop_event.set()
        #     processing_thread.join()

        self.calculate_pnl()
        metrics = self.calculate_metrics()
        # return
        return metrics
    


# Example usage:
# if __name__ == "__main__":
#     end_date = datetime.now().strftime('%Y-%m-%d')
#     start_date = (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d')

#     config = {
#         'strategy_name': 'VWAP',
#         'exchange': 'NSE',
#         'start_date': start_date,
#         'end_date': end_date,
#         'tokens': [14626050],
#         'bar_size': 'minute',
#     }

#     engine = BacktestEngine(config)
#     results = engine.run()
#     print(f"Backtest Results: {results}")

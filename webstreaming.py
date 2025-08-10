import logging
from kiteconnect import KiteTicker
from Bardata import BarData
from datetime import datetime, timedelta
import os
import csv
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# with open('/Users/sushrutkagde/Documents/ZerodhaAPI/access_token.txt','r') as file:
#     access_token = file.read()
kws = KiteTicker(api_key='s4huxmt59th45biy',access_token=os.getenv('access_token'))
# bank_nifty = 260105
# nifty = 256265
# # ATM_strike = None

# instruments = pd.read_csv('/Users/sushrutkagde/Documents/ZerodhaAPI/instrument_tokens/instruments_NFO.csv')
# symbol = 'BANKNIFTY'
# strike_gap=100

# tokens = []


# def add_tokens(close):
#     atm_strike = close['last_price']
#     expiry = instruments.loc[instruments['name']==symbol,'expiry'].values
#     expiry_futures = instruments.loc[(instruments['name']==symbol)&(instruments['instrument_type']=='FUT'),'expiry'].values

#     expiry = np.sort(expiry)
#     weekly = expiry[0]

#     instrument_token=instruments.loc[(instruments['name']==symbol)&(instruments['expiry']==weekly)&(instruments['strike']>=atm_strike-strike_gap)&(instruments['strike']<=atm_strike+strike_gap),'instrument_token'].values
#     instrument_token=instrument_token.tolist()
#     return instrument_token

def on_tick(ws,ticks):
    # logging.debug("Ticks: {}".format(ticks))
    # return ticks
    # ws.unsubscribe([738561])
    # ws.subscribe([265])
    # ws.set_mode(ws.MODE_FULL,[265])
    close = ticks[0]
    print(close)
    # curr = BarData(**close)
    # print(curr.volume_traded)
    # close_dict = curr.__dict__
    # vwap = ''
    # with open('/Users/sushrutkagde/Documents/ZerodhaAPI/indices/nifty.txt','r') as file:
    #     while vwap=='':
    #         try:
    #             vwap=file.read()
    #             vwap = float(vwap)
    #         except:
    #             vwap=''
    
    # close_dict['vwap'] = vwap
    # print(close_dict)

    # if len(tokens)==0:
    # tokens = add_tokens(close)
    # ws.subscribe(tokens)
    
    # future_token = instruments.loc[(instruments['name']==symbol)&(instruments['expiry']==nearest_future)&(instruments['instrument_type']=='FUT'),'instrument_token'].values
    # future_token = future_token[0] if len(future_token) > 0 else None
    # instrument_token.append(future_token)
    # for _, bar in close.iterrows():
    #       curr = BarData(**bar.to_dict())
    # curr_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # print(curr.exchange_timestamp==curr_time)
    # print(close)
    # csv_file = 'banknifty_27-09-24.csv'

    # file_exist = os.path.isfile(csv_file)

    # with open(csv_file,mode='a',newline='') as file:
    #     writer = csv.DictWriter(file, fieldnames=ticks[0].keys())
        
    #     # Write header only if file does not exist
    #     if not file_exist:
    #         writer.writeheader()
        
    #     # Write the data rows
    #     writer.writerows(ticks) 
    # if(curr.exchange_timestamp==curr_time):
    #     print(curr.exchange_timestamp,curr.last_price,"\n")

    # curr_time = datetime.now()
    # if curr_time>datetime(2024,9,27,15,30):
    #     ws.stop()
        # kws.on_close()

def on_connect(ws,response):
    ws.subscribe([136442372])
    ws.set_mode(ws.MODE_FULL,[136442372])

def on_close(ws,code,reason):
    ws.stop()

kws.on_ticks = on_tick
kws.on_connect = on_connect
kws.on_close = on_close


kws.connect()
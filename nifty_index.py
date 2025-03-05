import logging
from kiteconnect import KiteTicker
from Bardata import BarData
from datetime import datetime, timedelta
import os
import csv
import pandas as pd
import numpy as np


with open('/Users/sushrutkagde/Documents/Trading platform/access_token.txt','r') as file:
    access_token = file.read()

kws = KiteTicker(api_key='s4huxmt59th45biy',access_token=access_token)

instrument = pd.read_csv('/Users/sushrutkagde/Documents/Trading platform/instrument_tokens/instruments_NSE.csv')

index = {}
weights = weights = {6401: 0.64, 3861249: 0.92, 40193: 0.63, 60417: 1.3, 1510401: 3.03, 4267265: 1.18, 81153: 1.86, 4268801: 0.93, 98049: 0.88, 134657: 0.62, 2714625: 3.95, 140033: 0.64, 177665: 0.78, 5215745: 1.0, 225537: 0.71, 232961: 0.6, 315393: 0.9, 1850625: 1.64, 341249: 11.34, 119553: 0.66, 345089: 0.64, 348929: 0.95, 356865: 2.27, 1270529: 7.74, 424961: 4.16, 1346049: 0.82, 408065: 5.82, 3001089: 0.85, 492033: 2.35, 2939649: 3.73, 519937: 2.38, 2815745: 1.5, 2977281: 1.81, 4598529: 0.83, 633601: 1.0, 3834113: 1.38, 738561: 8.64, 5582849: 0.71, 1102337: 0.86, 779521: 2.62, 857857: 1.79, 2953217: 3.76, 878593: 0.67, 884737: 1.78, 895745: 1.21, 3465729: 0.86, 897537: 1.37, 502785: 1.45, 2952193: 1.16, 969473: 0.66}
nifty_value=0
factor = []
tokens = list(weights.keys())
tokens.append(256265)

vwap_dict = {token : [] for token in tokens}


def calculate_vwap(avg):

    curr_time = datetime.now()
    index_vwap = 0
    for token in tokens:
        if token==256265:
            continue
        filtered=[]
        filtered = [bar for bar in vwap_dict[token] if (curr_time-bar.exchange_timestamp)<timedelta(minutes=30)]
        if len(filtered)==0:
            return None
        volume = [bar.volume_traded for bar in filtered]
        volume = np.array(volume)
        prices = [bar.last_price for bar in filtered]
        prices = np.array(prices)
        vwap = np.dot(prices,volume)/np.sum(volume)
        index_vwap += vwap*weights[token]

    index_vwap = ((index_vwap/avg))

    # new_row=[filtered[0].exchange_timestamp,index_vwap]
    # print(new_row)
    
    return index_vwap



def on_tick(ws,ticks):
    close = ticks[0]
    # print(close)
    curr = BarData(**close)
    name  = instrument.loc[instrument['instrument_token']==curr.instrument_token,'tradingsymbol'].values[0]
    # print(index[curr.instrument_token].last_price,weights[curr.instrument_token])
    # print(len(weights))
    # if len(weights) == len(index):
    # if curr.instrument_token == 256265:
    #     nifty_value=curr.last_price
    # else:
    index[curr.instrument_token] = curr
    
    vwap_dict[curr.instrument_token].append(curr)
    if curr.instrument_token == 256265:
        with open('/Users/sushrutkagde/Documents/Trading platform/strategy_new/index.txt','w') as file:
            file.write(str(curr.last_price))
    index_price = 0
    for key in index.keys():
        # if key not in index.keys():
        #     print(key)
        #     continue
        if key == 256265:
            continue
        index_price += index[key].last_price*weights[key]
    # print(len(index),index_price,name)
    avg=1
    if 256265 in index.keys():
        # print(index_price,index[256265].last_price,len(index))
        if len(index)==len(tokens):
            # print(index_price/index[256265].last_price)
            factor.append(index_price/index[256265].last_price)
            moving_factor = factor[-100:]
            avg = sum(moving_factor)/len(moving_factor)
            # print(avg)
            # print(index_price/avg)


    with open('vwap.txt','w') as file:
        file.write(str(calculate_vwap(avg)))


def on_connect(ws,response):
    ws.subscribe(tokens)
    ws.set_mode(ws.MODE_FULL,tokens)

def on_close(ws,code,reason):
    ws.stop()

kws.on_ticks = on_tick
kws.on_connect = on_connect
kws.on_close = on_close



kws.connect()
from threading import *
import threading
from queue import Queue
from kiteconnect import KiteTicker, KiteConnect
# import time
from collections import defaultdict, deque
import os
import csv
from datetime import date, datetime, time, timedelta
import dotenv
from dotenv import load_dotenv
import logging
# from Bardata import BarData
from datetime import datetime, timedelta
import numpy as np
from scipy import stats

# from dotenv import load_dotenv
import pandas as pd
from scipy import optimize

from black_scholes_model import option_greeks

load_dotenv()

kws = KiteTicker(api_key='s4huxmt59th45biy',access_token=os.getenv('access_token'))
kite = KiteConnect(api_key=os.getenv('api_key'),access_token=os.getenv('access_token'))

# df = pd.DataFrame(kite.instruments('NFO'))
df = pd.read_csv('instruments_NFO.csv')

index = 0


def calculate_iv(strike,spot,rate,dte,option_type,option_price):
    def black_scholes_price(vol):
        d1 = (np.log(spot/strike) + (rate + 0.5*(vol**2))*dte)/(vol*np.sqrt(dte))
        d2 = (np.log(spot/strike) + (rate - 0.5*(vol**2))*dte)/(vol*np.sqrt(dte))
        nd1 = stats.norm.cdf(d1)
        nd2 = stats.norm.cdf(d2)

        n_d1 = stats.norm.pdf(-1*d1)
        n_d2 = stats.norm.pdf(-1*d2)
        # print(nd1)
        # print(nd2)
        price =0

        if option_type == 'CE':
            price = spot*nd1 - strike*np.exp(-rate*dte)*nd2
            # print(price)
            return (price-option_price), nd1

        elif option_type == 'PE':
            price = spot*n_d1 - strike*np.exp(-rate*dte)*n_d2
            return ( price-option_price), n_d1

    original_vol = 0.1
    new_vol = 0.5
    epsilon = 0.00001
    iteration=0
    maxiterations = 100

    while abs((new_vol - original_vol)/original_vol) > epsilon:
        if iteration >= maxiterations:
            print("Max iterations reached")
            break
        diff, nd1 = black_scholes_price(new_vol)
        # print(diff)
        vega = spot*nd1*np.sqrt(dte)
        original_vol = new_vol
        new_vol = new_vol - (diff/vega)
        iteration+=1

    gamma = nd1/(spot*new_vol*np.sqrt(dte))

    print(f"Delta: {nd1}")
    print(f"gamma: {gamma}")
    return new_vol



    
    # root = optimize.least_squares(black_scholes_price,0.1,bounds=(0,1)).x
    # return root

# print(calculate_iv(24900,24951.8,0.086038,3/365,'CE',180.35))






def on_tick(ws,ticks):

    close = ticks[0]
    # print(len(ticks))
    if close['instrument_token'] == 256265:
        global index 
        index= close['last_price']
        
    else:
        row = df[df['instrument_token'] == close['instrument_token']]

        # exp = datetime.combine(row['expiry'].values[0],time(15,30,00))
        # print(exp)
        # dte = exp - close['last_trade_time'] 
        # print(dte.total_seconds()/(365*86400))
        if not index == 0:
            os.system('clear')
            print(f"Spot: {index}")
            print(f"strike: {row['strike'].values[0]}")
            expiry = datetime.strptime(row['expiry'].values[0],"%Y-%m-%d") + timedelta(hours=15,minutes=30)
            print(f"Expiry: {expiry}")
            time_to_expiry = expiry - close['last_trade_time']
            print(f"Time to expiry: {time_to_expiry}")
            dte = time_to_expiry.total_seconds()/(365*86400)  # convert to years
            print(f"DTE: {dte}")
            # iv = calculate_iv(row['strike'].values[0],index,0.086038,dte,row['instrument_type'].values[0],close['last_price'])

            iv, delta, gamma = option_greeks(spot=index,strike=row['strike'].values[0],rate=0.086038,dte=dte,option_type=row['instrument_type'].values[0],option_price=close['last_price'])
            print(f"Delta: {delta}")
            print(f"Gamma: {gamma}")
            print(f"Implied volatility: {iv}")


def on_connect(ws,response):
    ws.subscribe([10248962,256265])
    ws.set_mode(ws.MODE_FULL,[10248962,256265])

def on_close(ws,code,reason):
    ws.stop()

kws.on_ticks = on_tick
kws.on_connect = on_connect
kws.on_close = on_close


kws.connect()
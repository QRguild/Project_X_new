import os
import csv
from datetime import date, datetime, time, timedelta
from datetime import datetime, timedelta
import numpy as np
from scipy import stats



def option_greeks(spot, strike, rate, dte, option_type, option_price):

    def black_scholes_price(vol):
        d1 = (np.log(spot/strike) + (rate + 0.5*(vol**2))*dte)/(vol*np.sqrt(dte))
        d2 = (np.log(spot/strike) + (rate - 0.5*(vol**2))*dte)/(vol*np.sqrt(dte))
        nd1 = stats.norm.cdf(d1)
        nd2 = stats.norm.cdf(d2)

        n_d1 = 1-nd1
        n_d2 = 1-nd2
        # print(nd1)
        # print(nd2)
        price =0

        if option_type == 'CE':
            price = spot*nd1 - strike*np.exp(-rate*dte)*nd2
            # print(price)
            return (price-option_price), nd1

        elif option_type == 'PE':
            price =  strike*np.exp(-rate*dte)*n_d2 - spot*n_d1
            return (price-option_price), n_d1

    original_vol = 0.1
    new_vol = 0.5
    epsilon = 0.00001
    iteration=0
    maxiterations = 100
    vega = 0.0

    while abs((new_vol - original_vol)/original_vol) > epsilon:
        if iteration >= maxiterations:
            # print("Max iterations reached")
            break
        diff, nd1 = black_scholes_price(new_vol)
        vega = spot*nd1*np.sqrt(dte)
        original_vol = new_vol
        new_vol = new_vol - (diff/vega)
        iteration+=1

    gamma = nd1/(spot*new_vol*np.sqrt(dte))
    n__d1 = np.exp(-0.5*(nd1**2))/np.sqrt(2*np.pi)
    vega1 = spot*n__d1*np.sqrt(dte)/100

    # print(f"Delta: {nd1}")
    # print(f"gamma: {gamma}")
    return new_vol, nd1, gamma, vega1

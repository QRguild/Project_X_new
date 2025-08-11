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
            return (price-option_price), n_d2

    original_vol = 0.1
    new_vol = 0.5
    epsilon = 0.00001
    iteration=0
    maxiterations = 100
    vega1 = 0.0

    while abs((new_vol - original_vol)/original_vol) > epsilon:
        if iteration >= maxiterations:
            # print("Max iterations reached")
            break
        diff, nd1 = black_scholes_price(new_vol)
        vega1 = spot*nd1*np.sqrt(dte)
        original_vol = new_vol
        new_vol = new_vol - (diff/vega1)
        iteration+=1

    d1 = (np.log(spot/strike) + (rate + 0.5*(new_vol**2))*dte)/(new_vol*np.sqrt(dte))
    d2 = (np.log(spot/strike) + (rate - 0.5*(new_vol**2))*dte)/(new_vol*np.sqrt(dte))
    gamma = nd1/(spot*new_vol*np.sqrt(dte))
    n__d1 = np.exp(-0.5*(d1**2))/np.sqrt(2*np.pi)
    vega = spot*n__d1*np.sqrt(dte)

    # print(f"Delta: {nd1}")
    # print(f"gamma: {gamma}")
    return new_vol, nd1, gamma, vega


# Basic validations
# option_type = option_type.upper()
# if option_type not in ('CE', 'PE'):
#     raise ValueError("option_type must be 'CE' or 'PE'")
# if spot <= 0 or strike <= 0:
#     raise ValueError("spot and strike must be positive")
# if dte <= 0:
#     # At expiry, greeks are ill-defined; return edge-case values
#     return 0.0, (1.0 if (option_type=='CE' and spot>strike) else (0.0 if option_type=='CE' else (-1.0 if spot<strike else 0.0))), 0.0, 0.0

# def bs_price_delta_gamma_vega(vol):
#     if vol <= 0:
#         vol = 1e-8
#     sqrtT = np.sqrt(dte)
#     vsqrtT = vol * sqrtT
#     d1 = (np.log(spot/strike) + (rate + 0.5*vol*vol)*dte) / vsqrtT
#     d2 = d1 - vsqrtT

#     Nd1 = norm.cdf(d1)
#     Nd2 = norm.cdf(d2)
#     nd1 = norm.pdf(d1)  # standard normal PDF at d1
#     disc = np.exp(-rate * dte)

#     if option_type == 'CE':
#         price = spot * Nd1 - strike * disc * Nd2
#         delta = Nd1
#     else:
#         price = strike * disc * norm.cdf(-d2) - spot * norm.cdf(-d1)
#         delta = Nd1 - 1.0  # put delta

#     gamma = nd1 / (spot * vsqrtT)
#     vega = spot * nd1 * sqrtT  # per 1.00 vol (not per 1%)
#     return price, delta, gamma, vega, d1, d2

# # Newton-Raphson for IV
# vol = max(iv_init, 1e-4)
# for _ in range(max_iter):
#     price, _, _, vega, _, _ = bs_price_delta_gamma_vega(vol)
#     diff = price - option_price
#     if abs(diff) < tol:
#         break
#     if vega < 1e-12:
#         # Flat vega: break to avoid blow-up
#         break
#     step = diff / vega
#     vol = max(1e-8, vol - step)  # keep vol positive
#     # Optional damping if diverging
#     if vol > 5.0:  # cap at very high vol to stabilize
#         vol = 5.0

# # Final greeks at the solved vol
# price, delta, gamma, vega, _, _ = bs_price_delta_gamma_vega(vol)
# return vol, delta, gamma, vega

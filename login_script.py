from kiteconnect import KiteConnect
import os
import dotenv
from dotenv import load_dotenv,set_key
load_dotenv()
kite  = KiteConnect(api_key=os.getenv("api_key"))
print(kite.login_url())

request_token = input("Enter Your Request Token Here : ")
session = kite.generate_session(request_token, api_secret=os.getenv("api_secret"))
set_key('.env','access_token',session['access_token'])

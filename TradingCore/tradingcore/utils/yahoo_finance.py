import pandas as pd
import yfinance as yf

def fetch_yahoo_finance_data(symbol: str, interval: str, period: str = None, start: str = None, end: str = None):
    ticker = yf.Ticker(symbol)
    
    if period:
        data = ticker.history(interval=interval, period=period)
    elif start:
        if end:
            data = ticker.history(interval=interval, start=start, end=end)
        else:
            data = ticker.history(interval=interval, start=start)
    else:
        raise ValueError("You must provide either period or start with optional end dates.")
    
    return data
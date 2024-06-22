import pandas as pd
import yfinance as yf

def fetch_yahoo_finance_data(symbol: str, start: str = '2000-01-01'):
    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start)
    return data

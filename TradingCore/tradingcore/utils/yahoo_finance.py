import os
import pickle
import yfinance as yf
from datetime import datetime, timedelta

def load_cached_data(ticker):
    cache_folder = 'cache'
    cache_file = os.path.join(cache_folder, f'{ticker}_1h.pkl')
    
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            cached_data = pickle.load(f)
        return cached_data
    return None

def fetch_yahoo_finance_data(ticker: str, interval: str, period: str = None, start: str = None, end: str = None):
    ticker = yf.Ticker(ticker)
    
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

def check_tickers_exist(tickers):
    valid_tickers = []
    invalid_tickers = []
    
    for ticker in tickers:
        cached_data = load_cached_data(ticker)
        
        if cached_data is not None:
            print(f"Using cached data for {ticker}")
            data = cached_data
        else:
            #print(f"Fetching data for {ticker} from Yahoo Finance...")
            # Example: Fetch data for the last 1 month with daily interval
            data = fetch_yahoo_finance_data(ticker, interval='1d', period='1mo')
        
        if data is not None and not data.empty:
            valid_tickers.append(ticker)
        else:
            invalid_tickers.append(ticker)
    
    return valid_tickers, invalid_tickers
import pandas as pd
import os
import pickle
from datetime import datetime, timedelta, timezone
import logging
from tradingcore.utils.yahoo_finance import fetch_yahoo_finance_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeSeriesData:
    ALLOWED_INTERVALS = {'1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d'}

    def __init__(self, ticker: str, interval: str, cache_dir: str = 'cache'):
        self.ticker = ticker
        if interval not in self.ALLOWED_INTERVALS:
            raise ValueError(f"Interval '{interval}' is not allowed. Allowed values are: {', '.join(self.ALLOWED_INTERVALS)}")
        self.interval = interval
        self.period = self.calc_period()
        self.cache_dir = cache_dir
        self.data = self.load_data().drop_duplicates(subset=['Close'], keep='first')

    def load_data(self):
        # Load data from cache if available
        cache_path = os.path.join(self.cache_dir, f"{self.ticker}_{self.interval}.pkl")
        if os.path.exists(cache_path):
            logging.debug(f"Loading data from cache: {cache_path}")
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        else:
            logging.debug(f"No cache found. Fetching new data for {self.ticker} with interval {self.interval}")
            return self.fetch_new_data()

    def fetch_new_data(self):
        # Fetch new data from Yahoo Finance
        logging.debug(f"Fetching new data for {self.ticker} with interval {self.interval} and period {self.period}")
        data = fetch_yahoo_finance_data(self.ticker, self.interval, self.period)
        self.cache_data(data)
        return data

    def cache_data(self, data):
        # Cache the fetched data
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        cache_path = os.path.join(self.cache_dir, f"{self.ticker}_{self.interval}.pkl")
        logging.debug(f"Caching data to {cache_path}")
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
    
    def delete_old_data(self, cutoff_date):
        # Delete data older than cutoff_date
        logging.debug(f"Deleting data older than {cutoff_date}")    
        if cutoff_date.tzinfo == None:             
            logging.error(f"Naive datetime object, timezone is {cutoff_date.tzinfo}") 
        else:
            self.data = self.data[self.data.index >= cutoff_date]
            self.cache_data(self.data)

    def update_data(self):
        # Update data by fetching new data if needed
        last_date = self.data.index[-1]
        last_date_dt = pd.to_datetime(last_date)        
        cutoff_date = self.calculate_cutoff_date()
        self.delete_old_data(cutoff_date)

        if last_date_dt < cutoff_date:
            logging.debug("Last data point is before cutoff date. Fetching new data for the entire period.")
            self.data = self.fetch_new_data().drop_duplicates(subset=['Close'], keep='first')
        elif timedelta(hours=1) < (datetime.now(timezone.utc) - last_date_dt):
            logging.debug("Last data point is after cutoff date. Fetching incremental data.")
            new_data = fetch_yahoo_finance_data(ticker=self.ticker, start=last_date, end=datetime.now(timezone.utc).strftime('%Y-%m-%d'), interval=self.interval)
            self.data = pd.concat([self.data, new_data]).drop_duplicates(subset=['Close'], keep='first')
            
        self.cache_data(self.data)

    def calc_period(self):
        # Calculate the period based on interval
        if self.interval == '1m':
            return '7d'
        elif self.interval in ['60m', '1h', '1d']:
            return '2y'
        else:
            return '1mo'
    
    def calculate_cutoff_date(self) -> datetime:
        # Calculate the cutoff date based on the period
        if self.period == '7d':
            return datetime.now(timezone.utc) - timedelta(days=7)
        elif self.period == '2y':
            return datetime.now(timezone.utc) - timedelta(days=730)
        else:  # Default to '1mo'
            return datetime.now(timezone.utc) - timedelta(days=30)

import pandas as pd
import os
import pickle
from datetime import datetime
from TradingCore.utils.yahoo_finance import fetch_yahoo_finance_data

class TimeSeriesData:
    def __init__(self, symbol: str, cache_dir: str = 'cache'):
        self.symbol = symbol
        self.cache_dir = cache_dir
        self.data = self.load_data()

    def load_data(self):
        cache_path = os.path.join(self.cache_dir, f"{self.symbol}.pkl")
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        else:
            return self.fetch_new_data()

    def fetch_new_data(self):
        data = fetch_yahoo_finance_data(self.symbol)
        self.cache_data(data)
        return data

    def cache_data(self, data):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        cache_path = os.path.join(self.cache_dir, f"{self.symbol}.pkl")
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)

    def update_data(self):
        last_date = self.data.index[-1]
        new_data = fetch_yahoo_finance_data(self.symbol, start=last_date)
        self.data = pd.concat([self.data, new_data])
        self.cache_data(self.data)

import pandas as pd
import os
import pickle
from datetime import datetime, timedelta, timezone
import logging
from tradingcore.utils.yahoo_finance import fetch_yahoo_finance_data
from tradingcore.utils.postgresql import init_database, connect_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeSeriesData:
    ALLOWED_INTERVALS = {'1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d'}

    def __init__(self, ticker: str, interval: str):

        # Initialize postgresql database
        init_database()

        self.ticker = ticker
        if interval not in self.ALLOWED_INTERVALS:
            raise ValueError(f"Interval '{interval}' is not allowed. Allowed values are: {', '.join(self.ALLOWED_INTERVALS)}")
        self.interval = interval
        self.period = self.calc_period()
        self.data = self.load_data().drop_duplicates(subset=['Open'], keep='first')

    def load_data(self):

        # Load data from PostgreSQL if available
        conn = connect_db()
        query = """
        SELECT * FROM DataTimeSeries
        WHERE ticker = %s AND interval = %s
        ORDER BY date ASC
        """
        try:
            data = pd.read_sql(query, conn, params=(self.ticker, self.interval))
            conn.close()
            if not data.empty:
                logging.debug(f"Loaded data from PostgreSQL for {self.ticker} with interval {self.interval}")
                return data
            else:
                logging.debug(f"No data found in PostgreSQL for {self.ticker} with interval {self.interval}")
                return self.fetch_new_data()
        except Exception as e:
            logging.error(f"Error loading data from PostgreSQL: {e}")
            conn.close()
            return self.fetch_new_data()

    def fetch_new_data(self):
        # Fetch new data from Yahoo Finance
        logging.debug(f"Fetching new data for {self.ticker} with interval {self.interval} and period {self.period}")
        data = fetch_yahoo_finance_data(self.ticker, self.interval, self.period)
        self.cache_data(data)
        return data

    def cache_data(self, data):

        # Cache the fetched data into PostgreSQL
        conn = connect_db()
        cursor = conn.cursor()

        # Insert the data into PostgreSQL table
        for index, row in data.iterrows():
            cursor.execute("""
            INSERT INTO DataTimeSeries (date, ticker, interval, open, high, low, close, volume, dividends, stock_splits)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, ticker, interval) DO NOTHING
            """, (row['Date'], self.ticker, self.interval, row['Open'], row['High'], row['Low'], row['Close'],
                  row['Volume'], row['Dividends'], row['Stock Splits']))
        conn.commit()
        cursor.close()
        conn.close()
        logging.debug(f"Cached data to PostgreSQL for {self.ticker} with interval {self.interval}")

    
    def delete_old_data(self, cutoff_date):
        # Delete data older than cutoff_date
        logging.debug(f"Deleting data older than {cutoff_date}")
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
        DELETE FROM DataTimeSeries
        WHERE date < %s AND ticker = %s AND interval = %s
        """, (cutoff_date, self.ticker, self.interval))
        conn.commit()
        cursor.close()
        conn.close()

    def update_data(self):
        # Update data by fetching new data if needed
        last_date = self.data.index[-1]
        last_date_dt = pd.to_datetime(last_date)        
        cutoff_date = self.calculate_cutoff_date()
        self.delete_old_data(cutoff_date)

        if last_date_dt < cutoff_date:
            logging.debug("Last data point is before cutoff date. Fetching new data for the entire period.")
            self.data = self.fetch_new_data().drop_duplicates(subset=['Open'], keep='first')
        elif timedelta(hours=1) >= (datetime.now(timezone.utc) - last_date_dt):
            logging.debug("Last data point is after cutoff date. Fetching incremental data.")
            new_data = fetch_yahoo_finance_data(ticker=self.ticker, start=last_date, end=datetime.now(timezone.utc).strftime('%Y-%m-%d'), interval=self.interval)
            self.data = pd.concat([self.data, new_data]).drop_duplicates(subset=['Open'], keep='first')
            
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

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
        self.conn = connect_db()
        self.data = self.load_data().drop_duplicates(subset=['Open'], keep='first')
        

    def load_data(self):

        query = """
        SELECT date, open, high, low, close, volume
        FROM DataTimeSeries
        WHERE ticker = %s AND interval = %s
        ORDER BY date ASC
        """
        try:
            data = pd.read_sql_query(query, self.conn, index_col='date', params=(self.ticker, self.interval))
            if not data.empty:
                logging.info(f"Loaded data from PostgreSQL for {self.ticker} with interval {self.interval}")        
   
                data = data.rename(columns={'open': 'Open', 'close': 'Close', 'high': 'High', 'low': 'Low', 'volume': 'Volume'})
                return data
            else:
                logging.info(f"No data found in PostgreSQL for {self.ticker} with interval {self.interval}")
                new_data = self.fetch_new_data()
                return new_data
        except Exception as e:
            logging.error(f"Error loading data from PostgreSQL: {e}")
            new_data = self.fetch_new_data()
            return new_data

    def fetch_new_data(self):
        # Fetch new data from Yahoo Finance
        logging.info(f"Fetching new data for {self.ticker} with interval {self.interval} and period {self.period}")
        data = fetch_yahoo_finance_data(self.ticker, self.interval, self.period)
        self.cache_data(data)
        return data

    def cache_data(self, data):

        cursor = self.conn.cursor()

        # Insert the data into PostgreSQL table
        for index, row in data.iterrows():
            cursor.execute("""
            INSERT INTO DataTimeSeries (date, ticker, interval, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, ticker, interval) DO NOTHING
            """, (index, self.ticker, self.interval, row['Open'], row['High'], row['Low'], row['Close'],
                  row['Volume']))
        self.conn.commit()
        cursor.close()
        logging.info(f"Cached data to PostgreSQL for {self.ticker} with interval {self.interval}")

    
    def delete_old_data(self, cutoff_date):
        # Delete data older than cutoff_date
        logging.debug(f"Deleting data older than {cutoff_date}")
        cursor = self.conn.cursor()
        cursor.execute("""
        DELETE FROM DataTimeSeries
        WHERE date < %s AND ticker = %s AND interval = %s
        """, (cutoff_date, self.ticker, self.interval))
        self.conn.commit()
        cursor.close()

    def update_data(self):
        # Update data by fetching new data if needed
        last_date = pd.to_datetime(self.data.index[-1])
        cutoff_date = self.calculate_cutoff_date()
        self.delete_old_data(cutoff_date)

        if last_date < cutoff_date:
            logging.debug("Last data point is before cutoff date. Fetching new data for the entire period.")
            self.data = self.fetch_new_data().drop_duplicates(subset=['Open'], keep='first')
        else:
            new_data = fetch_yahoo_finance_data(ticker=self.ticker, start=last_date, interval=self.interval)
            if (new_data.index[-1] - last_date) >= timedelta(hours=1) :
                logging.debug("Last data point is after cutoff date. Fetching incremental data.")                
                self.data = pd.concat([self.data, new_data]).drop_duplicates(subset=['Open'], keep='first')
                self.data.index = pd.to_datetime(self.data.index)
            
        self.cache_data(self.data)
        self.conn.close()

    def calc_period(self):
        # Calculate the period based on interval
        if self.interval == '1m':
            return '7d'
        elif self.interval in ['60m', '1h', '1d']:
            return '1y'
        else:
            return '1mo'
    
    def calculate_cutoff_date(self) -> datetime:
        # Calculate the cutoff date based on the period
        if self.period == '7d':
            return datetime.now(timezone.utc) - timedelta(days=7)
        elif self.period == '1y':
            return datetime.now(timezone.utc) - timedelta(days=365)
        else:  # Default to '1mo'
            return datetime.now(timezone.utc) - timedelta(days=30)

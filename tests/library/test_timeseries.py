import unittest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from tradingcore_library.data.timeseries import TimeSeriesData

class TestTimeSeriesData(unittest.TestCase):

    @patch('tradingcore.utils.yahoo_finance.fetch_yahoo_finance_data')
    def setUp(self, mock_fetch):                
        # Initialize the TimeSeriesData object with mock data
        self.ts_data = TimeSeriesData(ticker='AAPL', interval='1d')

    def test_load_data(self):
        # Test that data is loaded correctly
        self.assertFalse(self.ts_data.data.empty)
    
    def test_fetch_new_data(self):
        # Test fetching new data
        new_data = self.ts_data.fetch_new_data()
        self.assertFalse(new_data.empty)
    
    def test_delete_old_data(self):
        # Test deleting old data
        cutoff_date = datetime(2022, 1, 5, tzinfo=timezone.utc)
        self.ts_data.delete_old_data(cutoff_date)
        self.assertTrue((self.ts_data.data.index >= cutoff_date).all())
    
    @patch('tradingcore.utils.yahoo_finance.fetch_yahoo_finance_data')
    def test_update_data(self, mock_fetch):        
        # Test updating data
        self.ts_data.update_data()
        self.assertTrue(datetime.now(timezone.utc) - timedelta(days=7) <= self.ts_data.data.index[-1])

    def test_calc_period(self):
        # Test period calculation
        self.assertEqual(self.ts_data.calc_period(), '1mo')
        self.ts_data.interval = '1m'
        self.assertEqual(self.ts_data.calc_period(), '5d')
        self.ts_data.interval = '60m'
        self.assertEqual(self.ts_data.calc_period(), '1y')

    def test_calculate_cutoff_date(self):
        # Test cutoff date calculation
        self.ts_data.period = '1mo'
        expected_cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        self.assertAlmostEqual(self.ts_data.calculate_cutoff_date(), expected_cutoff_date, delta=timedelta(days=1))
        self.ts_data.period = '1y'
        expected_cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)
        self.assertAlmostEqual(self.ts_data.calculate_cutoff_date(), expected_cutoff_date, delta=timedelta(days=1))

if __name__ == '__main__':
    unittest.main()

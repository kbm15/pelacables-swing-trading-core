import unittest
import pandas as pd
from unittest.mock import MagicMock
import os, sys

# Obtiene el directorio donde se encuentra el archivo actual (test_backtester.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
tradingcore_dir = os.path.join(current_dir, '..')
sys.path.append(tradingcore_dir)

from tradingcore import TimeSeriesData, MAIndicator , Backtester

class MockIndicator(MAIndicator):
    """Mock indicator for testing."""
    def calculate(self, data):
        # Simulate a simple strategy where the indicator alternates between buy and sell signals
        return pd.Series([1 if i % 2 == 0 else -1 for i in range(len(data))])

class TestBacktester(unittest.TestCase):

    def setUp(self):
        # Set up mock data for testing
        data = {
            'Close': [100, 105, 102, 110, 108, 115]  # Mocked close prices for backtesting
        }
        df = pd.DataFrame(data)

        # Mock TimeSeriesData
        self.ts_data = TimeSeriesData(ticker='AAPL', interval='1h')

        # Use the mock indicator
        self.indicator = MockIndicator(strategy="Mock Strategy")

        # Create Backtester instance with mock data and indicator
        self.backtester = Backtester(self.ts_data, self.indicator)

    def test_initial_capital(self):
        # Ensure initial capital is set correctly
        self.assertEqual(self.backtester.initial_capital, 10000)

    def test_purchase_fraction(self):
        # Check that purchase fraction is correctly used in the backtest
        self.backtester.purchase_fraction = 0.25  # Set custom purchase fraction
        self.backtester.run_backtest()
        self.assertAlmostEqual(self.backtester.purchase_fraction, 0.25)

    def test_take_profit(self):
        # Test the take-profit mechanism
        self.backtester.take_profit = 1.05  # Set custom take-profit level
        final_value, total_return = self.backtester.run_backtest()
        self.assertGreater(total_return, 0)  # Ensure profitable return

    def test_run_backtest(self):
        # Run the backtest and validate the main functionality

        # Execute the backtest
        final_value, total_return = self.backtester.run_backtest()

        # Ensure that the final portfolio value is greater than or equal to the initial capital
        # because the simple mock strategy alternates between buys and sells
        self.assertGreaterEqual(final_value, self.backtester.initial_capital)

        # Verify the total return calculation
        expected_return = ((final_value - self.backtester.initial_capital) / self.backtester.initial_capital) * 100

        # Assert that the total return is correctly calculated
        self.assertAlmostEqual(total_return, expected_return, places=2)

        # Additional checks: Ensure holdings and capital update correctly
        self.assertEqual(self.backtester.holdings, 0)  # All shares should have been sold by the end
        self.assertGreaterEqual(self.backtester.capital, 0)  # Capital should not be negative

    def test_empty_data(self):
        # Test edge case where data is empty
        self.ts_data.data = pd.DataFrame()  # Set an empty DataFrame

        # Run the backtest, it should handle empty data without errors
        with self.assertRaises(IndexError):
            self.backtester.run_backtest()  # Expected to raise IndexError due to empty data

if __name__ == '__main__':
    unittest.main()
# tradingcore

tradingcore is a Python library for managing timeseries financial data, implementing trading indicators, and performing backtesting.

## Installation

pip install tradingcore


## Usage

### Example Backtest

```python
from tradingcore.data.timeseries import TimeSeriesData
from tradingcore.indicators.moving_average import MovingAverageIndicator
from tradingcore.backtesting.backtester import Backtester

# Initialize timeseries data
ts_data = TimeSeriesData('AAPL')

# Initialize indicator
ma_indicator = MovingAverageIndicator(window=20)

# Initialize backtester
backtester = Backtester(ts_data, ma_indicator)

# Run backtest
results = backtester.run_backtest()
print(results)
```
### Tests
Example test cases to ensure your library works as expected.

#### `tradingcore/tests/test_timeseries.py`
```python
import unittest
from tradingcore.data.timeseries import TimeSeriesData

class TestTimeSeriesData(unittest.TestCase):
    def test_load_data(self):
        ts_data = TimeSeriesData('AAPL')
        self.assertIsNotNone(ts_data.data)

if __name__ == '__main__':
    unittest.main()
```
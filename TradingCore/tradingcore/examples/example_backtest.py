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

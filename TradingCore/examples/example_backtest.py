from TradingCore.data.timeseries import TimeSeriesData
from TradingCore.indicators.moving_average import MovingAverageIndicator
from TradingCore.backtesting.backtester import Backtester

# Initialize timeseries data
ts_data = TimeSeriesData('AAPL')

# Initialize indicator
ma_indicator = MovingAverageIndicator(window=20)

# Initialize backtester
backtester = Backtester(ts_data, ma_indicator)

# Run backtest
results = backtester.run_backtest()
print(results)

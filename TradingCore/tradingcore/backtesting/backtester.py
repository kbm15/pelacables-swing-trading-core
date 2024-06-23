from tradingcore.data.timeseries import TimeSeriesData
from tradingcore.indicators.base import Indicator

class Backtester:
    def __init__(self, data: TimeSeriesData, indicator: Indicator):
        self.data = data
        self.indicator = indicator

    def run_backtest(self):
        data_with_signals = self.indicator.calculate(self.data.data)
        # Implement backtest logic here
        return data_with_signals

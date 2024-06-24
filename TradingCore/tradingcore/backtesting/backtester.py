from tradingcore.data.timeseries import TimeSeriesData
from tradingcore.indicators.base import Indicator
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Backtester:
    def __init__(self, tsdata: TimeSeriesData, indicator: Indicator, initial_capital: float = 10000.0, purchase_fraction: float = 1.0, sell_fraction: float = 1.0):
        self.tsdata = tsdata
        self.indicator = indicator
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.holdings = 0.0
        self.purchase_fraction = purchase_fraction
        self.sell_fraction = sell_fraction
        self.data = []


    def run_backtest(self):
        logging.debug(f'Starting indicator {self.indicator.strategy} on {self.tsdata.ticker}')
        self.data = self.indicator.calculate(self.tsdata.data).tolist()

        self.capital = self.initial_capital
        self.holdings = 0.0

        logging.debug(f'Running backtest {self.indicator.strategy} on {self.tsdata.ticker}')
        # Backtest logic here
        max_holdings = self.holdings
        for i in range(1, len(self.tsdata.data)):            
            if (self.capital > 0.0) and (self.data[i] == 1):  # Comprar
                amount_to_spend = min(self.capital, max(self.initial_capital,self.capital) * self.purchase_fraction)
                shares_bought = amount_to_spend / self.tsdata.data['Close'].iloc[i]
                self.holdings += shares_bought
                self.capital -=  amount_to_spend
                # Logica para vender fracciones
                if  max_holdings < self.holdings:
                    max_holdings = self.holdings
            elif (self.holdings > 0.0) and (self.data[i] == -1):  # Vender
                shares_to_sell = min(self.holdings, max_holdings * self.sell_fraction)
                self.holdings -= shares_to_sell
                self.capital +=  shares_to_sell * self.tsdata.data['Close'].iloc[i]
                # Logica para vender fracciones
                if  self.holdings == 0:
                    max_holdings = self.holdings

        logging.debug(f'Finished backtest {self.indicator.strategy} on {self.tsdata.ticker}')
        final_portfolio_value = self.capital + self.holdings * self.tsdata.data['Close'].iloc[i]
        total_return = (final_portfolio_value - self.initial_capital) / self.initial_capital * 100
        return final_portfolio_value, total_return
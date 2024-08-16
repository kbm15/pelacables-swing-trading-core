from tradingcore.data.timeseries import TimeSeriesData
from tradingcore.indicators.base import BaseIndicator
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Backtester:
    def __init__(self, tsdata: TimeSeriesData, indicator: BaseIndicator, initial_capital: float = 10000.0, purchase_fraction: float = 0.5, sell_fraction: float = 0.5, take_profit: float = 1.04, backoff: int = 0):
        self.tsdata = tsdata
        self.indicator = indicator
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.holdings = 0.0
        self.purchase_fraction = purchase_fraction
        self.sell_fraction = sell_fraction
        self.data = []
        self.close = []
        self.only_profit = True
        self.take_profit = take_profit
        self.backoff = backoff



    def run_backtest(self):
        logging.debug(f'Starting indicator {self.indicator.strategy} on {self.tsdata.ticker}')
        self.data = self.indicator.calculate(self.tsdata.data).tolist()

        self.close = self.tsdata.data['Close'].tolist()

        self.capital = self.initial_capital
        self.holdings = 0.0

        logging.debug(f'Running backtest {self.indicator.strategy} on {self.tsdata.ticker}')
        # Backtest logic here
        max_holdings = self.holdings
        price_bought = 0.0        
        backoff_cnt = 0
        for i in range(1, len(self.tsdata.data)):            
            if self.backoff and backoff_cnt: backoff_cnt-=1
            if (self.capital > 0.0) and (self.data[i] == 1) and backoff_cnt == 0:  # Comprar
                amount_to_spend = min(self.capital, max(self.initial_capital,self.capital) * self.purchase_fraction)
                shares_bought = amount_to_spend / self.close[i]
                if self.only_profit:
                    price_bought = ((self.close[i] * shares_bought)+(price_bought*self.holdings))/(shares_bought+self.holdings)
                self.holdings += shares_bought
                self.capital -=  amount_to_spend
                backoff_cnt = self.backoff
                # Logica para vender fracciones
                if  max_holdings < self.holdings:
                    max_holdings = self.holdings
            elif (self.holdings > 0.0) and (self.data[i] == -1) and (price_bought * self.take_profit) < self.close[i] and backoff_cnt == 0:  # Vender
                shares_to_sell = min(self.holdings, max((max_holdings * self.sell_fraction),(self.initial_capital * self.purchase_fraction)))
                self.holdings -= shares_to_sell
                self.capital +=  shares_to_sell * self.close[i]
                backoff_cnt = self.backoff
                # Logica para vender fracciones
                if  self.holdings == 0:
                    max_holdings = self.holdings

        logging.debug(f'Finished backtest {self.indicator.strategy} on {self.tsdata.ticker}')
        final_portfolio_value = self.capital + self.holdings * self.close[i]
        total_return = (final_portfolio_value - self.initial_capital) / self.initial_capital * 100
        return final_portfolio_value, total_return
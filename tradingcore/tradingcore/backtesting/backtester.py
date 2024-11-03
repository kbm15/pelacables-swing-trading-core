from tradingcore.data.timeseries import TimeSeriesData
from tradingcore.indicators.base import BaseIndicator
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Backtester:
    def __init__(self, tsdata: TimeSeriesData, indicator: BaseIndicator, initial_capital: float = 10000.0, purchase_fraction: float = 0.5, sell_fraction: float = 0.5,days: int = 180, take_profit: float = 1.04):
        self.tsdata = tsdata
        self.indicator = indicator
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.holdings = 0.0
        self.purchase_fraction = purchase_fraction
        self.sell_fraction = sell_fraction
        self.days = days
        self.data = []
        self.open = []
        self.take_profit = take_profit


    def run_backtest(self):
        logging.debug(f'Starting indicator {self.indicator.strategy} on {self.tsdata.ticker}')
        
        last_date = self.tsdata.data.index[-1]
        period_delta = last_date - timedelta(days=self.days)
        
        self.data = self.indicator.calculate(self.tsdata.data).loc[period_delta:].tolist()
        self.open = self.tsdata.data.loc[period_delta:, 'Open'].tolist()

        self.capital = self.initial_capital
        self.holdings = 0.0

        logging.debug(f'Running backtest {self.indicator.strategy} on {self.tsdata.ticker}')
        # Backtest logic here
        max_holdings = self.holdings
        price_bought = 0.0        
        for i in range(len(self.data) - 1):  # Loop to len(data) - 2 to safely access open_prices[i + 1]
            if (self.capital > 0.0) and (self.data[i] == 1):  # Comprar
                amount_to_spend = min(self.capital, max(self.initial_capital,self.capital) * self.purchase_fraction)
                shares_bought = amount_to_spend / self.open[i+1]
                price_bought = ((self.open[i+1] * shares_bought)+(price_bought*self.holdings))/(shares_bought+self.holdings)
                self.holdings += shares_bought
                self.capital -=  amount_to_spend
                # Logica para vender fracciones
                if  max_holdings < self.holdings:
                    max_holdings = self.holdings
            elif (self.holdings > 0.0) and (self.data[i] == -1) and (price_bought * self.take_profit) < self.open[i+1]:  # Vender
                shares_to_sell = min(self.holdings, max((max_holdings * self.sell_fraction),(self.initial_capital * self.purchase_fraction)))
                self.holdings -= shares_to_sell
                self.capital +=  shares_to_sell * self.open[i+1]
                # Logica para vender fracciones
                if  self.holdings == 0:
                    max_holdings = self.holdings

        logging.debug(f'Finished backtest {self.indicator.strategy} on {self.tsdata.ticker}')
        final_portfolio_value = self.capital + self.holdings * self.open[i+1]
        total_return = (final_portfolio_value - self.initial_capital) / self.initial_capital * 100
        # self.upsert_backtest(total_return)
        return total_return
    
    def get_signal(self):
        if len(self.data) > 0 :
            if self.data[-1] == 1:
                return 'buy'
            elif self.data[-1] == -1:
                return 'sell'
        else:
            return None
from tradingcore.data.timeseries import TimeSeriesData
from tradingcore.indicators.base import Indicator
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Backtester:
    def __init__(self, tsdata: TimeSeriesData, indicator: Indicator, initial_capital: float = 10000.0, purchase_fraction: float = 0.25, sell_fraction: float = 0.25):
        self.tsdata = tsdata
        self.indicator = indicator
        self.capital = initial_capital
        self.holdings = 0.0
        self.purchase_fraction = purchase_fraction
        self.sell_fraction = sell_fraction
        self.data = pd.DataFrame(columns=['Portfolio Value', 'Holdings', 'Cash', 'Position'])


    def run_backtest(self):
        
        self.data['Position'] = self.indicator.calculate(self.tsdata.data)
        self.data['Portfolio Value'].iloc[0] = 0.0
        self.data['Holdings'].iloc[0] = self.holdings
        self.data['Cash'].iloc[0] = self.capital


        # Backtest logic here
        total_holdings = self.data['Holdings'].iloc[0]
        for i in range(1, len(self.tsdata.data)):
            if  total_holdings < self.data['Holdings'].iloc[i-1]:
                total_holdings = self.data['Holdings'].iloc[i-1]
            if self.data['Position'].iloc[i-1] == 1:  # Comprar
                amount_to_spend = min(self.data['Cash'].iloc[i-1], self.capital * self.purchase_fraction)
                shares_bought = amount_to_spend / self.tsdata.data['Open'].iloc[i]
                self.data.loc[self.data.index[i], 'Holdings'] = self.data['Holdings'].iloc[i-1] + shares_bought
                self.data.loc[self.data.index[i], 'Cash'] = self.data['Cash'].iloc[i-1] - amount_to_spend
                # self.data.loc[self.data.index[i], 'Take Profit'] = self.tsdata.data['Close'].iloc[i] * (1 + take_profit_pct)
                # self.data.loc[self.data.index[i], 'Stop Loss'] = self.tsdata.data['Close'].iloc[i] * (1 - stop_loss_pct)
            elif self.data['Position'].iloc[i] == -1:  # Vender
                # if self.tsdata.data['Close'].iloc[i] >= data['Take Profit'][i-1]:
                #     shares_to_sell = data['Holdings'].iloc[i-1] * self.sell_fraction
                #     self.data.loc[self.data.index[i], 'Cash'] = self.data['Cash'].iloc[i-1] + shares_to_sell * self.tsdata.data['Close'].iloc[i]
                #     self.data.loc[self.data.index[i], 'Holdings'] = self.data['Holdings'].iloc[i-1] - shares_to_sell
                # elif self.tsdata.data['Close'].iloc[i] <= data['Stop Loss'][i-1]:
                #     shares_to_sell = data['Holdings'].iloc[i-1] * self.sell_fraction
                #     self.data.loc[self.data.index[i], 'Cash'] = self.data['Cash'].iloc[i-1] + shares_to_sell * self.tsdata.data['Close'].iloc[i]
                #     self.data.loc[self.data.index[i], 'Holdings'] = self.data['Holdings'].iloc[i-1] - shares_to_sell
                # else:
                shares_to_sell = min(self.data['Holdings'].iloc[i-1], total_holdings * self.sell_fraction)
                self.data.loc[self.data.index[i], 'Holdings'] = self.data['Holdings'].iloc[i-1] - shares_to_sell
                self.data.loc[self.data.index[i], 'Cash'] = self.data['Cash'].iloc[i-1] + shares_to_sell * self.tsdata.data['Open'].iloc[i]
            else:  # Mantener
                self.data.loc[self.data.index[i], 'Holdings'] = self.data['Holdings'].iloc[i-1]
                self.data.loc[self.data.index[i], 'Cash'] = self.data['Cash'].iloc[i-1]
                # self.data.loc[self.data.index[i], 'Take Profit'] = self.data['Take Profit'][i-1]
                # self.data.loc[self.data.index[i], 'Stop Loss'] = self.data['Stop Loss'][i-1]

            self.data.loc[self.data.index[i], 'Portfolio Value'] = self.data['Cash'].iloc[i] + self.data['Holdings'].iloc[i] * self.tsdata.data['Close'].iloc[i]
            self.data.loc[self.data.index[i], 'Shares Owned'] = self.data['Holdings'].iloc[i]

        final_portfolio_value = self.data['Portfolio Value'].iloc[-1]
        total_return = (final_portfolio_value - self.capital) / self.capital * 100
        maximum_hold_return = self.tsdata.data['High'].max() /self.tsdata.data['Low'].min() * 100
        return final_portfolio_value, total_return, maximum_hold_return
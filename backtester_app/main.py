from tradingcore import TimeSeriesData, Backtester, ScreenerData, AwesomeOscillator,BollingerBands,IchimokuCloud,KeltnerChannel,MovingAverage,MACD,PSAR,RSI,StochasticOscillator,VolumeIndicator,Hold
from tradingcore.utils.yahoo_finance import check_tickers_exist
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from concurrent.futures import ThreadPoolExecutor, as_completed

# Updated load_tasks to include configurations
def load_tasks(tickers, indicators_strategies_path):
    # Load the indicators and strategies from the JSON file
    with open(indicators_strategies_path, 'r') as file:
        indicators_strategies = json.load(file)

    # Define all configurations we want to test
    config_variations = [
        {
            "take_profit": tp,
            "backoff": bf,
            "purchase_fraction": pf,
            "sell_fraction": sf
        }
        for tp in [1.00, 1.02, 1.05]          # Example take_profit values
        for bf in [0, 2, 5]                   # Example backoff values
        for pf in [0.33, 0.67, 1.0]            # Example purchase_fraction values
        for sf in [0.33, 0.67, 1.0]            # Example sell_fraction values
    ]

    # Generate task list
    tasks = []
    
    for ticker in tickers:
        task_count = 0
        for indicator, strategies in indicators_strategies.items():
            for strategy in strategies:
                if indicator == 'Hold':
                    task = {
                        "ticker": ticker,
                        "indicator": indicator,
                        "strategy": strategy,
                        "take_profit": 1.00,
                        "backoff": 0,
                        "purchase_fraction": 1.0,
                        "sell_fraction": 1.0,
                        "backtest": True
                    }
                    tasks.append(task)
                    task_count += 1
                    continue
                for config in config_variations:
                    task = {
                        "ticker": ticker,
                        "indicator": indicator,
                        "strategy": strategy,
                        **config,  # Merge the configuration settings into each task
                        "backtest": True
                    }
                    tasks.append(task)
                    task_count += 1
    return tasks, task_count

# Updated ResultAggregator to track best config per ticker
class ResultAggregator:
    def __init__(self, strategies_per_ticker: Dict[str, int]):
        self.responses = defaultdict(lambda: {'results': [], 'count': 0})
        self.strategies_per_ticker = strategies_per_ticker  # Expected counts per ticker

    def add_result(self, ticker: str, result_data: Dict):
        self.responses[ticker]['results'].append(result_data)
        self.responses[ticker]['count'] += 1
        # Print the total return of the Hold indicator
        if result_data['indicator'] == 'Hold':
            print(f"Total return for {ticker} with Hold indicator: {result_data.get('total_return', 0)}")
        # If all results for the ticker are collected, process the best result
        if self.responses[ticker]['count'] == self.strategies_per_ticker[ticker]:
            best_result = max(
                self.responses[ticker]['results'],
                key=lambda r: r.get('total_return', 0)
            )
            print(f"Best result for {ticker}: {best_result}")
            del self.responses[ticker]  # Clear data once processed

class IndicatorWorker:
    def __init__(self, task, ts):
        self.task = task
        self.ts = ts  # Shared TimeSeriesData instance

    def process_task(self):
        logging.debug(f"Processing task: {self.task}")
        
        # Use the shared TimeSeriesData instance directly
        indicator = globals()[self.task['indicator']]()
        indicator.setStrategy(self.task['strategy'])
        bs = indicator.calculate(self.ts.data)
        
        result_data = {
            "ticker": self.task["ticker"],
            "indicator": self.task["indicator"],
            "strategy": self.task["strategy"],
            "take_profit": self.task["take_profit"],
            "backoff": self.task["backoff"],
            "purchase_fraction": self.task["purchase_fraction"],
            "sell_fraction": self.task["sell_fraction"],
            "total_return": self.run_backtest(bs)
        }
        logging.debug(f"Completed task with result: {result_data}")
        return result_data
    
    def run_backtest(self, bs):
        initial_capital = 10000.0
        purchase_fraction = self.task["purchase_fraction"]
        sell_fraction = self.task["sell_fraction"]
        take_profit = self.task["take_profit"]
        backoff = self.task["backoff"]
        only_profit = True
        
        last_date = self.ts.data.index[-1]
        one_quarter_ago = last_date - timedelta(days=90)
        open_prices = self.ts.data.loc[one_quarter_ago:, 'Open'].tolist()
        data = bs.loc[one_quarter_ago:].tolist()
        
        capital = initial_capital
        holdings = 0.0
        price_bought = 0.0
        backoff_cnt = 0
        
        for i in range(len(data) - 2):  # Loop to len(data) - 2 to safely access open_prices[i + 1]
            if backoff and backoff_cnt:
                backoff_cnt -= 1
            
            if capital > 0.0 and data[i] == 1 and backoff_cnt == 0:
                # Buy at the next day's open price
                amount_to_spend = capital * purchase_fraction
                shares_bought = amount_to_spend / open_prices[i + 1]
                price_bought = ((open_prices[i + 1] * shares_bought) + (price_bought * holdings)) / (shares_bought + holdings) if only_profit and holdings > 0 else open_prices[i + 1]
                holdings += shares_bought
                capital -= amount_to_spend
                backoff_cnt = backoff
            
            elif holdings > 0.0 and data[i] == -1 and open_prices[i + 1] >= price_bought * take_profit and backoff_cnt == 0:
                # Sell at the next day's open price
                shares_to_sell = holdings * sell_fraction
                holdings -= shares_to_sell
                capital += shares_to_sell * open_prices[i + 1]
                backoff_cnt = backoff
        
        # Final portfolio calculation
        final_portfolio_value = capital + holdings * open_prices[-1]
        total_return = (final_portfolio_value - initial_capital) / initial_capital * 100
        return total_return



def main():
    ticker = 'NVDA'  # Single ticker for testing
    indicators_strategies_path = "indicators_strategies.json"
    
    # Load TimeSeriesData once and share it across tasks
    ts = TimeSeriesData(ticker=ticker, interval='1d')
    ts.update_data()  # Pre-fetch and store data for reuse

    # Load tasks with varying configurations for purchase and sell fractions
    tasks, _ = load_tasks([ticker], indicators_strategies_path)
    result_aggregator = ResultAggregator({ticker: len(tasks)})

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(IndicatorWorker(task, ts).process_task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            result_aggregator.add_result(result['ticker'], result)

if __name__ == "__main__":
    main()

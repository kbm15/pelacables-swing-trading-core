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
            "purchase_fraction": pf,
            "sell_fraction": sf
        }
        for tp in [1.00, 1.02, 1.05]          # Example take_profit values
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

        # Initialize the indicator
        indicator = globals()[self.task['indicator']]()
        indicator.setStrategy(self.task['strategy'])

        # Initialize Backtester with the provided parameters
        backtester = Backtester(
            tsdata=self.ts,
            indicator=indicator,
            initial_capital=10000.0,
            purchase_fraction=self.task["purchase_fraction"],
            sell_fraction=self.task["sell_fraction"],
            take_profit=self.task["take_profit"]
        )

        # Run the backtest and get the total return
        total_return = backtester.run_backtest()
        
        result_data = {
            "ticker": self.task["ticker"],
            "indicator": self.task["indicator"],
            "strategy": self.task["strategy"],
            "take_profit": self.task["take_profit"],
            "purchase_fraction": self.task["purchase_fraction"],
            "sell_fraction": self.task["sell_fraction"],
            "total_return": total_return
        }
        logging.debug(f"Completed task with result: {result_data}")
        return result_data

def main():
    ticker = 'AAPL'  # Single ticker for testing
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

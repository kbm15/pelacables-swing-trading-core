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

class ResultAggregator:
    def __init__(self, strategies_per_ticker: Dict[str, int]):
        # Each ticker has a list of responses and a total count of expected responses
        self.responses = defaultdict(lambda: {'results': [], 'count': 0})
        self.strategies_per_ticker = strategies_per_ticker  # Expected counts per ticker

    def add_result(self, ticker: str, result_data: Dict):
        self.responses[ticker]['results'].append(result_data)
        self.responses[ticker]['count'] += 1

        # If all results for the ticker are collected, process the best result
        if self.responses[ticker]['count'] == self.strategies_per_ticker[ticker]:
            best_result = max(
                self.responses[ticker]['results'],
                key=lambda r: r.get('total_return', 0)
            )
            print(f"Best result for {ticker}: {best_result}")
            del self.responses[ticker]  # Clear data once processed


    def send_best_result(self, best_result):
        # Send the best result to the database or a specific queue
        print(f"Sending best result for ticker {best_result['ticker']} with return {best_result['total_return']}")
        # You can push the result to another queue or write it to a database here


class IndicatorWorker(threading.Thread):
    def __init__(self, tasks):
        super().__init__()
        
        self.static_tasks = tasks
        logging.info(f"Initialized with static tasks.")

    def process_task(self, task_data):
        logging.info(f"Processing task: {task_data}")
        
        result_data = {}
        if 'ticker' in task_data and 'indicator' in task_data and 'strategy' in task_data:
            result_data['ticker'] = task_data['ticker']
            result_data['indicator'] = task_data['indicator']
            result_data['strategy'] = task_data['strategy']
            
            # Example time series data retrieval and indicator processing
            ts = TimeSeriesData(ticker=task_data['ticker'], interval='1d')
            ts.update_data()

            indicator = globals()[task_data['indicator']]()
            indicator.setStrategy(task_data['strategy'])
            bs = indicator.calculate(ts.data)
            
            if bs.iloc[-1] == 1:
                result_data['signal'] = 'buy'
            elif bs.iloc[-1] == -1:
                result_data['signal'] = 'sell'
            
            if task_data.get("backtest"):
                logging.info(f"Backtest task: {task_data}")
                result_data['total_return'] = self.run_backtest(ts, bs)
                result_data['signal'] = None
            else:
                logging.info(f"Indicator task: {task_data}")
        
        logging.info(f"Completed task with result: {result_data}")
        return result_data
        
    def run_backtest(self, ts, bs):
        initial_capital = 10000.0
        purchase_fraction = 1
        sell_fraction = 1
        take_profit = 1.02
        backoff = 0
        only_profit = True
        
        # Calculate the date one year ago from the last date in the time series
        last_date = ts.data.index[-1]
        one_year_ago = last_date - timedelta(days=365)
        one_quarter_ago = last_date - timedelta(days=90)    

        # Filter the 'Open' prices from one year ago to the last value
        open_prices = ts.data.loc[one_quarter_ago:, 'Open'].tolist()
        data = bs.loc[one_quarter_ago:].tolist()
        
        capital = initial_capital
        holdings = 0.0
        max_holdings = holdings
        price_bought = 0.0
        backoff_cnt = 0

        for i in range(0, len(data) - 1):
            if backoff and backoff_cnt:
                backoff_cnt -= 1
            if (capital > 0.0) and (data[i] == 1) and backoff_cnt == 0:
                amount_to_spend = min(capital, max(initial_capital, capital) * purchase_fraction)
                shares_bought = amount_to_spend / open_prices[i + 1]
                if only_profit:
                    price_bought = ((open_prices[i + 1] * shares_bought) + (price_bought * holdings)) / (shares_bought + holdings)
                holdings += shares_bought
                capital -= amount_to_spend
                backoff_cnt = backoff
                if max_holdings < holdings:
                    max_holdings = holdings
            elif (holdings > 0.0) and (data[i] == -1) and (price_bought * take_profit) < open_prices[i + 1] and backoff_cnt == 0:
                shares_to_sell = min(holdings, max((max_holdings * sell_fraction), (initial_capital * purchase_fraction)))
                holdings -= shares_to_sell
                capital += shares_to_sell * open_prices[i + 1]
                backoff_cnt = backoff
                if holdings == 0:
                    max_holdings = holdings

        final_portfolio_value = capital + holdings * open_prices[-1]
        total_return = (final_portfolio_value - initial_capital) / initial_capital * 100
        return total_return

    def start_consuming(self):
        logging.info(f"Starting local processing with static tasks.")
        for task_data in self.static_tasks:
            result_data = self.process_task(task_data)
            result_queue.put_nowait(result_data)

        logging.info(f"Completed processing all static tasks.")

def load_tasks(tickers, indicators_strategies_path):
    # Load the indicators and strategies from the JSON file
    with open(indicators_strategies_path, 'r') as file:
        indicators_strategies = json.load(file)

    # Generate task list
    tasks = []
    
    for ticker in tickers:
        length = 0
        for indicator, strategies in indicators_strategies.items():
            for strategy in strategies:
                tasks.append({
                    "ticker": ticker,
                    "indicator": indicator,
                    "strategy": strategy,
                    "backtest": True  # Set as needed
                })
                length += 1
    return tasks, length

result_queue = queue.Queue()
task_queue = queue.Queue()

def main():
    tickers = ['NVDA', 'MSFT']  # Example list of tickers
    indicators_strategies_path = "indicators_strategies.json"

    # Load tasks from tickers and indicator-strategy combinations
    tasks,length = load_tasks(tickers, indicators_strategies_path)
    worker = IndicatorWorker(tasks)

    result_aggregator = ResultAggregator({ticker: length for ticker in tickers})

    # Start the worker with the static tasks
    worker.start_consuming()

    for i in range(len(tasks)):
        result_data = result_queue.get(timeout=10)
        result_aggregator.add_result(result_data['ticker'], result_data)
        result_queue.task_done()
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

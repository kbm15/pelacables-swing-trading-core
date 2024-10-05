import time
from tradingcore_library import TimeSeriesData, Backtester, ScreenerData, AwesomeOscillator,BollingerBands,IchimokuCloud,KeltnerChannel,MovingAverage,MACD,PSAR,RSI,StochasticOscillator,VolumeIndicator
from tradingcore_library.utils.yahoo_finance import check_tickers_exist     
import pandas as pd
import json
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

indicators_strategies = {
  "AwesomeOscillator": ['SMA_Crossover'],
   "BollingerBands": ['Bollinger'],  
   "IchimokuCloud": ['Ichimoku', 'Kumo', 'KumoChikou', 'Kijun', 'KijunPSAR', 'TenkanKijun', 'KumoTenkanKijun', 'TenkanKijunPSAR', 'KumoTenkanKijunPSAR', 'KumoKiyunPSAR', 'KumoChikouPSAR', 'KumoKiyunChikouPSAR'],
   "KeltnerChannel": ['KC'],
   "MovingAverage": ['MA'],
   "MACD": ['MACD'],
   "PSAR": ['PSAR'],
   "RSI": ['RSI', 'RSI_Falling', 'RSI_Divergence', 'RSI_Cross'],
  "VolumeIndicator": ['Volume']
}


def backtest_ticker(ticker, ts):
    # results = pd.DataFrame(columns=['Ticker', 'BaseIndicator', 'Strategy', 'Valor final', 'Retorno total'])
    for indicator_name, strategies in indicators_strategies.items():
        # Dynamically create an instance of the indicator
        indicator = globals()[indicator_name]()
        backtest = Backtester(ts, indicator)

        for strategy in strategies:
            indicator.setStrategy(strategy)
            backtest.run_backtest()
    #         value, returned = backtest.run_backtest()
            logging.debug(f"Backtest result {indicator_name} on {strategy}")
    #         results.loc[len(results)]={
    #             'Ticker': ticker, 
    #             'Indicator': indicator_name, 
    #             'Strategy': strategy, 
    #             'Valor final': value, 
    #             'Retorno total': returned
    #         }
    
    #     returned = (ts.data['Close'].iloc[-1] - ts.data['Close'].iloc[0]) / ts.data['Close'].iloc[0] * 100    
    #     value = backtest.initial_capital * (returned/100 +1)
    #     results.loc[len(results)]={
    #             'Ticker': ticker, 
    #             'Indicator': indicator_name, 
    #             'Strategy': 'Hold', 
    #             'Valor final': value, 
    #             'Retorno total': returned
    #         }
    # logging.info(f"Backtest results: {results}")
    # return results


# Worker thread that runs and processes tasks from the queue
def worker():
    logging.info("Worker thread started and waiting for tasks...")
    while True:
        # Get a task from the queue
        ticker = task_queue.get()

        if ticker is None:
            logging.info("None received, worker is exiting...")
            task_queue.task_done()
            break  # Exit loop if None is received

        logging.info(f"Processing ticker: {ticker}")

        try:
            ts = TimeSeriesData(ticker=ticker, interval='1h')
            logging.info(f"TimeSeriesData created for ticker: {ticker}")

            # Submit the task to the executor for processing
            executor.submit(backtest_ticker, ticker, ts)
            logging.info(f"Task submitted for backtesting: {ticker}")


        except Exception as e:
            logging.error(f"Error while processing ticker {ticker}: {str(e)}")

        task_queue.task_done()

    logging.info("Worker thread has been stopped.")
        

# Initialize task and result queues 
task_queue = queue.Queue()
result_queue = queue.Queue()

# Define a ThreadPoolExecutor with a fixed number of threads
executor = ThreadPoolExecutor(max_workers=5)

# Shared data structure to store futures 
futures = []



# Define the FastAPI app with a lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the worker thread during the startup
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    
    # Yield control back to FastAPI (app runs here)
    yield
    
    # Optionally, cleanup during shutdown
    task_queue.put(None)  # Signal the worker to exit
    worker_thread.join()  # Ensure the worker thread finishes

app = FastAPI(lifespan=lifespan)





# Define an API endpoint to receive the data
@app.post("/add-screener/")
async def add_screener(data: ScreenerData):

    # Extract the ticker list from the received data
    tickers, trash = check_tickers_exist(data.tickers)
    logging.info(f"Loading tickers {tickers}, discarded {trash}")

    # Add the incoming data to the task queue
    for ticker in tickers:
        task_queue.put(ticker)
    
    # Return a response
    return {
        "received_tickers": tickers
    }

# Define an API endpoint to receive the data
@app.post("/add-ticker/")
async def add_ticker(data):

    ticker = data.ticker
    
    tickers, trash = check_tickers_exist([ticker])
    logging.info(f"Loading tickers {tickers}, discarded {trash}")

    if len(tickers) == 1:
        logging.info(f"Loading single ticker {ticker}")
        ts = TimeSeriesData(ticker=ticker, interval='1h')
        result = backtest_ticker(ticker=ticker, ts=ts, indicators_strategies=indicators_strategies)
        return result.to_json(orient="records")

    else:
        logging.error(f"Failed to load ticker from json {data}")
        return {
            "message": "Invalid ticker data"
        }
    
    


# Running the app using Uvicorn server (optional, useful when running locally)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# OLD 

""" results = threaded_backtest(ticker_list, indicators_strategies)

results.to_csv('result.csv', index=False)

# Calculate the average Retorno total per Strategy
average_ret_per_strategy = results.groupby('Strategy')['Retorno total'].mean().reset_index()
average_ret_per_strategy.columns = ['Strategy','Average Retorno total']
average_ret_per_strategy = average_ret_per_strategy.sort_values(by='Average Retorno total', ascending=False)

# Calculate the max Retorno total Strategy per Ticker
max_ret_per_ticker = results.loc[results.groupby('Ticker')['Retorno total'].idxmax()]
max_ret_per_ticker = max_ret_per_ticker[['Ticker','Strategy','Valor final','Retorno total']].reset_index(drop=True)
max_ret_per_ticker.columns = ['Ticker','Max Strategy','Max Valor final','Max Retorno total']
max_ret_per_ticker = max_ret_per_ticker.sort_values(by='Max Valor final', ascending=False)


print("Average Retorno total per Strategy (sorted):")
print(average_ret_per_strategy)
print("\nMax Retorno total Strategy per Ticker (sorted):")
print(max_ret_per_ticker)

logging.info(f"Finished batch") """
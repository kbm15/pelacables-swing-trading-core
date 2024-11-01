from datetime import datetime, timezone
from tradingcore import TimeSeriesData, Backtester, ScreenerData, AwesomeOscillator,BollingerBands,IchimokuCloud,KeltnerChannel,MovingAverage,MACD,PSAR,RSI,StochasticOscillator,VolumeIndicator,Hold

import queue
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TABLE_NAME = "backtest"

# DB Connection
def initialize_table():
    db_connection.execute(f'''
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker REAL NOT NULL UNIQUE,
                    added TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    return FLOAT NOT NULL                
                )
            ''')
    db_connection.commit()
    db_connection.close()
def upsert_backtest(ticker, ret, strategy, db_connection):

    # Convert the current datetime to a timestamp
    current_time = int(datetime.now(timezone.utc).timestamp())

    # First, check if the ticker exists in the table
    db_connection.execute("SELECT return FROM backtest WHERE ticker = ?", (ticker,))
    exists = db_connection.fetchone()

    if exists:
        # If the ticker exists, update the record
        db_connection.execute("""
            UPDATE backtest 
            SET added = ?, strategy = ?, return = ? 
            WHERE ticker = ?
        """, (current_time, strategy, ret, ticker))
    else:
        # If the ticker does not exist, insert a new record
        db_connection.execute("""
            INSERT INTO backtest (ticker, added, strategy, return)
            VALUES (?, ?, ?, ?)
        """, (ticker, current_time, strategy, ret))

    # Commit the transaction and close the connection
    db_connection.commit()

def check_updated(ticker, db_connection):

    updated = False
    # Convert the current datetime to a timestamp
    current_time = int(datetime.now(timezone.utc).timestamp())

    # First, check if the ticker exists in the table
    db_connection.execute("SELECT added FROM backtest WHERE ticker = ?", (ticker,))
    exists = db_connection.fetchone()

    if exists:
        added_time = datetime.fromtimestamp(exists[0], timezone.utc)
        if current_time - added_time.timestamp() < 604800:
            updated = True

    return updated

# Backtest thread function
def backtest_ticker(ticker, ts):
    # Read indicators_strategies.json
    with open('indicators_strategies.json') as f:
        indicators_strategies = json.load(f)
    previous_return = 0
    previous_strategy = None

    for indicator_name, strategies in indicators_strategies.items():
        # Dynamically create an instance of the indicator
        indicator = globals()[indicator_name]()
        backtest = Backtester(ts, indicator)

        for strategy in strategies:
            indicator.setStrategy(strategy)
            returned = backtest.run_backtest()
            if returned > previous_return:
                previous_return = returned
                previous_strategy = strategy
    result = {
        "ticker": ticker,
        "strategy": previous_strategy,
        "return": previous_return
    }
    return result

# Callback function for future results
def handle_future_result(future: Future):
    try:
        result = future.result()
        logging.debug(f"Backtest result received for ticker: {result['ticker']}")
        # Enqueue the result for further processing
        result_queue.put(result)
    except Exception as e:
        logging.error(f"Error in backtest task: {str(e)}")

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

        logging.debug(f"Processing ticker: {ticker}")

        try:
            ts = TimeSeriesData(ticker=ticker, interval='1h')
            logging.debug(f"TimeSeriesData created for ticker: {ticker}")

            # Submit the task to the executor for processing
            future = executor.submit(backtest_ticker, ticker, ts)

            # Attach callback
            future.add_done_callback(handle_future_result)

            # Optionally store the future
            futures.append(future)

            logging.debug(f"Task submitted for backtesting: {ticker}")


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


# DB Connection




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
    executor.shutdown(wait=True)


# Create the FastAPI app
app = FastAPI(lifespan=lifespan)



# Function to process results
def process_results():
    while True:
        try:
            result = result_queue.get(timeout=60)
            logging.info(f"Processed backtest result for {result}")
            # Here, you can store the result in a database or perform other actions
            if result['strategy'] is not None:
                upsert_backtest(result['ticker'], result['return'], result['strategy'], db_connection)
            result_queue.task_done()
        except queue.Empty:
            logging.info("No more results to process.")

            break


# Define an API endpoint to receive the data
@app.post("/add-screener/")
async def add_screener(data: ScreenerData, background_tasks: BackgroundTasks):

    # Extract the ticker list from the received data
    tickers, trash = check_tickers_exist(data.tickers)
    logging.info(f"Loading tickers {tickers}, discarded {trash}")

    # Add the incoming data to the task queue
    for ticker in tickers:
        task_queue.put(ticker)
    
    background_tasks.add_task(process_results)

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
        ts.update_data()
        result = backtest_ticker(ticker=ticker, ts=ts)
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
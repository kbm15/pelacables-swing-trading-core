from tradingcore import TimeSeriesData, Backtester, connect_db, init_database, AwesomeOscillator,BollingerBands,IchimokuCloud,KeltnerChannel,MovingAverage,MACD,PSAR,RSI,StochasticOscillator,VolumeIndicator,Hold

import pika
import logging
import requests  # For signaling the coordinator
import os
import orjson
from datetime import timedelta


RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
TASK_QUEUE = os.getenv('TASK_QUEUE', 'indicator_tasks')
RESULTS_QUEUE = os.getenv('RESULTS_QUEUE', 'indicator_results')
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_DB = os.getenv("POSTGRES_DB", "timeseries_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

print("Configuration Loaded:")
print(f"RABBITMQ_HOST = {RABBITMQ_HOST}")
print(f"TASK_QUEUE = {TASK_QUEUE}")
print(f"RESULTS_QUEUE = {RESULTS_QUEUE}")
print(f"POSTGRES_HOST = {POSTGRES_HOST}")
print(f"POSTGRES_DB = {POSTGRES_DB}")
print(f"POSTGRES_USER = {POSTGRES_USER}")
print(f"POSTGRES_PASSWORD = {POSTGRES_PASSWORD}")

logging.basicConfig(level=logging.INFO)

class IndicatorWorker:
    def __init__(self, instance_id, coordinator_url):
        self.instance_id = instance_id
        self.coordinator_url = coordinator_url
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=TASK_QUEUE, durable=True)
        self.channel.queue_declare(queue=RESULTS_QUEUE, durable=True)

        # Set QoS for load balancing
        self.channel.basic_qos(prefetch_count=1)

        self.db_connection = connect_db(POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
    def process_task(self, ch, method, properties, body):
        logging.info(f"[{self.instance_id}] Processing task: {body}")
        # Process the task 
        task_data = orjson.loads(body.decode('utf-8'))

        result_data = {
        "flag": task_data.get("flag", ""),
        "ticker": task_data.get("ticker", ""),
        "indicator": task_data.get("indicator", ""),
        "strategy": task_data.get("strategy", ""),
        "signals": {}
        }
        if 'ticker' in task_data and 'indicator' in task_data and 'strategy' in task_data:

            ts = TimeSeriesData(ticker=task_data['ticker'], interval='1d', db_connection=self.db_connection)
            ts.update_data()
            logging.info(f"Last data point: {ts.data.index[-1]}")
            indicator = globals()[task_data['indicator']]()
            indicator.setStrategy(task_data['strategy'])  

            # Run backtest
            if task_data['flag'] == 'backtest':
                logging.info(f"[{self.instance_id}] Backtest task: {body}")
                
                logging.debug(f'Starting backtest indicator {task_data['strategy']} on {task_data['ticker']}')
                days = 182
                if task_data['indicator'] == 'Hold':
                    last_date = ts.data.index[-1]
                    period_delta = last_date - timedelta(days=days)
                    ts.data = ts.data.loc[period_delta:].copy()

                # Configure Backtester instance
                backtester = Backtester(
                    tsdata=ts,
                    indicator=indicator,
                    initial_capital=10000.0,
                    purchase_fraction=task_data.get("purchase_fraction", 1.0),
                    sell_fraction=task_data.get("sell_fraction", 1.0),
                    take_profit=task_data.get("take_profit", 1.01)
                )

                result_data['total_return'] = backtester.run_backtest()
                timestamps = backtester.get_timestamps()
                data = backtester.data.copy()
                
                if len(timestamps) != len(data):
                    logging.error(f"Longitudes desiguales: timestamps ({len(timestamps)}) vs raw_signals ({len(data)})")
                else:
                    if len(data) == 0:                        
                        timestamps = ts.data.index[-1].tolist()
                        data = [0]         
                    signal = data[0]
                    buy_signals = signal == 1
                    result_data['signals'][str(timestamps[0].timestamp()*1000)] = signal
                    for i in range(len(timestamps)):
                        if data[i] != signal:
                            if data[i] == 1 and not buy_signals:
                                buy_signals = True
                            signal = data[i]
                            result_data['signals'][str(timestamps[i].timestamp()*1000)] = signal
                    if not buy_signals:
                        result_data['total_return'] = -100.0
                
                logging.debug(f'Finished backtest {task_data['strategy']} on {task_data['ticker']}')

            # Run indicator
            else:
                bs = indicator.calculate(ts.data)                
                signal = bs.iloc[-1]
                result_data['signals']={str(ts.data.index[-1].timestamp()*1000):signal}
                for i in range(1,len(bs)):
                    if bs.iloc[-i] != signal: 
                        result_data['signals'].update({str(ts.data.index[-i+1].timestamp()*1000):bs.iloc[-i+1]})
                        break
                        
                logging.debug(f'Finished indicator {task_data["strategy"]} on {task_data["ticker"]}')
            logging.info(f"Result data: {result_data}")
            self.channel.basic_publish(
                exchange='',
                routing_key=RESULTS_QUEUE,
                body=orjson.dumps(result_data, default=str),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                )
            )
        # Acknowledge message processing
        ch.basic_ack(delivery_tag=method.delivery_tag)
        # self.report_status()

    def report_status(self):
        # Report to coordinator (with queue depth or other relevant info)
        try:
            requests.post(f"{self.coordinator_url}/update_status", json={
                "instance_id": self.instance_id,
                "queue_depth": self.channel.queue_declare(queue=TASK_QUEUE, passive=True).method.message_count
            })
        except Exception as e:
            logging.error(f"Failed to report status: {e}")

    def start_consuming(self):
        self.channel.basic_consume(queue=TASK_QUEUE, on_message_callback=self.process_task)
        logging.info(f"[{self.instance_id}] Waiting for tasks...")
        self.channel.start_consuming()

    def stop(self):
        self.channel.stop_consuming()
        self.connection.close()
        self.db_connection.close()

if __name__ == "__main__":
    instance_id = "instance_1"  # Example; you could auto-generate this or use environment variables
    coordinator_url = f"http://{RABBITMQ_HOST}:5000"  # Coordinator URL for reporting status
    init_database(POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
    
    worker = IndicatorWorker(instance_id, coordinator_url)
    try:
        worker.start_consuming()
    except KeyboardInterrupt:
        worker.stop()
        logging.info("Worker stopped.")
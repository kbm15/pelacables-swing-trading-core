from tradingcore import TimeSeriesData, AwesomeOscillator,BollingerBands,IchimokuCloud,KeltnerChannel,MovingAverage,MACD,PSAR,RSI,StochasticOscillator,VolumeIndicator,Hold
import pika
import time
import logging
import json
import requests  # For signaling the coordinator
from decouple import config,UndefinedValueError

try:
    RABBITMQ_HOST = config('RABBITMQ_HOST')
    TASK_QUEUE = config('TASK_QUEUE')
    RESULTS_QUEUE = config('RESULTS_QUEUE')
except UndefinedValueError as e:
    # Handle the case where a variable is not defined in .env
    print(f"Error: {e}")
    exit(1)

print("Configuration Loaded:")
print(f"RABBITMQ_HOST = {RABBITMQ_HOST}")
print(f"TASK_QUEUE = {TASK_QUEUE}")
print(f"RESULTS_QUEUE = {RESULTS_QUEUE}")

logging.basicConfig(level=logging.INFO)

class IndicatorWorker:
    def __init__(self, instance_id, coordinator_url):
        self.instance_id = instance_id
        self.coordinator_url = coordinator_url
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=TASK_QUEUE, exchange_type='direct')
        self.channel.queue_declare(queue=RESULTS_QUEUE, durable=True)

        # Declare a unique queue for this instance
        self.queue_name = f"app_instance_queue_{instance_id}"
        self.channel.queue_declare(queue=self.queue_name, exclusive=True)
        self.channel.queue_bind(exchange=TASK_QUEUE, queue=self.queue_name)

        # Set QoS for load balancing
        self.channel.basic_qos(prefetch_count=1)

    def process_task(self, ch, method, properties, body):
        logging.info(f"[{self.instance_id}] Processing task: {body}")
        # Process the task 
        task_data = json.loads(body.decode('utf-8'))

        result_data = {}
        if 'ticker' in task_data and 'indicator' in task_data and 'strategy' in task_data:
            result_data['ticker'] = task_data['ticker']
            result_data['indicator'] = task_data['indicator']
            result_data['strategy'] = task_data['strategy']
            ts = TimeSeriesData(ticker=task_data['ticker'], interval='1h')
            ts.update_data()
            indicator = globals()[task_data['indicator']]()
            indicator.setStrategy(task_data['strategy'])
            bs = indicator.calculate(ts.data)
            if bs[-1] == 1:
                result_data['signal'] = 'buy'
            elif bs[-1] == -1:
                result_data['signal'] = 'sell'

            if 'backtest' in task_data and task_data['backtest']:
                logging.info(f"[{self.instance_id}] Backtest task: {body}")
                
                logging.debug(f'Starting backtest indicator {task_data['strategy']} on {task_data['ticker']}')
                
                result_data['total_return'] = self.run_backtest(ts, bs)
                result_data['signal'] = None
                
                logging.debug(f'Finished backtest {task_data['strategy']} on {task_data['ticker']}')
            else:
                logging.info(f"[{self.instance_id}] Indicator task: {body}")
            
            self.channel.basic_publish(
                exchange='',
                routing_key=RESULTS_QUEUE,
                body=json.dumps(result_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                )
            )
        time.sleep(1)
        # Acknowledge message processing
        ch.basic_ack(delivery_tag=method.delivery_tag)
        self.report_status()

    def report_status(self):
        # Report to coordinator (with queue depth or other relevant info)
        try:
            requests.post(f"{self.coordinator_url}/update_status", json={
                "instance_id": self.instance_id,
                "queue_depth": self.channel.queue_declare(queue=self.queue_name, passive=True).method.message_count
            })
        except Exception as e:
            logging.error(f"Failed to report status: {e}")

    def start_consuming(self):
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.process_task)
        logging.info(f"[{self.instance_id}] Waiting for tasks...")
        self.channel.start_consuming()

    def stop(self):
        self.channel.stop_consuming()
        self.connection.close()
    

    def run_backtest(self, ts, bs):
        initial_capital= 10000.0
        purchase_fraction = 0.5
        sell_fraction = 0.5
        take_profit = 1.04
        backoff = 0
        only_profit = True
        

        open= ts.data['Open'].tolist()[ 200 : ]
        data= bs.tolist()[ 200 : ]

        capital = initial_capital
        holdings = 0.0

        # Backtest logic here
        max_holdings = holdings
        price_bought = 0.0        
        backoff_cnt = 0
        for i in range(0, len(data)-1):            
            if backoff and backoff_cnt: backoff_cnt-=1
            if (capital > 0.0) and (data[i] == 1) and backoff_cnt == 0:  # Comprar
                amount_to_spend = min(capital, max(initial_capital,capital) * purchase_fraction)
                shares_bought = amount_to_spend / open[i+1]
                if only_profit:
                    price_bought = ((open[i+1] * shares_bought)+(price_bought*holdings))/(shares_bought+holdings)
                holdings += shares_bought
                capital -=  amount_to_spend
                backoff_cnt = backoff
                # Logica para vender fracciones
                if  max_holdings < holdings:
                    max_holdings = holdings
            elif (holdings > 0.0) and (data[i] == -1) and (price_bought * take_profit) < open[i+1] and backoff_cnt == 0:  # Vender
                shares_to_sell = min(holdings, max((max_holdings * sell_fraction),(initial_capital * purchase_fraction)))
                holdings -= shares_to_sell
                capital +=  shares_to_sell * open[i+1]
                backoff_cnt = backoff
                # Logica para vender fracciones
                if  holdings == 0:
                    max_holdings = holdings

        final_portfolio_value = capital + holdings * open[i+1]
        total_return = (final_portfolio_value - initial_capital) / initial_capital * 100
        return total_return

if __name__ == "__main__":
    instance_id = "instance_1"  # Example; you could auto-generate this or use environment variables
    coordinator_url = f"http://{RABBITMQ_HOST}:5000"  # Coordinator URL for reporting status
    worker = IndicatorWorker(instance_id, coordinator_url)

    try:
        worker.start_consuming()
    except KeyboardInterrupt:
        worker.stop()
        logging.info("Worker stopped.")
import json
import threading
import time
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import pika
import os

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
TASK_QUEUE = os.getenv('TASK_QUEUE', 'indicator_tasks')

# Variable global para almacenar los datos
initial_data = {
    "timestamps": [],
    "prices": [],
    "signals": []
}

# Ruta para el gráfico
@app.route('/grafico/<ticker>')
def grafico(ticker):
    """
    Renderiza la página para mostrar el gráfico de un determinado ticker.
    """
    # Puedes pasar `initial_data` o un conjunto de datos específico si es necesario
    return render_template('grafico.html', ticker=ticker, data=initial_data)

# Función para consumir mensajes de RabbitMQ
def rabbitmq_consumer():
    global initial_data
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    # Declarar la cola en caso de que no exista
    channel.queue_declare(queue=TASK_QUEUE, durable=True)

    def process_message(ch, method, properties, body):
        global initial_data
        try:
            message = json.loads(body)
            new_timestamp = message.get("timestamp")
            new_price = message.get("price")
            new_signal = message.get("signal")

            if new_timestamp and new_price is not None and new_signal is not None:
                # Actualizar los datos
                initial_data["timestamps"].append(new_timestamp)
                initial_data["prices"].append(new_price)
                initial_data["signals"].append(new_signal)

                # Limitar los datos a los últimos 100 puntos
                if len(initial_data["timestamps"]) > 100:
                    for key in initial_data.keys():
                        initial_data[key].pop(0)

                # Emitir los datos actualizados al frontend
                socketio.emit("update_chart", {
                    "timestamps": initial_data["timestamps"],
                    "prices": initial_data["prices"],
                    "signals": initial_data["signals"]
                })

            # Confirmar el mensaje procesado
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            ch.basic_nack(delivery_tag=method.delivery_tag)
            print(f"Error procesando el mensaje: {e}")

    # Configuración del consumidor
    channel.basic_consume(queue=TASK_QUEUE, on_message_callback=process_message)
    print("Esperando mensajes en RabbitMQ...")
    channel.start_consuming()

# Función para iniciar el consumidor de RabbitMQ en un hilo separado
def start_rabbitmq_thread():
    thread = threading.Thread(target=rabbitmq_consumer, daemon=True)
    thread.start()

# Iniciar el hilo de consumo de RabbitMQ cuando se ejecuta la aplicación
if __name__ == '__main__':
    start_rabbitmq_thread()
    socketio.run(app, host='0.0.0.0', port=5000)

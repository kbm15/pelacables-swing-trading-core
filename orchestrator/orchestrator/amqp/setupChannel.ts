// src/amqp/setupChannel.ts
import amqp from 'amqplib';
import { RABBITMQ_HOST, TICKER_REQUEST_QUEUE, TICKER_RESPONSE_QUEUE, TASK_QUEUE, RESULTS_QUEUE } from '../config';

export async function setupChannel() {
    const connection = await amqp.connect(RABBITMQ_HOST);
    const channel = await connection.createChannel();
    await channel.assertQueue(TICKER_REQUEST_QUEUE, { durable: true });
    await channel.assertQueue(TICKER_RESPONSE_QUEUE, { durable: true });
    await channel.assertQueue(RESULTS_QUEUE, { durable: true });
    await channel.assertExchange(TASK_QUEUE, 'direct', { durable: false });
    return channel;
}

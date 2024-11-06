// src/amqp/sendRequest.ts
import amqp from 'amqplib';
import { APP_INSTANCE_QUEUE, TASK_QUEUE } from '../config';

export async function sendRequest(channel: amqp.Channel, request: Request) {
    await channel.publish(TASK_QUEUE, APP_INSTANCE_QUEUE, Buffer.from(JSON.stringify(request)), { persistent: true });
}

// src/amqp/sendRequest.ts
import amqp from 'amqplib';
import type { Request } from '../types';
import {  TASK_QUEUE } from '../config';

export async function sendRequest(channel: amqp.Channel, request: Request) {
    await channel.sendToQueue(TASK_QUEUE, Buffer.from(JSON.stringify(request)), { persistent: true });
}

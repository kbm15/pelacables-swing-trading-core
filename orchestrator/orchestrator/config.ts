// src/config.ts
import dotenv from 'dotenv';

dotenv.config();

export const RABBITMQ_HOST = process.env.RABBITMQ_HOST!;
export const TICKER_REQUEST_QUEUE = process.env.TICKER_REQUEST_QUEUE!;
export const TASK_QUEUE = process.env.TASK_QUEUE!;
export const RESULTS_QUEUE = process.env.RESULTS_QUEUE!;
export const TICKER_RESPONSE_QUEUE = process.env.TICKER_RESPONSE_QUEUE!;
export const SCYLLA_HOST = process.env.SCYLLA_HOST!;
export const SCYLLA_KEYSPACE = process.env.SCYLLA_KEYSPACE!;
export const SCYLLA_DATACENTER = process.env.SCYLLA_DATACENTER!;
export const SCYLLA_USERNAME = process.env.SCYLLA_USERNAME!;
export const SCYLLA_PASSWORD = process.env.SCYLLA_PASSWORD!;
export const APP_INSTANCE_QUEUE = 'app_instance_queue_instance_1';
export const INDICATORS_STRATEGIES = { /* same as before */ };
export const TWO_WEEKS_MS = 14 * 24 * 60 * 60 * 1000;

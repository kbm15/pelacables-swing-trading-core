// src/config.ts

export const RABBITMQ_HOST = process.env.RABBITMQ_HOST!;
export const TICKER_REQUEST_QUEUE = process.env.TICKER_REQUEST_QUEUE!;
export const TASK_QUEUE = process.env.TASK_QUEUE!;
export const RESULTS_QUEUE = process.env.RESULTS_QUEUE!;
export const TICKER_RESPONSE_QUEUE = process.env.TICKER_RESPONSE_QUEUE!;
export const POSTGRES_HOST = process.env.POSTGRES_HOST!;
export const POSTGRES_DB = process.env.POSTGRES_DB!;
export const POSTGRES_USERNAME = process.env.POSTGRES_USERNAME!;
export const POSTGRES_PASSWORD = process.env.POSTGRES_PASSWORD!;
export const APP_INSTANCE_QUEUE = 'app_instance_queue_instance_1';

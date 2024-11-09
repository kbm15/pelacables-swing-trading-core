// src/config.ts

function loadEnvVariable(name: string): string {
    const value = process.env[name];
    if (!value) {
        console.error(`Environment variable ${name} is missing.`);
        process.exit(1);
    }
    return value;
}

export const RABBITMQ_HOST = loadEnvVariable('RABBITMQ_HOST');
export const TICKER_REQUEST_QUEUE = loadEnvVariable('TICKER_REQUEST_QUEUE');
export const TASK_QUEUE = loadEnvVariable('TASK_QUEUE');
export const RESULTS_QUEUE = loadEnvVariable('RESULTS_QUEUE');
export const TICKER_RESPONSE_QUEUE = loadEnvVariable('TICKER_RESPONSE_QUEUE');
export const POSTGRES_HOST = loadEnvVariable('POSTGRES_HOST');
export const POSTGRES_DB = loadEnvVariable('POSTGRES_DB');
export const POSTGRES_USER = loadEnvVariable('POSTGRES_USER');
export const POSTGRES_PASSWORD = loadEnvVariable('POSTGRES_PASSWORD');
export const APP_INSTANCE_QUEUE = 'app_instance_queue_instance_1';


import amqplib from 'amqplib';
import { loadEnvVariable } from '../utils/loadEnv';

// Load and validate necessary environment variables

const RABBITMQ_HOST = loadEnvVariable('RABBITMQ_HOST');
const TICKER_REQUEST_QUEUE = loadEnvVariable('TICKER_REQUEST_QUEUE');
const TICKER_RESPONSE_QUEUE = loadEnvVariable('TICKER_RESPONSE_QUEUE');
const NOTIFICATION_QUEUE = loadEnvVariable('NOTIFICATION_QUEUE');
export async function connectRabbitMQ() {
    try {        
        const connection = await amqplib.connect(RABBITMQ_HOST);
        const channel = await connection.createChannel();

        // Ensure queues exist
        await channel.assertQueue(TICKER_REQUEST_QUEUE, { durable: true });
        await channel.assertQueue(TICKER_RESPONSE_QUEUE, { durable: true });
        await channel.assertQueue(NOTIFICATION_QUEUE, { durable: true });

        
        console.log("Connected to RabbitMQ and queues initialized.");
        return channel;
    } catch (error) {
        console.error("Failed to connect to RabbitMQ:", error);
        process.exit(1);
    }
}
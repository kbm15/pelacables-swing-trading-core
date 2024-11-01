import amqp from 'amqplib';
import sqlite3 from 'sqlite3';
import { open, Database } from 'sqlite';

// Function to load environment variables
function loadEnvVariable(name: string): string {
    const value = process.env[name];
    if (!value) {
        console.error(`Environment variable ${name} is missing.`);
        process.exit(1);
    }
    return value;
}

// Load constants from environment variables
const RABBITMQ_HOST = loadEnvVariable('RABBITMQ_HOST');
const TICKER_REQUEST_QUEUE = loadEnvVariable('TICKER_REQUEST_QUEUE'); // Queue where we receive ticker requests
const TASK_QUEUE = loadEnvVariable('TASK_QUEUE'); // Direct exchange for indicator tasks
const RESULTS_QUEUE = loadEnvVariable('RESULTS_QUEUE'); // Queue to retrieve results from the indicator app
const TICKER_RESPONSE_QUEUE = loadEnvVariable('TICKER_RESPONSE_QUEUE'); // Queue to respond with results

const APP_INSTANCE_QUEUE = 'app_instance_queue_instance_1'

interface IndicatorStrategies {
    [indicator: string]: string[];
}

// Indicator strategies mapping
const INDICATORS_STRATEGIES: IndicatorStrategies = {
    "AwesomeOscillator": ["SMA_Crossover"],
    "BollingerBands": ["Bollinger"],
    "IchimokuCloud": ["Ichimoku", "Kumo", "KumoChikou", "Kijun", "KijunPSAR", "TenkanKijun", "KumoTenkanKijun", "TenkanKijunPSAR", "KumoTenkanKijunPSAR", "KumoKiyunPSAR", "KumoChikouPSAR", "KumoKiyunChikouPSAR"],
    "KeltnerChannel": ["KC"],
    "MovingAverage": ["MA"],
    // "MACD": ["MACD"],
    "PSAR": ["PSAR"],
    "RSI": ["RSI", "RSI_Falling", "RSI_Divergence", "RSI_Cross"],
    "VolumeIndicator": ["Volume"],
    "Hold": ["Hold"]
};

// Initialize SQLite database
async function initDatabase() {
    const db = await open({
        filename: 'indicators.db',
        driver: sqlite3.Database,
    });

    await db.exec(`CREATE TABLE IF NOT EXISTS best_indicators (
        ticker TEXT PRIMARY KEY,
        indicator TEXT,
        strategy TEXT,
        signal TEXT
    )`);

    console.log("Initialized SQLite database and ensured best_indicators table exists.");
    return db;
}
interface Request {
    ticker: string;
    indicator: string;
    strategy: string;
    backtest: boolean;
    userId: number;
    chatId: number;
}

// Function to send request to the indicator app via TASK_QUEUE
async function sendRequest(channel: amqp.Channel, request: Request) {
    
    console.log(`Sending request for ticker ${request.ticker}, indicator ${request.indicator}, strategy ${request.strategy} to TASK_QUEUE.`);
    
    await channel.publish(TASK_QUEUE, APP_INSTANCE_QUEUE, Buffer.from(JSON.stringify(request)), {
        persistent: true,
    });
}

interface Response {
    userId: number;
    ticker: string;
    indicator: string;
    strategy: string;
    signal: string;
    total_return: number | null;
    chatId: number | null;
}

interface UserResponseAggregator {
    chatId: number | null;
    timestamp: number;
    ticker:Response[] ;
}

interface ResponseAggregator {
    [userId: number]: UserResponseAggregator;
}

const responseAggregator: ResponseAggregator = {};

async function handleResponse(channel: amqp.Channel, message: amqp.Message, db: Database) {
    const response: Response   = JSON.parse(message.content.toString());


    // Ensure an entry for the userId and ticker
    if (!responseAggregator[response.userId]) {
        responseAggregator[response.userId] = { chatId: response.chatId, timestamp: Date.now(), ticker: [] };
    } 
    // Add the response to the ticker's list of responses
    responseAggregator[response.userId].ticker.push(response);

    // Check if we received all strategies for the ticker and indicator
    const expectedResponses = Object.values(INDICATORS_STRATEGIES).flat().length;

    console.log('Aggregating responses, expected responses:', expectedResponses,'received responses:', responseAggregator[response.userId].ticker.length);  

    // Process only if all responses are gathered
    if (responseAggregator[response.userId].ticker.length === expectedResponses) {
        // Find the response with the highest total_return
        const bestResponse = responseAggregator[response.userId].ticker.reduce((best, current) =>
            (current.total_return || 0) > (best.total_return || 0) ? current : best
        );

        // Save the best response to the database
        await saveBestIndicator(bestResponse, db);

        // Clear the aggregated responses for the processed ticker
        delete responseAggregator[response.userId];
    }

    // Acknowledge the message
    channel.ack(message);
}

// Function to save the best indicator in SQLite
async function saveBestIndicator(response: any, db: Database) {
    const { ticker, indicator, strategy, signal } = response;

    await db.run(`
        INSERT OR REPLACE INTO best_indicators (ticker, indicator, strategy, signal)
        VALUES (?, ?, ?, ?)`, [ticker, indicator, strategy, signal]);

    console.log(`Saved best indicator for ticker ${ticker}: ${indicator}, strategy: ${strategy}, signal: ${signal}.`);
}

// Function to get the best indicator from the database
async function getBestIndicator(ticker: string, db: Database) {
    const row = await db.get(`
        SELECT * FROM best_indicators WHERE ticker = ?`, [ticker]);

    return row || null;
}

// Main function to set up RabbitMQ and handle requests
async function main() {
    const db = await initDatabase();
    const connection = await amqp.connect(RABBITMQ_HOST);
    const channel = await connection.createChannel();

    // Assert the necessary queues
    await channel.assertQueue(TICKER_REQUEST_QUEUE, { durable: true });
    await channel.assertQueue(TICKER_RESPONSE_QUEUE, { durable: true });
    await channel.assertQueue(RESULTS_QUEUE, { durable: true });
    await channel.assertExchange(TASK_QUEUE, 'direct', { durable: false });

    console.log(`Connected to RabbitMQ and asserted queues: ${TICKER_REQUEST_QUEUE}, ${TICKER_RESPONSE_QUEUE}, ${RESULTS_QUEUE}.`);

    // Start consuming requests from TICKER_REQUEST_QUEUE
    channel.consume(TICKER_REQUEST_QUEUE, async (msg) => {
        if (msg) {
            console.log(`Received ticker request: ${msg.content.toString()}`);
            const { ticker, chatId, userId } = JSON.parse(msg.content.toString());

            console.log(`Received ticker request for: ${ticker}`);

            // Check for the best indicator in the database
            const bestIndicator = await getBestIndicator(ticker, db);

            if (!bestIndicator) {
                // If not found, send requests to all indicators and strategies
                console.log(`No best indicator found for ${ticker}. Sending requests to all indicators.`);
                for (const indicator in INDICATORS_STRATEGIES) {
                    for (const strategy of INDICATORS_STRATEGIES[indicator]) {
                        const request: Request = { ticker, indicator, strategy, backtest: false, userId, chatId };
                        await sendRequest(channel, request);
                    }
                }
            } else {
                // If found, send the cached indicator information to the TICKER_RESPONSE_QUEUE
                console.log(`Best indicator found for ${ticker}: ${bestIndicator.indicator}, strategy: ${bestIndicator.strategy}. Sending to TICKER_RESPONSE_QUEUE.`);
                const response = JSON.stringify({ ...bestIndicator, chatId, userId });
                console.log(response);
                await channel.sendToQueue(TICKER_RESPONSE_QUEUE, Buffer.from(response), {
                    persistent: false,
                });
            }

            // Acknowledge the message
            channel.ack(msg);
            console.log(`Acknowledged ticker request for: ${ticker}`);
        }
    }, { noAck: false });

    // Start consuming responses from the RESULTS_QUEUE
    channel.consume(RESULTS_QUEUE, async (msg) => {
        if (msg) {
            await handleResponse(channel, msg, db);
        }
    }, { noAck: false });
}

// Run the main function
main().catch(console.error);

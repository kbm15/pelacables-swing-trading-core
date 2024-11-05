import amqp from 'amqplib';
import cassandra from 'cassandra-driver';

const TWO_WEEKS_MS = 14 * 24 * 60 * 60 * 1000; // Two weeks in milliseconds

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
const TICKER_REQUEST_QUEUE = loadEnvVariable('TICKER_REQUEST_QUEUE');
const TASK_QUEUE = loadEnvVariable('TASK_QUEUE');
const RESULTS_QUEUE = loadEnvVariable('RESULTS_QUEUE');
const TICKER_RESPONSE_QUEUE = loadEnvVariable('TICKER_RESPONSE_QUEUE');

const SCYLLA_HOST = loadEnvVariable('SCYLLA_HOST');
const SCYLLA_KEYSPACE = loadEnvVariable('SCYLLA_KEYSPACE');
const SCYLLA_DATACENTER = loadEnvVariable('SCYLLA_DATACENTER');
const SCYLLA_USERNAME = loadEnvVariable('SCYLLA_USERNAME');
const SCYLLA_PASSWORD = loadEnvVariable('SCYLLA_PASSWORD');

const APP_INSTANCE_QUEUE = 'app_instance_queue_instance_1';


interface IndicatorStrategies {
    [indicator: string]: string[];
}

const INDICATORS_STRATEGIES: IndicatorStrategies = {
    "AwesomeOscillator": ["SMA_Crossover"],
    "BollingerBands": ["Bollinger"],
    "IchimokuCloud": ["Ichimoku", "Kumo", "KumoChikou", "Kijun", "KijunPSAR", "TenkanKijun", "KumoTenkanKijun", "TenkanKijunPSAR", "KumoTenkanKijunPSAR", "KumoKiyunPSAR", "KumoChikouPSAR", "KumoKiyunChikouPSAR"],
    "KeltnerChannel": ["KC"],
    "MovingAverage": ["MA"],
    "MACD": ["MACD"],
    "PSAR": ["PSAR"],
    "RSI": ["RSI", "RSI_Falling", "RSI_Divergence", "RSI_Cross"],
    "VolumeIndicator": ["Volume"],
    "Hold": ["Hold"]
};




async function initDatabase() {
    const cluster = new cassandra.Client({
        contactPoints: [SCYLLA_HOST],    
        localDataCenter: SCYLLA_DATACENTER,
        credentials: { username: SCYLLA_USERNAME, password: SCYLLA_PASSWORD }
    });
    const createKeyspaceQuery = `
        CREATE KEYSPACE IF NOT EXISTS ${SCYLLA_KEYSPACE}
        WITH REPLICATION = { 'class': 'SimpleStrategy', 'replication_factor': 1 }
        AND durable_writes = true;
    `;
    await cluster.execute(createKeyspaceQuery);
    console.log("Initialized Cassandra database.");
}

async function runDatabase() {
    const cluster = new cassandra.Client({
        contactPoints: [SCYLLA_HOST],    
        localDataCenter: SCYLLA_DATACENTER,
        keyspace: SCYLLA_KEYSPACE,
        credentials: { username: SCYLLA_USERNAME, password: SCYLLA_PASSWORD }
    });
    const queries = [
        // Users table
        `CREATE TABLE IF NOT EXISTS ${SCYLLA_KEYSPACE}.Users (
            user_id UUID PRIMARY KEY,
            telegram_id TEXT,
            username TEXT,
            email TEXT,
            date_created TIMESTAMP,
            status TEXT,
            preferences TEXT
        )`,

        // Subscriptions table
        `CREATE TABLE IF NOT EXISTS ${SCYLLA_KEYSPACE}.Subscriptions (
            subscription_id UUID PRIMARY KEY,
            user_id UUID,
            plan_type TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            status TEXT,
            auto_renewal BOOLEAN
        )`,

        // Indicator table
        `CREATE TABLE IF NOT EXISTS ${SCYLLA_KEYSPACE}.Indicator (
            indicator_id UUID PRIMARY KEY,
            name TEXT,
            description TEXT,
            strategy TEXT,
            configurations TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )`,

        // Ticker Indicator table
        `CREATE TABLE IF NOT EXISTS ${SCYLLA_KEYSPACE}.TickerIndicator (
            ticker TEXT PRIMARY KEY,
            indicator_id UUID,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )`,

        // Messages table
        `CREATE TABLE IF NOT EXISTS ${SCYLLA_KEYSPACE}.Messages (
            message_id UUID PRIMARY KEY,
            indicator_id UUID,
            user_id UUID,
            message_content TEXT,
            message_type TEXT,
            sent_at TIMESTAMP
        )`,

        // Notifications table
        `CREATE TABLE IF NOT EXISTS ${SCYLLA_KEYSPACE}.Notifications (
            ticker TEXT,
            user_id UUID,
            subscribed_at TIMESTAMP,
            status TEXT,
            PRIMARY KEY (ticker, user_id)
        )`,

        // Operations table
        `CREATE TABLE IF NOT EXISTS ${SCYLLA_KEYSPACE}.Operations (
            ticker TEXT,
            operation TEXT,
            indicator UUID,
            timestamp TIMESTAMP,
            PRIMARY KEY (ticker, timestamp)
        )`,
    ];

    for (const query of queries) {
        try {
            await cluster.execute(query);
            console.log(`Table created with query: ${query}`);
        } catch (error) {
            console.error(`Failed to create table with query: ${query}`);
            console.error(error);
        }
    }

    

    await cluster.shutdown();
}

// Function to insert indicators and strategies
async function insertIndicators(client: cassandra.Client) {
    for (const [name, strategies] of Object.entries(INDICATORS_STRATEGIES)) {
        for (const strategy of strategies) {
            const configurations = ''; // Store strategies as JSON

            const query = `INSERT INTO ${SCYLLA_KEYSPACE}.Indicator (indicator_id, name, description, strategy, configurations, created_at, updated_at)
                           VALUES (uuid(), ?, ?, ?, ?, toTimestamp(now()), toTimestamp(now()))`;

            try {
                await client.execute(query, [ name, `${name} indicator`, strategy, configurations], { prepare: true });
                console.log(`Inserted indicator: ${name} with strategy: ${strategy}`);
            } catch (error) {
                console.error(`Failed to insert indicator: ${name} with strategy: ${strategy}`);
                console.error(error);
            }
        }
    }
}

async function countIndicators(cluster: cassandra.Client): Promise<number> {
    const query = `SELECT COUNT(*) FROM ${SCYLLA_KEYSPACE}.Indicator`;
    
    try {
        const result = await cluster.execute(query, [], { prepare: true });
        
        // Check the count to determine if the table is populated
        const count = result.rows[0]['count'];
        return count;
    } catch (error) {
        console.error("Error checking if Indicator table is populated:", error);
        return 0;
    }
}

// Function to get indicator details (name and strategy) by indicator_id
async function getIndicatorDetailsById(indicator_id: string, cluster: cassandra.Client) {
    console.log(`Getting indicator details for ID: ${indicator_id}`);
    const query = `
        SELECT name, strategy FROM ${SCYLLA_KEYSPACE}.Indicator WHERE indicator_id = ? ALLOW FILTERING
    `;
    const result = await cluster.execute(query, [indicator_id], { prepare: true });
    
    if (result.rows.length > 0) {
        const { name, strategy } = result.rows[0];
        return { name, strategy };
    } else {
        console.log(`No indicator found with ID: ${indicator_id}`);
        return null;
    }
}

// Function to get indicator_id by name and strategy
async function getIndicatorIdByNameAndStrategy(name: string, strategy: string, cluster: cassandra.Client) {
    console.log(`Getting indicator ID for name: ${name} and strategy: ${strategy}`);
    const query = `
        SELECT indicator_id FROM ${SCYLLA_KEYSPACE}.Indicator WHERE name = ? AND strategy = ? ALLOW FILTERING
    `;
    const result = await cluster.execute(query, [name, strategy], { prepare: true });
    
    if (result.rows.length > 0) {
        const { indicator_id } = result.rows[0];
        return indicator_id;
    } else {
        console.log(`No indicator found with name: ${name} and strategy: ${strategy}`);
        return null;
    }
}

// Function to save the best indicator in TickerIndicator
async function saveBestIndicator(response: Response, cluster: cassandra.Client) {
    const { ticker, indicator, strategy } = response;
    const indicatorId = await getIndicatorIdByNameAndStrategy(indicator, strategy, cluster);

    if (!indicatorId) {
        console.error(`Failed to save best indicator: Indicator ${indicator} with strategy ${strategy} not found.`);
        return;
    }

    const query = `
        INSERT INTO ${SCYLLA_KEYSPACE}.TickerIndicator (ticker, indicator_id, created_at, updated_at)
        VALUES (?, ?, toTimestamp(now()), toTimestamp(now()))
    `;
    await cluster.execute(query, [ticker, indicatorId], { prepare: true });
    console.log(`Saved best indicator for ticker ${ticker}: ${indicator}, strategy: ${strategy}.`);
}

// Function to get the best indicator from TickerIndicator
async function getBestIndicator(ticker: string, cluster: cassandra.Client) {
    const query = `
        SELECT indicator_id, created_at, updated_at FROM ${SCYLLA_KEYSPACE}.TickerIndicator WHERE ticker = ?
    `;
    const result = await cluster.execute(query, [ticker], { prepare: true });

    if (result.rows.length > 0) {
        const { indicator_id, created_at, updated_at } = result.rows[0];
        const indicatorDetails = await getIndicatorDetailsById(indicator_id, cluster);
        if (indicatorDetails) {
            return { ...indicatorDetails, created_at, updated_at };
        }
    }
    console.log(`No best indicator found for ticker: ${ticker}`);
    return null;
}

// Function to record an operation in the Operations table
async function recordOperation(ticker: string, operationType: string, indicator: string, strategy: string, timestamp: Date, cluster: cassandra.Client) {
    const indicatorId = await getIndicatorIdByNameAndStrategy(indicator, strategy, cluster);

    if (!indicatorId) {
        console.error(`Failed to record operation: Indicator ${indicator} with strategy ${strategy} not found.`);
        return;
    }

    const query = `
        INSERT INTO ${SCYLLA_KEYSPACE}.Operations (ticker, operation, indicator, timestamp)
        VALUES (?, ?, ?, ?)
    `;
    await cluster.execute(query, [ticker, operationType, indicatorId, timestamp], { prepare: true });
    console.log(`Recorded operation for ticker ${ticker}: ${operationType}, indicator: ${indicator}, strategy: ${strategy}.`);
}

// Function to get the last non-'None' operation for a given ticker
async function getLastOperation(ticker: string, cluster: cassandra.Client) {
    console.log(`Getting last operation for ticker: ${ticker}`);
    const query = `
        SELECT * FROM Operations 
        WHERE ticker = ? 
        AND operation IN ('Buy', 'Sell')
        ORDER BY timestamp DESC 
        LIMIT 1
        ALLOW FILTERING
    `;
    const result = await cluster.execute(query, [ticker], { prepare: true });
    return result.rows[0] || null;
}

const pendingRequests: Request[] = [];

// Function to send request to the indicator app via TASK_QUEUE
async function sendRequest(channel: amqp.Channel, request: Request) {
    console.log(`Sending request for ticker ${request.ticker}, indicator ${request.indicator}, strategy ${request.strategy} to TASK_QUEUE.`);
    await channel.publish(TASK_QUEUE, APP_INSTANCE_QUEUE, Buffer.from(JSON.stringify(request)), {
        persistent: true,
    });    
}

interface Request {
    ticker: string;
    indicator: string;
    strategy: string;
    backtest: boolean;
    userId: number;
    chatId: number;
}

interface Response {
    ticker: string;
    indicator: string;
    strategy: string;
    backtest: boolean;
    signal: string;
    total_return: number | null;
    chatId: number | null;
}

interface TickerResponseAggregator {
    timestamp: number;
    responses: Response[];
}

interface ResponseAggregator {
    [ticker: string]: TickerResponseAggregator;
}

const responseAggregator: ResponseAggregator = {};

async function handleResponse(channel: amqp.Channel, message: amqp.Message, cluster: cassandra.Client) {
    const response: Response = JSON.parse(message.content.toString());

    if (response.backtest && responseAggregator[response.ticker]) {    
        
        responseAggregator[response.ticker].responses.push(response);
        const expectedResponses = Object.values(INDICATORS_STRATEGIES).flat().length;
        const receivedResponses = responseAggregator[response.ticker].responses.length;

        console.log('Aggregating responses, expected responses:', expectedResponses, 'received responses:', receivedResponses);

        if (receivedResponses === expectedResponses) {
            const bestResponse = responseAggregator[response.ticker].responses.reduce((best, current) =>
                (current.total_return || 0) > (best.total_return || 0) ? current : best
            );

            console.log('Best response:', bestResponse);
            await saveBestIndicator(bestResponse, cluster);
            await answerPendingRequests(channel, bestResponse);
            delete responseAggregator[response.ticker];
        }
    } else {
        await recordOperation(response.ticker, response.signal, response.indicator, response.strategy, new Date(), cluster);
        await answerPendingRequests(channel, response);
    }
    channel.ack(message);
}

async function answerPendingRequests(channel: amqp.Channel, response: Response) {

    const processingRequests = [...pendingRequests];
    pendingRequests.splice(0, pendingRequests.length);
    for (const request of processingRequests) {
        const message = JSON.stringify({
            userId: request.userId,
            ticker: response.ticker,
            indicator: response.indicator,
            strategy: response.strategy,
            signal: response.signal,
            total_return: response.total_return,
            chatId: request.chatId
        });
        channel.sendToQueue(TICKER_RESPONSE_QUEUE, Buffer.from(message), { persistent: true });
    }
}

// Main function to set up RabbitMQ and handle requests
async function main() {
    await initDatabase();
    await runDatabase();
    const cluster = new cassandra.Client({
        contactPoints: [SCYLLA_HOST],    
        localDataCenter: SCYLLA_DATACENTER,
        keyspace: SCYLLA_KEYSPACE,
        credentials: { username: SCYLLA_USERNAME, password: SCYLLA_PASSWORD }
    });    
    console.log("Connected to Cassandra database");

    if (await countIndicators(cluster) == 0) {
        console.log("Initializing indicators table");
        await insertIndicators(cluster);
    }

    const connection = await amqp.connect(RABBITMQ_HOST);
    const channel = await connection.createChannel();

    await channel.assertQueue(TICKER_REQUEST_QUEUE, { durable: true });
    await channel.assertQueue(TICKER_RESPONSE_QUEUE, { durable: true });
    await channel.assertQueue(RESULTS_QUEUE, { durable: true });
    await channel.assertExchange(TASK_QUEUE, 'direct', { durable: false });

    console.log(`Connected to RabbitMQ and asserted queues: ${TICKER_REQUEST_QUEUE}, ${TICKER_RESPONSE_QUEUE}, ${RESULTS_QUEUE}.`);

    channel.consume(TICKER_REQUEST_QUEUE, async (msg) => {
        if (msg) {
            console.log(`Received ticker request: ${msg.content.toString()}`);
            const { ticker, chatId, userId } = JSON.parse(msg.content.toString());

            const bestIndicator = await getBestIndicator(ticker, cluster);

            if (!bestIndicator || (Date.now() - new Date(bestIndicator.updated_at).getTime() > TWO_WEEKS_MS)) {
                // If no bestIndicator or the bestIndicator was updated more than two weeks ago
                

                if (!responseAggregator[ticker]) {
                    responseAggregator[ticker] = {timestamp: Date.now(), responses: []};
                    console.log(`No recent best indicator found for ${ticker}. Sending requests for all strategies.`);                
            
                    for (const indicator in INDICATORS_STRATEGIES) {
                        for (const strategy of INDICATORS_STRATEGIES[indicator]) {
                            const request: Request = { ticker, indicator, strategy, backtest: true, userId, chatId };
                            await sendRequest(channel, request);
                        }
                    }
                    const request: Request = { ticker, indicator: 'None', strategy: 'None', backtest: true, userId, chatId };
                    pendingRequests.push(request);
                } else {
                    console.log(`Already aggregating responses for ${ticker}, skipping request.`);
                }
            } else {
                console.log(`Best indicator found for ${ticker}: ${bestIndicator.name}, strategy: ${bestIndicator.strategy}.`);
                
                // Retrieve the last non-'None' operation
                const lastOperation = await getLastOperation(ticker, cluster);                
                if (lastOperation) {
                    console.log(`Last valid operation for ${ticker}: ${lastOperation.operation} with indicator ${lastOperation.indicator} on ${lastOperation.timestamp}.`);
                    const indicatorDetails = await getIndicatorDetailsById(lastOperation.indicator, cluster);
                    const response = JSON.stringify({ 
                        ticker: ticker,
                        indicator: indicatorDetails?.name,
                        strategy: indicatorDetails?.strategy,
                        signal: lastOperation.operation,
                        timestamp: lastOperation.timestamp,
                        chatId,
                        userId 
                    });
                    
                    await channel.sendToQueue(TICKER_RESPONSE_QUEUE, Buffer.from(response), { persistent: false });
                } else {
                    // No recent operation found, send only best indicator details
                    const response = JSON.stringify({ ...bestIndicator, chatId, userId });
                    await channel.sendToQueue(TICKER_RESPONSE_QUEUE, Buffer.from(response), { persistent: false });
                }
            }
            channel.ack(msg);
        }
    }, { noAck: false });

    channel.consume(RESULTS_QUEUE, async (msg) => {
        if (msg) {
            await handleResponse(channel, msg, cluster);
        }
    }, { noAck: false });
}

// Run the main function
main().catch(console.error);

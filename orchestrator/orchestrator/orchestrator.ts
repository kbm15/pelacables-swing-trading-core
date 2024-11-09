// src/orchestrator.ts
import amqp from 'amqplib';
import { Client as PostgresClient } from 'pg';
import { setupChannel } from './amqp/setupChannel';
import { initDatabase} from './db/initDatabase';
import { runDatabase } from './db/runDatabase';
import { insertIndicators, countIndicators } from './db/indicatorQueries';
import { getLastOperation } from './db/operationsQueries';
import { TICKER_REQUEST_QUEUE, TASK_QUEUE, RESULTS_QUEUE, TICKER_RESPONSE_QUEUE, RABBITMQ_HOST, 
    POSTGRES_HOST, POSTGRES_DB, POSTGRES_USERNAME, POSTGRES_PASSWORD } from './config';
import { handleResponse } from './amqp/handleResponse';


const TWO_WEEKS_MS = 14 * 24 * 60 * 60 * 1000;

async function main() {    
    await initDatabase();
    const client = await runDatabase();

    console.log(`Connected to PostgreSQL`);

    if (await countIndicators(client) === 0) {
        console.log("Initializing indicators table");
        await insertIndicators(client);
    }
    const channel = await setupChannel();

    handleResponse(channel,client)
    handleRequest(channel,client);
}

main().catch(console.error);


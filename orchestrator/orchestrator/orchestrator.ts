// src/orchestrator.ts
import { setupChannel } from './amqp/setupChannel';
import { initDatabase} from './db/initDatabase';
import { runDatabase } from './db/runDatabase';
import { insertIndicators, countIndicators } from './db/indicatorQueries';
import { handleResponse } from './amqp/handleResponse';
import { handleRequest } from './amqp/handleRequest';

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


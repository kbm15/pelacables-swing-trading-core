// src/orchestrator.ts
import amqp from 'amqplib';
import { setupChannel } from './amqp/setupChannel';
import { initDatabase, runDatabase } from './db/initDatabase';
import { insertIndicators, countIndicators } from './db/indicatorQueries';
import { getLastOperation } from './db/operationsQueries';
import { TICKER_REQUEST_QUEUE, TWO_WEEKS_MS } from './config';

export async function orchestrate() {
    const cluster = await initDatabase();
    await runDatabase(cluster);

    if (await countIndicators(cluster) === 0) {
        await insertIndicators(cluster);
    }

    const channel = await setupChannel();

    channel.consume(TICKER_REQUEST_QUEUE, async (msg) => {
        if (msg) {
            // Process ticker request logic, as in main function
        }
    }, { noAck: false });
}

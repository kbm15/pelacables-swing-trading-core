// handleResponse.ts
import type { Channel, Message } from 'amqplib';
import { Client as PostgresClient } from 'pg';
import { saveBestIndicator } from '../db/indicatorQueries'
import { recordOperation } from '../db/operationsQueries';
import { answerPendingRequests } from './handleRequest';
import type { Response, ResponseAggregator } from '../types';
import { RESULTS_QUEUE, TICKER_RESPONSE_QUEUE } from '../config';

const responseAggregator: ResponseAggregator = {};



export async function handleResponse(channel: Channel,client: PostgresClient): Promise<void> {
    channel.consume(RESULTS_QUEUE, async (msg) => {
        if (msg) {
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
    }, { noAck: false });

}

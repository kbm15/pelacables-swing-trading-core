// handleResponse.ts
import type { Channel } from 'amqplib';
import { Client as PostgresClient } from 'pg';
import { countIndicators, saveBestIndicator } from '../db/indicatorQueries'
import { recordLastOperation } from '../db/operationsQueries';
import { answerPendingRequests } from './handleRequest';
import type { Operation, Response, ResponseAggregator, TickerIndicator } from '../types';
import { RESULTS_QUEUE } from '../config';

const responseAggregator: ResponseAggregator = {};

export async function handleResponse(channel: Channel,client: PostgresClient): Promise<void> {
    channel.consume(RESULTS_QUEUE, async (msg) => {
        if (msg) {
            const response: Response = JSON.parse(msg.content.toString());

            if (response.backtest) {
                if(responseAggregator[response.ticker]){
                    responseAggregator[response.ticker].responses.push(response);
                    const expectedResponses = await countIndicators(client);
                    const receivedResponses = responseAggregator[response.ticker].responses.length;

                    console.log('Aggregating responses, expected responses:', expectedResponses, 'received responses:', receivedResponses);

                    if (receivedResponses === expectedResponses) {
                        const bestResponse = responseAggregator[response.ticker].responses.reduce((best, current) =>
                            (current.total_return || 0) > (best.total_return || 0) ? current : best
                        );

                        console.log('Best response:', bestResponse);
                        const tickerIndicator: TickerIndicator = { 
                            ticker: response.ticker, 
                            name: bestResponse.indicator, 
                            strategy: bestResponse.strategy,
                            total_return: bestResponse.total_return, 
                            createdAt: new Date(),
                            updatedAt: new Date() 
                        };
                        await saveBestIndicator(tickerIndicator, client);
                        await answerPendingRequests(channel, bestResponse);
                        delete responseAggregator[response.ticker];
                    }
                } else {
                    console.error(`Not aggregating responses for ${response.ticker} but received request.`)
                }
            } else {
                const operation: Operation = { ticker: response.ticker, operation: response.signal, indicator: response.indicator, strategy: response.strategy, timestamp: new Date() };
                const tickerIndicator: TickerIndicator = { 
                    ticker: response.ticker, 
                    name: response.indicator, 
                    strategy: response.strategy, 
                    total_return: response.total_return, 
                    createdAt: new Date(), 
                    updatedAt: new Date() };
                await saveBestIndicator(tickerIndicator, client);
                await recordLastOperation(operation, client);
                await answerPendingRequests(channel, response);
            }
            channel.ack(msg);
        }
    }, { noAck: false });

}

export function addTickerToResponseAggregator(ticker: string) {
    if (!responseAggregator[ticker]) {
        responseAggregator[ticker] = { timestamp: Date.now(), responses: [] };
        return true;
    } else {
        console.log(`Already aggregating responses for ${ticker}, skipping request.`);
        return false;
    }
}
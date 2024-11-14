// handleResponse.ts
import type { Channel } from 'amqplib';
import { Client as PostgresClient } from 'pg';
import { countIndicators, getBestIndicator, saveBestIndicator } from '../db/indicatorQueries'
import { recordLastOperation } from '../db/operationsQueries';
import { answerRequest } from './handleRequest';
import type { Operation, Response, ResponseAggregator, TickerIndicator } from '../types';
import { RESULTS_QUEUE } from '../config';

const responseAggregator: ResponseAggregator = {};

export async function handleResponse(channel: Channel,client: PostgresClient): Promise<void> {
    channel.consume(RESULTS_QUEUE, async (msg) => {
        if (msg) {
            console.log(`Response received: ${msg.content.toString()}`);
            const response: Response = JSON.parse(msg.content.toString());

            if (response.flag === 'backtest') {
                if(responseAggregator[response.ticker]){
                    responseAggregator[response.ticker].responses.push(response);
                    const expectedResponses = await countIndicators(client);
                    const receivedResponses = responseAggregator[response.ticker].responses.length;

                    console.log(`Aggregating responses for ${response.ticker}: expected ${expectedResponses}, received ${receivedResponses}`);

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
                        const operation: Operation = { ticker: response.ticker, operation: bestResponse.signal, indicator: bestResponse.indicator, strategy: bestResponse.strategy, timestamp: new Date() };                        
                        await saveBestIndicator(tickerIndicator, client);
                        await recordLastOperation(operation, client);
                        answerRequest(channel, bestResponse);
                        delete responseAggregator[response.ticker];
                    }
                } else {
                    console.error(`Not aggregating responses for ${response.ticker} but received request.`)
                }
            } else {
                const operation: Operation = { ticker: response.ticker, operation: response.signal, indicator: response.indicator, strategy: response.strategy, timestamp: new Date() };                                
                await recordLastOperation(operation, client);
                const bestIndicator = await getBestIndicator(response.ticker, client);
                if(response.flag === 'notification') {
                    if (bestIndicator !== null) {
                        const responseReturn : Response = { 
                            ticker: response.ticker,
                            indicator: response.indicator,
                            strategy: response.strategy,
                            flag: 'notification',
                            signal: response.signal,
                            total_return: bestIndicator.total_return,
                            chatId: response.chatId
                        }; 
                        answerRequest(channel, responseReturn);
                    } else {
                        answerRequest(channel, response);
                    }                    
                }
                if(response.flag === 'simple') {
                    if (bestIndicator !== null) {
                        const responseReturn : Response = { 
                            ticker: response.ticker,
                            indicator: response.indicator,
                            strategy: response.strategy,
                            flag: 'simple',
                            signal: response.signal,
                            total_return: bestIndicator.total_return,
                            chatId: response.chatId
                        }; 
                        answerRequest(channel, responseReturn);
                    } else {
                        answerRequest(channel, response);
                    }
                }
                
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
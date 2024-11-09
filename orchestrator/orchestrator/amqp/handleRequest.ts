// handleRequest.ts
import type { Channel } from 'amqplib';
import { Client as PostgresClient } from 'pg';
import { TICKER_REQUEST_QUEUE, TICKER_RESPONSE_QUEUE, TASK_QUEUE } from '../config';
import { getBestIndicator, getIndicatorDetailsById, getAllIndicators} from '../db/indicatorQueries';
import { getLastOperation } from '../db/operationsQueries';
import { addTickerToResponseAggregator } from './handleResponse';
import type { Response, Request } from '../types';
import { DateTime } from 'luxon';


const TWO_WEEKS_MS = 14 * 24 * 60 * 60 * 1000;
const pendingRequests: Request[] = [];

export async function answerPendingRequests(channel: Channel, response: Response) {
    for (const request of pendingRequests) {
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
    pendingRequests.length = 0;
}

export async function sendRequest(channel: Channel, request: Request) {
    const message = JSON.stringify(request);
    await channel.sendToQueue(TASK_QUEUE, Buffer.from(message), { persistent: true });
    console.log(`Ticker request sent: ${request.ticker} for userId: ${request.userId}, chatId: ${request.chatId}`);
}

export async function handleRequest(channel: Channel, client: PostgresClient) {
    channel.consume(TICKER_REQUEST_QUEUE, async (msg) => {
        if (msg) {
            console.log(`Received ticker request: ${msg.content.toString()}`);
            const { ticker, chatId, userId } = JSON.parse(msg.content.toString());

            const bestIndicator = await getBestIndicator(ticker, client);            

            if (!bestIndicator || (Date.now() - new Date(bestIndicator.updatedAt).getTime() > TWO_WEEKS_MS)) {
                // If no bestIndicator or the bestIndicator was updated more than two weeks ago
                
                if (addTickerToResponseAggregator(ticker)) {
                    const indicatorStrategies = await getAllIndicators(client);

                    
                    for (const { name, strategy } of indicatorStrategies) {
                        const request: Request = { 
                            ticker:ticker, 
                            indicator: name, 
                            strategy: strategy, 
                            backtest: true, 
                            userId: userId, 
                            chatId: chatId };
                        await sendRequest(channel, request);
                        
                    }
                    const request: Request = { ticker, indicator: 'None', strategy: 'None', backtest: true, userId, chatId };
                    pendingRequests.push(request);
                    
                } else {
                    console.log(`Already aggregating responses for ${ticker}, skipping request.`);
                }
            } else {
                // Retrieve the last operation
                const lastOperation = await getLastOperation(ticker, client);                
                if (lastOperation) {
                    // Set Eastern Time (ET) zone-aware times for NYSE open and close
                    const closeNYSE = DateTime.now()
                    .setZone("America/New_York")       // Set to ET
                    .minus({ days: 1 })                // Move to yesterday
                    .set({ hour: 16, minute: 0, second: 0, millisecond: 0 });

                    const openNYSE = DateTime.now()
                    .setZone("America/New_York")       // Set to ET
                    .set({ hour: 9, minute: 30, second: 0, millisecond: 0 });

                    const lastOperationTimestamp = DateTime.fromJSDate(lastOperation.timestamp).setZone("America/New_York");

                    // Check if the last operation's timestamp is within the specified range
                    //if (lastOperationTimestamp > closeNYSE && lastOperationTimestamp < openNYSE) {
                    if (lastOperationTimestamp > closeNYSE ) {                    
                        console.log(`Last operation for ${ticker} is ${lastOperationTimestamp.toISO()} which is within times for NYSE open and close`);
                        const response = JSON.stringify({ 
                            ticker: ticker,
                            indicator: lastOperation.indicator,
                            strategy: lastOperation.strategy,
                            signal: lastOperation.operation,
                            timestamp: lastOperation.timestamp,
                            total_return: bestIndicator.total_return,
                            chatId,
                            userId 
                        });
                        channel.sendToQueue(TICKER_RESPONSE_QUEUE, Buffer.from(response), { persistent: false });
                    } else {
                        console.log(`Last operation for ${ticker} is ${lastOperationTimestamp.toISO()} which is not within times for NYSE open and close`);
                        const request: Request = { 
                            ticker:ticker, 
                            indicator: bestIndicator.indicator, 
                            strategy: bestIndicator.strategy, 
                            backtest: false, 
                            userId: userId, 
                            chatId: chatId 
                        };                            
                        sendRequest(channel, request);
                        pendingRequests.push(request);
                    }
                } else {
                    console.log(`Last operation for ${ticker} not found`);
                    const request: Request = { 
                        ticker:ticker, 
                        indicator: bestIndicator.indicator, 
                        strategy: bestIndicator.strategy, 
                        backtest: false, 
                        userId: userId, 
                        chatId: chatId 
                    };                            
                    sendRequest(channel, request);
                    pendingRequests.push(request);
                }
                
            }
            channel.ack(msg);
        }
    }, { noAck: false });
}
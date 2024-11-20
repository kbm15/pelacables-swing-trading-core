// handleRequest.ts
import type { Channel } from 'amqplib';
import { Client as PostgresClient } from 'pg';
import { TICKER_REQUEST_QUEUE, TICKER_RESPONSE_QUEUE, TASK_QUEUE } from '../config';
import { getBestIndicator, getAllIndicators} from '../db/indicatorQueries';
import { getLastOperation, getOperation } from '../db/operationsQueries';
import { addTickerToResponseAggregator } from './handleResponse';
import { sendNotification } from './handleSuscription';
import type { Response, Request } from '../types';
import { DateTime } from 'luxon';

const pendingRequests: Request[] = [];


export function answerRequest(channel: Channel, response: Response, ) {
    const answeringRequests: Request[] = [...pendingRequests];
    pendingRequests.length = 0;
    for (const request of answeringRequests) {
        if (request.ticker == response.ticker) {
            const signalKeys = Object.keys(response.signals);
            const lastSignalKey = Number(signalKeys[signalKeys.length - 1]);
            const lastSignal = { [lastSignalKey]: response.signals[lastSignalKey] };
            
            const message = JSON.stringify({
                ticker: response.ticker,
                indicator: response.indicator,
                strategy: response.strategy,
                signals: lastSignal,
                total_return: response.total_return,
                chatId: request.chatId
            });
            console.log(`Answering request ${request.ticker} with ${message}`);
            if (request.flag === 'notification') {
                sendNotification(channel,Buffer.from(message));
            } else {
                console.log(`Answering request ${request.ticker} for ${response.ticker}`);
                channel.sendToQueue(TICKER_RESPONSE_QUEUE, Buffer.from(message), { persistent: true });
            }
            
        } else {
            pendingRequests.push(request);
        }
    }
}

// export function answerBacktestRequests(channel: Channel, response: Response) {
//     if(backtestRequests.length === 0) return;
//     answerRequest(channel, response, backtestRequests);
// }

// export function answerSimpleRequests(channel: Channel, response: Response) {
//     if(simpleRequests.length === 0) return;
//     answerRequest(channel, response, simpleRequests);
// }

// export function answerNotificationRequests(channel: Channel, response: Response) {
//     if(notificationRequests.length === 0) return;
//     answerRequest(channel, response, notificationRequests);
// }

function pushRequest(request: Request) {
    pendingRequests.push(request);
    // if (request.flag === 'simple') {
    //     simpleRequests.push(request);
    // } else if (request.flag === 'backtest') {
    //     backtestRequests.push(request);
    // } else if (request.flag === 'notification') {
    //     notificationRequests.push(request);
    // }
}

function tickerExists(ticker: string) {
    const requests = [...pendingRequests];
    for (const request of requests) {
        if (request.ticker === ticker) {
            return true;
        }
    }
    return false;
}

export function sendRequest(channel: Channel, request: Request) {
    const message = JSON.stringify(request);
    channel.sendToQueue(TASK_QUEUE, Buffer.from(message), { persistent: true });
    console.log(`Ticker request sent: ${request.ticker} for chatId: ${request.chatId}`);
}

export async function handleRequest(channel: Channel, client: PostgresClient) {
    channel.consume(TICKER_REQUEST_QUEUE, async (msg) => {
        if (msg) {
            console.log(`Received ticker request: ${msg.content.toString()}`);
            const { ticker, chatId, userId, source } = JSON.parse(msg.content.toString());

            const bestIndicator = await getBestIndicator(ticker, client);            

            const twoWeeksAgo = DateTime.now().minus({ weeks: 2 }).toJSDate();
            if (!bestIndicator || bestIndicator.updatedAt < twoWeeksAgo) {
                // If no bestIndicator or the bestIndicator was updated more than two weeks ago
                
                if (addTickerToResponseAggregator(ticker)) {
                    const indicatorStrategies = await getAllIndicators(client);
                    
                    for (const { name, strategy } of indicatorStrategies) {
                        const request: Request = { 
                            ticker:ticker, 
                            indicator: name, 
                            strategy: strategy, 
                            flag: 'backtest',
                            chatId: chatId !== null ? chatId : userId };
                        if (!tickerExists(ticker)) {
                            sendRequest(channel, request);
                        }                        
                    }
                    const request: Request = { ticker, indicator: 'None', strategy: 'None', flag: source,  chatId: chatId !== null ? chatId : userId };
                    pushRequest(request);
                    
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
                    .set({ hour: 16, minute: 0, second: 0, millisecond: 0 });

                    const openNYSE = DateTime.now()
                    .setZone("America/New_York")       // Set to ET
                    .set({ hour: 9, minute: 30, second: 0, millisecond: 0 });

                    const lastOperationTimestamp = DateTime.fromJSDate(lastOperation.timestamp).setZone("America/New_York");
                    const operation = await getOperation(ticker, client);
                    // Check if the last operation's timestamp is within the specified range
                    //if (lastOperationTimestamp > closeNYSE && lastOperationTimestamp < openNYSE) {
                    console.log(`Current time is ${DateTime.now().toISO()} and last operation for ${ticker} is ${lastOperationTimestamp.toISO()}`);
                    if (( DateTime.now() < openNYSE  && closeNYSE < DateTime.now() ) || lastOperationTimestamp < DateTime.now().minus({ hours: 24 })) {             
                        console.log(`Getting new data for ${ticker}`);
                        const request: Request = { 
                            ticker:ticker, 
                            indicator: bestIndicator.indicator, 
                            strategy: bestIndicator.strategy, 
                            flag: source, 
                            chatId: chatId !== null ? chatId : userId
                        }; 
                        if (!tickerExists(ticker)) {
                            sendRequest(channel, request);
                        }
                        pushRequest(request);        
                    } else {       
                        console.log(`Sending data from last operation for ${ticker}`);
                        const response : Response = { 
                            ticker: ticker,
                            indicator: lastOperation.indicator,
                            strategy: lastOperation.strategy,
                            flag: source,
                            signals: { [lastOperation.timestamp.getTime()]: operation?.operation === 'Buy' ? 1 : operation?.operation === 'Sell' ? -1 : 0 },
                            total_return: bestIndicator.total_return,
                            chatId: chatId !== null ? chatId : userId
                        };
                        if (source === 'notification') {
                            sendNotification(channel,Buffer.from(JSON.stringify(response)));
                        } else {
                            channel.sendToQueue(TICKER_RESPONSE_QUEUE, Buffer.from(JSON.stringify(response)), { persistent: false });
                        }                
                    }
                } else {
                    console.log(`Last operation for ${ticker} not found`);
                    const request: Request = { 
                        ticker:ticker, 
                        indicator: bestIndicator.indicator, 
                        strategy: bestIndicator.strategy, 
                        flag: source, 
                        chatId: chatId !== null ? chatId : userId 
                    };                            
                    if (!tickerExists(ticker)) {
                        sendRequest(channel, request);
                    }
                    pushRequest(request);
                }
                
            }
            channel.ack(msg);
        }
    }, { noAck: false });
}
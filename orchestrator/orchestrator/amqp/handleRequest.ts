// handleRequest.ts
import type { Channel, Message } from 'amqplib';
import { RESULTS_QUEUE, TICKER_RESPONSE_QUEUE } from '../config';

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
}

export async function handleRequest(channel: Channel) {
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
}
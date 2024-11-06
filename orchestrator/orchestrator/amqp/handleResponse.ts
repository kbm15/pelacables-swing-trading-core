// handleResponse.ts
import { Channel, Message } from 'amqplib';
import cassandra from 'cassandra-driver';
import { saveBestIndicator, recordOperation, answerPendingRequests } from './databaseHelpers';
import { INDICATORS_STRATEGIES, Response, ResponseAggregator } from './types';

const responseAggregator: ResponseAggregator = {};

async function answerPendingRequests(channel: Channel, response: Response) {
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

export async function handleResponse(
    channel: Channel,
    message: Message,
    cluster: cassandra.Client
): Promise<void> {
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

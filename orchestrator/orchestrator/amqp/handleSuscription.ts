import type { Channel } from 'amqplib';
import { Client as PostgresClient } from 'pg';
import { CronJob } from 'cron';
import { DateTime } from 'luxon';
import { TICKER_REQUEST_QUEUE, NOTIFICATION_QUEUE, SUSCRIPTION_QUEUE } from '../config';
import { getSubscriptions,getUserSubscriptions,addUserSubscription,removeUserSubscription } from '../db/suscriptionQueries';

export async function scheduleSuscriptionQueries(channel: Channel,client: PostgresClient) {
    const openNYSE = DateTime.now()
                    .setZone("America/New_York")       // Set to ET
                    .set({ hour: 9, minute: 30, second: 0, millisecond: 0 });
    openNYSE.setZone('local')                
    const cronString = `${openNYSE.minute} ${openNYSE.hour} * * *`;
    //const cronString = `* * * * *`;
    const job = new CronJob(cronString, async () => {  // Run daily at midnight
        console.log('Running subscription scheduler');
        const subscriptions = await getSubscriptions(client);
    
        // Group subscriptions by ticker for batch requests
        const tickers = [...new Set(subscriptions.map(sub => sub.ticker))];
        for (const { ticker, userIds } of subscriptions) {
            for (const userId of userIds) {
                const message = JSON.stringify({ userId, ticker, chatId: null, source: 'notification' });
                channel.sendToQueue(TICKER_REQUEST_QUEUE, Buffer.from(message), { persistent: true });
            }
            console.log(`Ticker request sent: ${ticker} for userIds: ${userIds}`);
        }
    },
    null, // onComplete
	true, // start
	'America/Los_Angeles' // timeZone
    );
    
}

export function handleSuscriptions(channel: Channel,client: PostgresClient) {
    channel.assertQueue(SUSCRIPTION_QUEUE, { durable: true });
    channel.consume(SUSCRIPTION_QUEUE, message => {
        if (message) {
            const messageContent = message.content.toString();
            const { userId, ticker, chatId, action} = JSON.parse(messageContent);
            if (action === 'subscribe') {
                addUserSubscription(ticker, userId, 'active', client);    
            } else if (action === 'unsuscribe') {
                removeUserSubscription(ticker, userId, client);
            } else if (action === 'unsuscribe_all') {
                getUserSubscriptions(userId, client).then(tickers => {
                    for (const ticker of tickers) {
                        removeUserSubscription(ticker, userId, client);
                    }
                });
            }
            channel.ack(message);
        }
    });
}

export function sendNotification(channel: Channel, message: Buffer) {
    channel.sendToQueue(NOTIFICATION_QUEUE, message, { persistent: true });
}
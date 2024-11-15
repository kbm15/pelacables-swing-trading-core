import type { Channel } from 'amqplib';
import type { Telegraf } from 'telegraf';
import { loadEnvVariable } from '../utils/loadEnv';

const SUSCRIPTION_QUEUE = loadEnvVariable('SUSCRIPTION_QUEUE');
const NOTIFICATION_QUEUE = loadEnvVariable('NOTIFICATION_QUEUE');

export function sendSuscriptionRequest(channel: Channel, message: Buffer) {
    channel.sendToQueue(SUSCRIPTION_QUEUE, message, { persistent: true });
}

// Consumer for subscription notifications
export async function consumeNotifications(channel: Channel, bot: Telegraf) {
    channel.consume(NOTIFICATION_QUEUE, (msg) => {
        if (msg) {
            const notification = JSON.parse(msg.content.toString());
            const { chatId, ticker, signal } = notification;

            // Send buy/sell signal to the subscribed user
            const message = `📢 Nueva señal de ${signal} para *${ticker}*!`;
            bot.telegram.sendMessage(chatId, message, { parse_mode: 'Markdown' });
            console.log(`Notification sent to userId: ${chatId} for ticker: ${ticker} with signal: ${signal}`);
            channel.ack(msg);
        }
    });
}

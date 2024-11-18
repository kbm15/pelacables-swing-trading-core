import type { Channel } from 'amqplib';
import type { Telegraf } from 'telegraf';
import { loadEnvVariable } from '../utils/loadEnv';

const SUSCRIPTION_QUEUE = loadEnvVariable('SUSCRIPTION_QUEUE');
const NOTIFICATION_QUEUE = loadEnvVariable('NOTIFICATION_QUEUE');

const DAY_IN_MS = 24 * 60 * 60 * 1000;

export function sendSuscriptionRequest(channel: Channel, message: Buffer) {
    channel.sendToQueue(SUSCRIPTION_QUEUE, message, { persistent: true });
}

// Consumer for subscription notifications
export async function consumeNotifications(channel: Channel, bot: Telegraf) {
    channel.consume(NOTIFICATION_QUEUE, (msg) => {
        if (msg) {
            const notification = JSON.parse(msg.content.toString());
            console.log(`Notification received: ${JSON.stringify(notification)}`);
            const { chatId, ticker, signal } = notification;

            // Send buy/sell signal to the subscribed user
            const now = Date.now();
            const signalEntries = Object.entries(signal);

            if (signalEntries != null && signalEntries != undefined) {
                const recentSignals = signalEntries.filter(([timestamp, value]) => {
                    const signalDate = new Date(Number(timestamp));
                    return now - signalDate.getTime() <= DAY_IN_MS && (value === 1 || value === -1);
                });
        
                if (recentSignals.length > 0) {
                    const [timestamp, value] = recentSignals[0];
                    const signalString = value === 1 ? 'Compra' : 'Venta';
                    const signalDate = new Date(Number(timestamp));
                    const message = `📢 *${ticker}* señal de ${signalString} a las ${signalDate.toTimeString()}!`;
                    bot.telegram.sendMessage(chatId, message, { parse_mode: 'Markdown' });
                    console.log(`Notification sent to userId: ${chatId} for ticker: ${ticker} with signal: ${signalString}`);
                }
            }
            channel.ack(msg);
        }
    });
}

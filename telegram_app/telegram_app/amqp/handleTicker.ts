import type { Channel } from 'amqplib';
import type { Telegraf } from 'telegraf';
import { loadEnvVariable } from '../utils/loadEnv';

const TICKER_REQUEST_QUEUE = loadEnvVariable('TICKER_REQUEST_QUEUE');
const TICKER_RESPONSE_QUEUE = loadEnvVariable('TICKER_RESPONSE_QUEUE');

// Send a ticker request to the queue
export async function sendTickerRequest(userId: number, ticker: string, channel: Channel, chatId?: number) {
    const message = JSON.stringify({ userId, ticker, chatId: chatId || null });
    channel.sendToQueue(TICKER_REQUEST_QUEUE, Buffer.from(message), { persistent: true });
    console.log(`Ticker request sent: ${ticker} for userId: ${userId}, chatId: ${chatId}`);
}

// Consumer for ticker responses
export async function consumeTickerResponses(channel: Channel, bot: Telegraf) {
    channel.consume(TICKER_RESPONSE_QUEUE, (msg) => {
        if (msg) {
            console.log(`Respuesta de ticker recibida: ${msg.content.toString()}`);
            const response = JSON.parse(msg.content.toString());

            for (const key in response) {
                if (response[key] === undefined) {
                    console.log(`Clave indefinida en la respuesta: ${key}`);
                    channel.ack(msg);
                    return;
                }
                continue;
            }

            const { userId, ticker, indicator, strategy, signal, total_return, chatId } = response;

            // Construir un mensaje detallado y formateado
            let responseMessage = `📊 *Resumen de Estrategia para ${ticker}*\n\n`;
            responseMessage += `📌 **Indicador:** *${indicator}*\n`;
            responseMessage += `📝 **Estrategia:** *${strategy}*\n`;
            responseMessage += `🔔 **Señal:** ${signal ? `*${signal}*` : 'Sin señal'}\n`;
            responseMessage += `💹 **Retorno Total:** ${total_return !== undefined && total_return !== null ? `*${total_return.toFixed(2)}%*` : '*No disponible*'}\n\n`;
            responseMessage += `🔄 _Respuesta solicitada por el usuario ${userId}_`;

            // Definir los botones de interacción
            const markup = {
                inline_keyboard: [
                    [
                        { text: '🔔 Suscribirse', callback_data: `SUBSCRIBE_${ticker}` },
                        { text: '📊 Ver en WebApp', url: `https://finance.yahoo.com/quote/${ticker}` },
                        { text: '🔙 Volver al Menú', callback_data: 'MAIN_MENU' }
                    ]
                ]
            };

            // Enviar mensaje al chat apropiado (usuario o grupo)
            if (userId !== undefined && userId !== null) {
                if (chatId !== undefined && chatId !== null) {
                    bot.telegram.sendMessage(chatId, responseMessage, { parse_mode: 'Markdown', reply_markup: markup });
                    console.log(`Respuesta enviada a chatId: ${chatId}`);
                } else {
                    bot.telegram.sendMessage(userId, responseMessage, { parse_mode: 'Markdown', reply_markup: markup });
                    console.log(`Respuesta enviada a userId: ${userId}`);
                }
            }
            channel.ack(msg);
        }
    });
}

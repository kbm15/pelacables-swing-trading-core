import type { Channel } from 'amqplib';
import type { Telegraf } from 'telegraf';
import { loadEnvVariable } from '../utils/loadEnv';
import { getTickerExchange } from '../utils/checkTicker';

const TICKER_REQUEST_QUEUE = loadEnvVariable('TICKER_REQUEST_QUEUE');
const TICKER_RESPONSE_QUEUE = loadEnvVariable('TICKER_RESPONSE_QUEUE');
const WEBAPP_URL = loadEnvVariable('WEBAPP_URL');

interface Response {
    ticker: string;
    indicator: string;
    strategy: string;
    flag: 'simple' | 'backtest' | 'notification';
    signals: { [timestamp: number]: number };
    total_return: number;
    chatId: number;
}

// Send a ticker request to the queue
export async function sendTickerRequest(userId: number, ticker: string, channel: Channel, chatId?: number) {
    const message = JSON.stringify({ userId, ticker, chatId: chatId || null, source: 'simple' });
    channel.sendToQueue(TICKER_REQUEST_QUEUE, Buffer.from(message), { persistent: true });
    console.log(`Ticker request sent: ${ticker} for userId: ${userId}, chatId: ${chatId}`);
}

// Consumer for ticker responses
export async function consumeTickerResponses(channel: Channel, bot: Telegraf) {
    const indicatorUrls: { [key: string]: string } = {
        "AwesomeOscillator": "https://www.tradingview.com/support/solutions/43000501826-awesome-oscillator-ao/",
        "BollingerBands": "https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/",
        "IchimokuCloud": "https://www.tradingview.com/support/solutions/43000589152-ichimoku-cloud/",
        "KeltnerChannel": "https://www.tradingview.com/support/solutions/43000502266-keltner-channels-kc/",
        "MovingAverage": "https://www.tradingview.com/support/solutions/43000502589-moving-averages/",
        "MACD": "https://www.tradingview.com/support/solutions/43000502344-macd-moving-average-convergence-divergence/",
        "PSAR": "https://www.tradingview.com/support/solutions/43000502597-parabolic-sar-sar/",
        "RSI": "https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/",
        "VolumeIndicator": "https://www.tradingview.com/support/solutions/43000591617-volume/"
    };
    
    channel.consume(TICKER_RESPONSE_QUEUE, async(msg) => {
        if (msg) {
            console.log(`Respuesta de ticker recibida: ${msg.content.toString()}`);
            const responseJson = JSON.parse(msg.content.toString());
            responseJson.signals = Object.fromEntries(Object.entries(responseJson.signals).map(([timestamp, signal]) => [Number(timestamp), Number(signal)]));
            const response: Response = responseJson;
            const { ticker, indicator, strategy, signals, total_return, chatId } = response

            // Construir un mensaje detallado y formateado
            let responseMessage = `📊 *Resumen de Estrategia para ${ticker}*\n\n`;
            if (indicatorUrls[indicator]) {
                responseMessage += `📌 *Indicador:* ${indicator} [+INFO](${indicatorUrls[indicator]})\n`;
            } else {
                responseMessage += `📌 *Indicador:* ${indicator}\n`;
            }

            responseMessage += `💹 *Últimos 180d:* ${total_return !== undefined && total_return !== null ? `${total_return.toFixed(2)}%` : 'No disponible'}\n\n`;

            if (Object.keys(signals).length === 0) {
                console.log(`No signals for ticker: ${ticker}, chatId: ${chatId}`);
            } else {
                const signal = Object.entries(signals)[0][1];
                const signalString = signal === 1 ? 'Alcista' : signal === -1 ? 'Bajista' : 'Neutral';
                const date = new Date(Number(Object.entries(signals)[0][0]));
                responseMessage += `🔔 Señal ${signalString} el ${date.toLocaleDateString()}\n`;
            }

            // Enviar mensaje al chat apropiado (usuario o grupo)
            if (chatId !== undefined && chatId !== null) {
                const isGroup = chatId < 0
                const marketTicker = await getTickerExchange(ticker);
                const cleanTicker = ticker.split('.')[0].replace('-', '');
                console.log(`URL: ${WEBAPP_URL}?ticker=${marketTicker}:${cleanTicker}&indicator=${indicator}`)
                const markup = {
                    inline_keyboard: [
                    [
                            { text: '🔔 Suscribir', callback_data: `SUBSCRIBE_${ticker}` },
                            isGroup
                            ? { text: '📊 Grafico', url: `${WEBAPP_URL}?ticker=${marketTicker}:${cleanTicker}&indicator=${indicator}` }
                            : { text: '📊 Grafico', web_app: { url: `${WEBAPP_URL}?ticker=${marketTicker}:${cleanTicker}&indicator=${indicator}` }},
                            { text: '🔙 Menú', callback_data: 'MAIN_MENU' }
                    ]
                    ]
                };
                bot.telegram.sendMessage(chatId, responseMessage, { parse_mode: 'Markdown', reply_markup: markup, link_preview_options: { is_disabled: true } });
                console.log(`Respuesta enviada a chatId: ${chatId}`);
            } 

            
            channel.ack(msg);
        }
    });
}

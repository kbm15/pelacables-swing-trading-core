import { Telegraf, Markup } from 'telegraf';
import { message } from 'telegraf/filters'
import type { Channel } from 'amqplib';
import { findTicker, checkTicker, formatTickerMessage } from './utils/checkTicker';

import { connectRabbitMQ } from './amqp/setupChannel';
import { sendSuscriptionRequest, consumeNotifications } from './amqp/handleNotification';
import { sendTickerRequest, consumeTickerResponses } from './amqp/handleTicker';


import { loadEnvVariable } from './utils/loadEnv';

// Load environment variables with required check
const TELEGRAM_TOKEN = loadEnvVariable('TELEGRAM_TOKEN');

async function registerBotActions(bot: Telegraf, channel: Channel) {    
    const menu = {
        inline_keyboard: [
            [{ text: '📈 Solicitar Estrategia de Ticker', callback_data:'CHECK_TICKER'}],
            [{ text:'📋 Ver Lista de Suscripciones', callback_data:'SUBSCRIPTION_LIST'}],
            [{ text:'📝 Ayuda del Bot', callback_data:'MAIN_MENU'}]
        ],
        resize_keyboard: true
    };
    const helpMessage = `
        🤖 *Bienvenido al Bot de MonoTrading* 📈

        Este bot te permite recibir señales de compra/venta basadas en el análisis del mercado con un marco de tiempo _diario_.

        ---

        🛠️ **Funciones Principales:**
        1. **📊 Solicitar Estrategia de Ticker**  
        Analiza un _ticker_ y obtén una estrategia recomendada. También puedes suscribirte para recibir actualizaciones automáticas.

        2. **📋 Lista de Suscripciones**  
        Administra tus suscripciones activas a señales de diferentes _tickers_ y anula la suscripción cuando lo desees.

        ---

        📖 **Interpretando las Señales:**
        - 📈 *Señal de Compra*: Indica una posible tendencia al alza.
        - 📉 *Señal de Venta*: Señala una posible tendencia a la baja.
        
        _Recuerda que estas señales son solo una guía, y es importante realizar tu propio análisis._

        🔍 Para un análisis detallado, abre el _ticker_ en la aplicación web para ver gráficos en tiempo real de las señales de compra/venta.

        📅 **Nota**: Todas las estrategias están basadas en datos diarios.
            
        ¡Esperamos que este bot te sea útil en tu camino financiero! 🤑💹
    `;
    bot.start((ctx) => {
        console.log(`El usuario inició el bot: ${ctx.from.id}`);
        return ctx.reply(`¡Bienvenido! ${helpMessage} Elige una opción:`, {parse_mode: "Markdown", reply_markup: menu});    
    });

    bot.action('MAIN_MENU', (ctx) => {
        return ctx.reply('Elige una opción:', {reply_markup: menu});    
    });

    bot.action('CHECK_TICKER', (ctx) => {
        ctx.reply('Por favor, ingresa el símbolo del ticker que deseas analizar:', Markup.forceReply());
        bot.on(message('text'), async (ctx) => {
            console.log(`Usuario ingresó ticker: ${ctx.message.text}`);
            const ticker = ctx.message.text.toUpperCase();
            const tickerRegex = /^[A-Za-z.]+$/;

            if (!tickerRegex.test(ticker)) {
                console.log(`Ticker inválido ingresado: ${ticker}`);
                return ctx.reply("⚠️ Por favor proporciona un ticker válido. Ejemplo: AAPL", Markup.forceReply());
            } else {
                const tickerResults = await findTicker(ticker);
                if (tickerResults['quotes'].length > 0) {
                    const buttons = tickerResults['quotes'].map(quote => [
                        Markup.button.callback(`${quote.longname} : ${quote.symbol}`, `TICKER_REQUEST_${quote.symbol}`)
                    ]);
                    ctx.reply('Elige un ticker:', Markup.inlineKeyboard(buttons));
                } else {                         
                    return ctx.reply("❌ El ticker proporcionado no existe.");
                }
            }
        });
    });

    bot.action(/^TICKER_REQUEST_/, async (ctx) => {
        const ticker = ctx.match.input.split('_')[2];
        const chatId = ctx.chat?.type === 'private' ? undefined : ctx.chat?.id;
        const userId = ctx.from.id;
        const tickerValid = await checkTicker(ticker);

        if (!tickerValid) {
            return ctx.reply(`❌ Valor ${ticker} no soportado, prueba con otro.`, Markup.forceReply());    
        }
        
        if (userId === undefined || ticker === undefined) {
            return ctx.reply("❌ Error en la solicitud. Por favor intenta de nuevo.");        
        } else {
            console.log(`Usuario ${userId} solicitó ticker: ${ticker.toUpperCase()}, chatId: ${chatId}`);

            
            const tickerRequestMessage = await formatTickerMessage(ticker);
            await sendTickerRequest(ctx.from.id, ticker.toUpperCase(), channel, chatId);
            if (tickerRequestMessage.length > 0) {
                return ctx.reply(tickerRequestMessage,{ parse_mode: 'Markdown'});
            }
            return;                    
        }    
    });

    bot.action(/^SUBSCRIBE_/, (ctx) => {
        const ticker = ctx.match.input.split('_')[1];
        const message = JSON.stringify({ userId: ctx.from.id, ticker: ticker.toUpperCase(), action: "subscribe" });
        sendSuscriptionRequest(channel, Buffer.from(message));
        ctx.reply(`🔔 Te has suscrito a las señales de ${ticker.toUpperCase()}.`);
        console.log(`Usuario ${ctx.from.id} suscrito a notificaciones para el ticker: ${ticker.toUpperCase()}`);
    });

    bot.action('SUBSCRIPTION_LIST', async (ctx) => {
        const subscriptions: string[] = []; // Replace with your subscription fetching logic
        if (subscriptions.length === 0) {
            return ctx.reply('❌ No tienes suscripciones activas.');
        }

        const buttons = subscriptions.map(ticker => [
            Markup.button.callback(`❌ Cancelar suscripción de ${ticker}`, `UNSUBSCRIBE_${ticker}`)
        ]);
        buttons.push([Markup.button.callback('❌ Cancelar todas las suscripciones', 'UNSUBSCRIBE_ALL')]);
        ctx.reply('Tus suscripciones:', Markup.inlineKeyboard(buttons));
    });

    bot.action(/^UNSUBSCRIBE_/, async (ctx) => {
        const ticker = ctx.match.input.split('_')[1];
        const message = JSON.stringify({ userId: ctx.from.id, ticker: ticker.toUpperCase(), action: "unsuscribe" });
        sendSuscriptionRequest(channel, Buffer.from(message));        
        ctx.reply(`❌ Has cancelado la suscripción a ${ticker}.`);
    });

    bot.action('UNSUBSCRIBE_ALL', async (ctx) => {
        const message = JSON.stringify({ userId: ctx.from.id, ticker: null, action: "unsuscribe_all" });
        sendSuscriptionRequest(channel, Buffer.from(message));        
        ctx.reply('❌ Has cancelado todas tus suscripciones.');
    });

    bot.action('BOT_HELP', (ctx) => {        
        ctx.reply(helpMessage);
    });
}


async function main() {
    const channel = await connectRabbitMQ();
    const bot = new Telegraf(TELEGRAM_TOKEN);
    await registerBotActions(bot, channel);
    consumeTickerResponses(channel, bot);
    consumeNotifications(channel, bot);
    bot.launch().catch(console.error);
    process.once('SIGINT', () => {
        console.log("Bot is stopping...");
        bot.stop('SIGINT');
    });
    process.once('SIGTERM', () => {
        console.log("Bot is stopping...");
        bot.stop('SIGTERM');
    });
}

main();
import { Telegraf } from 'telegraf';
import amqplib from 'amqplib';

// Load environment variables with required check
function loadEnvVariable(name: string): string {
    const value = process.env[name];
    if (!value) {
        console.error(`Environment variable ${name} is missing.`);
        process.exit(1);
    }
    return value;
}

// Load and validate necessary environment variables
const TELEGRAM_TOKEN = loadEnvVariable('TELEGRAM_TOKEN');
const RABBITMQ_HOST = loadEnvVariable('RABBITMQ_HOST');
const TICKER_REQUEST_QUEUE = loadEnvVariable('TICKER_REQUEST_QUEUE');
const TICKER_RESPONSE_QUEUE = loadEnvVariable('TICKER_RESPONSE_QUEUE');
const NOTIFICATION_QUEUE = loadEnvVariable('NOTIFICATION_QUEUE');

// Initialize Telegraf with the Telegram token
const bot = new Telegraf(TELEGRAM_TOKEN);

let channel: amqplib.Channel;

// Connect to RabbitMQ
async function connectRabbitMQ() {
    const connection = await amqplib.connect(RABBITMQ_HOST);
    channel = await connection.createChannel();

    // Ensure queues exist
    await channel.assertQueue(TICKER_REQUEST_QUEUE, { durable: true });
    await channel.assertQueue(TICKER_RESPONSE_QUEUE, { durable: true });
    await channel.assertQueue(NOTIFICATION_QUEUE, { durable: true });

    // Start consumers
    consumeTickerResponses();
    consumeNotifications();
}
connectRabbitMQ().catch(console.error);

// Send a ticker request to the queue
async function sendTickerRequest(userId: number, ticker: string, chatId: number) {
    const message = JSON.stringify({ userId, ticker, chatId });
    channel.sendToQueue(TICKER_REQUEST_QUEUE, Buffer.from(message), { persistent: true });
}

// Consumer for ticker responses
async function consumeTickerResponses() {
    channel.consume(TICKER_RESPONSE_QUEUE, (msg) => {
        if (msg) {
            const response = JSON.parse(msg.content.toString());
            const { userId, ticker, indicator, strategy, signal, total_return, chatId } = response;

            // Compose a detailed message for the response
            let responseMessage = `📈 Información para *${ticker}*\n`;
            responseMessage += `• Indicador: *${indicator}*\n`;
            responseMessage += `• Estrategia: *${strategy}*\n`;
            responseMessage += `• Señal: ${signal ? `*${signal}*` : 'Sin señal'}\n`;
            responseMessage += `• Retorno total: *${total_return.toFixed(2)}%*\n`;
            responseMessage += `_Respuesta solicitada por ${userId}_`;

            // Send the message to the appropriate chat (user or group)
            bot.telegram.sendMessage(chatId, responseMessage, { parse_mode: 'Markdown' });
            channel.ack(msg);
        }
    });
}

// Consumer for subscription notifications
async function consumeNotifications() {
    channel.consume(NOTIFICATION_QUEUE, (msg) => {
        if (msg) {
            const notification = JSON.parse(msg.content.toString());
            const { userId, ticker, signal } = notification;

            // Send buy/sell signal to the subscribed user
            const message = `📢 Nueva señal de ${signal} para *${ticker}*!`;
            bot.telegram.sendMessage(userId, message, { parse_mode: 'Markdown' });
            channel.ack(msg);
        }
    });
}

// Bot commands
bot.start((ctx) => {
    ctx.reply("Bienvenido! Usa /ticker <TICKER> para obtener información o /subscribe <TICKER> para recibir notificaciones.");
});

bot.command('ticker', async (ctx) => {
    const ticker = ctx.message.text.split(' ')[1];
    if (!ticker) {
        return ctx.reply("Por favor proporciona el ticker. Ejemplo: /ticker AAPL");
    }

    const chatId = ctx.message.chat.id;
    await sendTickerRequest(ctx.from.id, ticker.toUpperCase(), chatId);
    ctx.reply(`Solicitud enviada para ${ticker.toUpperCase()}. Recibirás la información en breve.`);
});

bot.command('subscribe', async (ctx) => {
    const ticker = ctx.message.text.split(' ')[1];
    if (!ticker) {
        return ctx.reply("Por favor proporciona el ticker. Ejemplo: /subscribe AAPL");
    }

    const message = JSON.stringify({ userId: ctx.from.id, ticker: ticker.toUpperCase(), action: "subscribe" });
    channel.sendToQueue(NOTIFICATION_QUEUE, Buffer.from(message), { persistent: true });
    
    ctx.reply(`Te has suscrito a las notificaciones de ${ticker.toUpperCase()}. Recibirás señales de compra/venta.`);
});

bot.command('unsubscribe', async (ctx) => {
    const ticker = ctx.message.text.split(' ')[1];
    if (!ticker) {
        return ctx.reply("Por favor proporciona el ticker. Ejemplo: /unsubscribe AAPL");
    }

    const message = JSON.stringify({ userId: ctx.from.id, ticker: ticker.toUpperCase(), action: "unsubscribe" });
    channel.sendToQueue(NOTIFICATION_QUEUE, Buffer.from(message), { persistent: true });

    ctx.reply(`Te has dado de baja de las notificaciones de ${ticker.toUpperCase()}.`);
});

bot.command('list', async (ctx) => {
    // Fetch the list of subscriptions for the user from a database or cache (to be implemented)
    const subscriptions = ["AAPL", "TSLA"];  // Example placeholder
    ctx.reply(`Tus suscripciones actuales: ${subscriptions.join(", ")}`);
});

// Start the bot
bot.launch().then(() => {
    console.log("Bot iniciado.");
}).catch(console.error);

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'))
process.once('SIGTERM', () => bot.stop('SIGTERM'))
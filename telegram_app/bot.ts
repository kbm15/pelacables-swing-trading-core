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
    try {
        const connection = await amqplib.connect(RABBITMQ_HOST);
        channel = await connection.createChannel();

        // Ensure queues exist
        await channel.assertQueue(TICKER_REQUEST_QUEUE, { durable: true });
        await channel.assertQueue(TICKER_RESPONSE_QUEUE, { durable: true });
        await channel.assertQueue(NOTIFICATION_QUEUE, { durable: true });

        // Start consumers
        consumeTickerResponses();
        consumeNotifications();
        console.log("Connected to RabbitMQ and queues initialized.");
    } catch (error) {
        console.error("Failed to connect to RabbitMQ:", error);
    }
}
connectRabbitMQ().catch(console.error);

// Send a ticker request to the queue
async function sendTickerRequest(userId: number, ticker: string, chatId?: number) {
    const message = JSON.stringify({ userId, ticker, chatId: chatId || null });
    channel.sendToQueue(TICKER_REQUEST_QUEUE, Buffer.from(message), { persistent: true });
    console.log(`Ticker request sent: ${ticker} for userId: ${userId}, chatId: ${chatId}`);
}

// Consumer for ticker responses
async function consumeTickerResponses() {
    channel.consume(TICKER_RESPONSE_QUEUE, (msg) => {
        if (msg) {
            const response = JSON.parse(msg.content.toString());

            for (const key in response) {
                if (response[key] === undefined) {
                    console.log(`Undefined key in response: ${key}`);
                    channel.ack(msg);
                    return;
                }
                continue;
            }
            const { userId, ticker, indicator, strategy, signal, total_return, chatId } = response;

            // Compose a detailed message for the response
            let responseMessage = `📈 Información para *${ticker}*\n`;
            responseMessage += `• Indicador: *${indicator}*\n`;
            responseMessage += `• Estrategia: *${strategy}*\n`;
            responseMessage += `• Señal: ${signal ? `*${signal}*` : 'Sin señal'}\n`;
            // Check if total_return is defined and format it accordingly
            if (total_return !== undefined && total_return !== null) {
                responseMessage += `• Retorno total: *${total_return.toFixed(2)}%*\n`;
            } else {
                responseMessage += `• Retorno total: *No disponible*\n`;
            }
            responseMessage += `_Respuesta solicitada por ${userId}_`;

            // Send the message to the appropriate chat (user or group)
            if (chatId !== undefined && chatId !== null) {
                bot.telegram.sendMessage(chatId, responseMessage, { parse_mode: 'Markdown' });
                console.log(`Response sent to chatId: ${chatId}`);
            } else {
                if (userId !== undefined && userId !== null) {                    
                    bot.telegram.sendMessage(userId, responseMessage, { parse_mode: 'Markdown' });
                    console.log(`Response sent to userId: ${userId}`);                    
                }
            }
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
            console.log(`Notification sent to userId: ${userId} for ticker: ${ticker} with signal: ${signal}`);
            channel.ack(msg);
        }
    });
}

// Bot commands
bot.start((ctx) => {
    ctx.reply("Bienvenido! Usa /ticker <TICKER> para obtener información o /subscribe <TICKER> para recibir notificaciones.");
    console.log(`User started the bot: ${ctx.from.id}`);
});

bot.command('ticker', async (ctx) => {
    const ticker = ctx.message.text.split(' ')[1];
    if (!ticker) {
        return ctx.reply("Por favor proporciona el ticker. Ejemplo: /ticker AAPL");
    }

    const chatId = ctx.message.chat.type === 'private' ? undefined : ctx.message.chat.id;
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
    console.log(`User ${ctx.from.id} subscribed to notifications for ticker: ${ticker.toUpperCase()}`);
});

bot.command('unsubscribe', async (ctx) => {
    const ticker = ctx.message.text.split(' ')[1];
    if (!ticker) {
        return ctx.reply("Por favor proporciona el ticker. Ejemplo: /unsubscribe AAPL");
    }

    const message = JSON.stringify({ userId: ctx.from.id, ticker: ticker.toUpperCase(), action: "unsubscribe" });
    channel.sendToQueue(NOTIFICATION_QUEUE, Buffer.from(message), { persistent: true });

    ctx.reply(`Te has dado de baja de las notificaciones de ${ticker.toUpperCase()}.`);
    console.log(`User ${ctx.from.id} unsubscribed from notifications for ticker: ${ticker.toUpperCase()}`);
});

bot.command('list', async (ctx) => {
    // Fetch the list of subscriptions for the user from a database or cache (to be implemented)
    const subscriptions = ["AAPL", "TSLA"];  // Example placeholder
    ctx.reply(`Tus suscripciones actuales: ${subscriptions.join(", ")}`);
    console.log(`User ${ctx.from.id} requested their subscriptions.`);
});

// Start the bot
bot.launch().catch(console.error);

// Enable graceful stop
process.once('SIGINT', () => {
    console.log("Bot is stopping...");
    bot.stop('SIGINT');
});
process.once('SIGTERM', () => {
    console.log("Bot is stopping...");
    bot.stop('SIGTERM');
});

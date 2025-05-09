// src/db/runDatabase.ts
import { Client as PostgresClient } from 'pg';
import { POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD } from '../config';

export async function runDatabase() {
    const client = new PostgresClient({
        host: POSTGRES_HOST,
        user: POSTGRES_USER,
        password: POSTGRES_PASSWORD,
        database: POSTGRES_DB,
    });
    await client.connect();
    const queries = [
        // Users table
        `CREATE TABLE IF NOT EXISTS Users (
            telegram_id INT PRIMARY KEY,
            username TEXT,
            email TEXT,
            date_created TIMESTAMPTZ,
            status TEXT,
            preferences TEXT
        )`,
    
        // Subscriptions table
        `CREATE TABLE IF NOT EXISTS Subscriptions (
            subscription_id UUID PRIMARY KEY,
            telegram_id INT REFERENCES Users(telegram_id) ON DELETE CASCADE,
            plan_type TEXT,
            start_date TIMESTAMPTZ,
            end_date TIMESTAMPTZ,
            status TEXT,
            auto_renewal BOOLEAN
        )`,
    
        // Indicator table
        `CREATE TABLE IF NOT EXISTS Indicators (
            indicator_id UUID PRIMARY KEY,
            name TEXT,
            description TEXT,
            strategy TEXT,
            configurations TEXT,
            created_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ
        )`,
    
        // Ticker Indicator table
        `CREATE TABLE IF NOT EXISTS TickerIndicators (
            ticker TEXT PRIMARY KEY,
            indicator_id UUID REFERENCES Indicators(indicator_id) ON DELETE CASCADE,
            total_return FLOAT,
            created_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ
        )`,
    
        // Messages table
        `CREATE TABLE IF NOT EXISTS Messages (
            message_id UUID PRIMARY KEY,
            indicator_id UUID REFERENCES Indicators(indicator_id) ON DELETE CASCADE,
            telegram_id INT REFERENCES Users(telegram_id) ON DELETE CASCADE,
            message_content TEXT,
            message_type TEXT,
            sent_at TIMESTAMPTZ
        )`,
    
        // Notifications table
        `CREATE TABLE IF NOT EXISTS Notifications (
            ticker TEXT,
            telegram_id INT REFERENCES Users(telegram_id) ON DELETE CASCADE,
            subscribed_at TIMESTAMPTZ,
            status TEXT,
            PRIMARY KEY (ticker, telegram_id)
        )`,
    
        // Operations table
        `CREATE TABLE IF NOT EXISTS Operations (
            ticker TEXT,
            operation TEXT,
            indicator UUID REFERENCES Indicators(indicator_id) ON DELETE CASCADE,
            timestamp TIMESTAMPTZ,
            PRIMARY KEY (ticker, timestamp)
        )`,
        
        // Last Operation table
        `CREATE TABLE IF NOT EXISTS LastOperations (
            ticker TEXT PRIMARY KEY,
            operation TEXT,
            indicator UUID REFERENCES Indicators(indicator_id) ON DELETE CASCADE,
            timestamp TIMESTAMPTZ
        )`
    ];
    

    for (const query of queries) {
        try {
            await client.query(query);
        } catch (error) {
            console.error(`Failed to create table:`, error);
        }
    }

    return client;
}

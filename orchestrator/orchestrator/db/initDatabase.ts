// src/db/initDatabase.ts
import { Client as PostgresClient } from 'pg';
import { POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD } from '../config';

export async function initDatabase() {
    const client = new PostgresClient({
        host: POSTGRES_HOST,
        user: POSTGRES_USER,
        password: POSTGRES_PASSWORD,
        database: 'postgres',
    });
    
    try {
        await client.connect();
        await client.query(`CREATE DATABASE ${POSTGRES_DB}`);
        console.log(`Initialized PostgreSQL database ${POSTGRES_DB}`);
        await client.end();
    } catch (error: any) {
        if (error.code === '42P04') {
            // Database already exists
            console.log(`PostgreSQL database ${POSTGRES_DB} already exists`);
            await client.end();
        } else {
            console.error('Failed to create PostgreSQL database:', error);
            console.log(`Host: ${POSTGRES_HOST}, User: ${POSTGRES_USER}, Password: ${POSTGRES_PASSWORD}`);
            process.exit(1);
        }
    }
    
}



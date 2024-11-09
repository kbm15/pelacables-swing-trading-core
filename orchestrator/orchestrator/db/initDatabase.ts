// src/db/initDatabase.ts
import { Client as PostgresClient } from 'pg';
import { POSTGRES_HOST, POSTGRES_DB, POSTGRES_USERNAME, POSTGRES_PASSWORD } from '../config';

export async function initDatabase() {
    const client = new PostgresClient({
        host: POSTGRES_HOST,
        user: POSTGRES_USERNAME,
        password: POSTGRES_PASSWORD,
        database: POSTGRES_DB,
    });
    await client.connect();
    try {
        await client.query(`CREATE DATABASE ${POSTGRES_DB}`);
        console.log(`Initialized PostgreSQL database ${POSTGRES_DB}`);
    } catch (error: any) {
        if (error.code === '42P04') {
            // Database already exists
            console.log(`PostgreSQL database ${POSTGRES_DB} already exists`);
        } else {
            console.error('Failed to create PostgreSQL database:', error);
        }
    }
    await client.end();
}



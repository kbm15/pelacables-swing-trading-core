// src/db/operationsQueries.ts
import { Client as PostgresClient } from 'pg';
import type { Operation } from '../types';
import { getIndicatorDetailsById } from './indicatorQueries';

async function recordOperation(operation: Operation, client: PostgresClient) {

    const query = `
        INSERT INTO Operations (ticker, operation, indicator, timestamp)
        VALUES ($1, $2, (SELECT indicator_id FROM Indicators WHERE name = $3 AND strategy = $4), $5)
    `;


    const values = [
        operation.ticker,
        operation.operation,
        operation.indicator,
        operation.strategy,
        operation.timestamp,
    ];
    
    await client.query(query, values);
    console.log(`Recorded operation for ticker ${operation.ticker}: ${operation.operation}.`);

}

export async function recordLastOperation(operation: Operation, client: PostgresClient) {

    const query = `
        INSERT INTO LastOperations ( ticker, operation, indicator, timestamp)
        VALUES ($1, $2, (SELECT indicator_id FROM Indicators WHERE name = $3 AND strategy = $4), $5)
        ON CONFLICT (ticker)
        DO UPDATE SET
            operation = EXCLUDED.operation,
            indicator = EXCLUDED.indicator,
            timestamp = EXCLUDED.timestamp;
    `;


    const values = [
        operation.ticker,
        operation.operation,
        operation.indicator,
        operation.strategy,
        operation.timestamp,
    ];
    
    await client.query(query, values);
    if(operation.operation === 'Buy' || operation.operation === 'Sell'){
        await recordOperation(operation, client);        
    }
    console.log(`Recorded operation for ticker ${operation.ticker}: ${operation.operation}.`);

}

export async function getOperation(ticker: string, client: PostgresClient): Promise<Operation | null> {
    const query = ` 
        SELECT * FROM Operations 
        WHERE ticker = $1 
        ORDER BY timestamp DESC 
        LIMIT 1
    `;

    const result = await client.query(query, [ticker]);
    if (result.rows.length === 0) {
        return null;
    } else {
        const indicatorDetails = await getIndicatorDetailsById(result.rows[0].indicator, client);
        if (indicatorDetails){
            return {
                ticker: result.rows[0].ticker,
                strategy: indicatorDetails.strategy,
                operation: result.rows[0].operation,
                indicator: indicatorDetails.name,
                timestamp: result.rows[0].timestamp
            };
        } else {
            return null;
        }
    }    
}

export async function getLastOperation(ticker: string, client: PostgresClient): Promise<Operation | null> {
    const query = `
        SELECT * FROM LastOperations 
        WHERE ticker = $1 
        LIMIT 1
    `;

    const result = await client.query(query, [ticker]);
    if (result.rows.length === 0) {
        return null;
    } else {
        const indicatorDetails = await getIndicatorDetailsById(result.rows[0].indicator, client);
        if (indicatorDetails){
            return {
                ticker: result.rows[0].ticker,
                strategy: indicatorDetails.strategy,
                operation: result.rows[0].operation,
                indicator: indicatorDetails.name,
                timestamp: result.rows[0].timestamp
            };
        } else {
            return null;
        }
    }
}

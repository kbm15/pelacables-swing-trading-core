// src/db/operationsQueries.ts
import { Client as PostgresClient } from 'pg';
import { v4 as uuidv4 } from 'uuid';
import type { Operation } from '../types';
import { getIndicatorDetailsById } from './indicatorQueries';

export async function recordOperation(operation: Operation, client: PostgresClient) {

    const query = `
        INSERT INTO Operations (operation_id, ticker, operation, indicator, timestamp)
        VALUES ($1, $2, $3, $4, $5)
    `;

    const operation_id = uuidv4();
    const values = [
        operation_id,
        operation.ticker,
        operation.operation,
        operation.indicator,
        operation.timestamp,
    ];

    await client.query(query, values);
    console.log(`Recorded operation for ticker ${operation.ticker}: ${operation.operation}.`);
}

export async function getLastOperation(ticker: string, client: PostgresClient): Promise<Operation | null> {

    const query = ` 
        SELECT * FROM Operations 
        WHERE ticker = $1 
        AND operation IN ('Buy', 'Sell')
        ORDER BY timestamp DESC 
        LIMIT 1
    `;

    const result = await client.query(query, [ticker]);
    if (result.rows.length === 0) {
        return null;
    } else {
        const indicatorDetails = await getIndicatorDetailsById(result.rows[0].indicator, client);
        if (indicatorDetails) {
            const operation : Operation = {
                ticker: result.rows[0].ticker,
                strategy: indicatorDetails.strategy,
                operation: result.rows[0].operation,
                indicator: indicatorDetails.name,
                timestamp: result.rows[0].timestamp
            }
            return operation;
        } else {
            const operation : Operation = {
                ticker: result.rows[0].ticker,
                strategy: 'None',
                operation: result.rows[0].operation,
                indicator: 'None',
                timestamp: result.rows[0].timestamp
            }
            return operation;
        }        
    }    
}

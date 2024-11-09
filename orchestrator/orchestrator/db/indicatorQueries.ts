// src/db/indicatorQueries.ts
import { Client as PostgresClient } from 'pg';
import { v4 as uuidv4 } from 'uuid';
import type { TickerIndicator } from '../types';


const IndicatorStrategies = {
    "AwesomeOscillator": ["SMA_Crossover"],
    "BollingerBands": ["Bollinger"],
    "IchimokuCloud": ["Ichimoku", "Kumo", "KumoChikou", "Kijun", "KijunPSAR", "TenkanKijun", "KumoTenkanKijun", "TenkanKijunPSAR", "KumoTenkanKijunPSAR", "KumoKiyunPSAR", "KumoChikouPSAR", "KumoKiyunChikouPSAR"],
    "KeltnerChannel": ["KC"],
    "MovingAverage": ["MA"],
    "MACD": ["MACD"],
    "PSAR": ["PSAR"],
    "RSI": ["RSI", "RSI_Falling", "RSI_Divergence", "RSI_Cross"],
    "VolumeIndicator": ["Volume"],
    "Hold": ["Hold"]
}

export async function insertIndicators(client: PostgresClient) {
    const now = new Date().toISOString(); // Current timestamp in ISO format (UTC)

    try {
        for (const [indicator, strategies] of Object.entries(IndicatorStrategies)) {
            for (const strategy of strategies) {
                const indicatorId = uuidv4();

                const queryText = `
                    INSERT INTO Indicators (indicator_id, name, description, strategy, configurations, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                `;

                const values = [
                    indicatorId,
                    indicator,
                    `Description for ${indicator}`,   // Example description
                    strategy,
                    '{}',                             // Placeholder for configurations
                    now,
                    now
                ];

                await client.query(queryText, values);
                console.log(`Inserted indicator ${indicator} with strategy ${strategy}`);
            }
        }
        console.log('All indicators inserted successfully.');
    } catch (err) {
        console.error('Error inserting indicators:', err);
    }     
}

export async function countIndicators(client: PostgresClient): Promise<number> {    
    const result = await client.query<{ count: string }>('SELECT COUNT(*) FROM Indicators');
    const count = parseInt(result.rows[0].count, 10);
    if (count > 0) {
        console.log(`Number of elements in Indicator: ${count}`);
        return count;
    } else {
        console.log('No elements found in Indicator.');
        return 0;
    }
}

export async function saveBestIndicator(tickerIndicator: TickerIndicator, client: PostgresClient) {
    const now = new Date().toISOString(); // Current timestamp in ISO format (UTC)
    const queryText = `
        INSERT INTO TickerIndicators (ticker, indicator_id, total_return, created_at, updated_at)
        VALUES ($1, (SELECT indicator_id FROM Indicators WHERE name = $2 AND strategy = $3), $4, $5, $6)
        ON CONFLICT (ticker) DO UPDATE
        SET indicator_id = (SELECT indicator_id FROM Indicators WHERE name = $2 AND strategy = $3), updated_at = $6
    `;

    const values = [ tickerIndicator.ticker, tickerIndicator.name, tickerIndicator.strategy, tickerIndicator.total_return, now, now ];    
    try {
        await client.query(queryText, values);
        console.log(`Saved best indicator for ticker ${tickerIndicator.ticker}.`);
    } catch (err) {
        console.error(`Failed to save best indicator for ticker ${tickerIndicator.ticker}:`, err);
    }
    
}

export async function getBestIndicator(ticker: string, client: PostgresClient): 
    Promise<{ indicator: string, strategy: string, total_return: number, createdAt: Date, updatedAt: Date } | null> {
    const queryText = `
        SELECT indicator_id, total_return, created_at, updated_at
        FROM TickerIndicators
        WHERE ticker = $1
    `;
    const values = [ticker];

    try {
        const result = await client.query(queryText, values);

        if (result.rows.length > 0) {
            const indicatorId = result.rows[0].indicator_id;
            const indicatorDetails = await getIndicatorDetailsById(indicatorId, client);
            if (indicatorDetails) {
                return {
                    indicator: indicatorDetails.name,
                    strategy: indicatorDetails.strategy,                    
                    total_return: result.rows[0].total_return,
                    createdAt: new Date(result.rows[0].created_at),
                    updatedAt: new Date(result.rows[0].updated_at)
                };
            } else {
                console.log(`No indicator found for indicator ID ${indicatorId} for ticker ${ticker}`);
                return null;
            }

        } else {
            console.log(`No best indicator found for ticker ${ticker}`);
            return null;
        }
    } catch (err) {
        console.error(`Failed to get best indicator for ticker ${ticker}:`, err);
        return null;
    }
}

export async function getIndicatorDetailsById(indicatorId: string, client: PostgresClient): Promise<{ name: string, strategy: string } | null> {
    const queryText = `
        SELECT name, strategy
        FROM Indicators
        WHERE indicator_id = $1
    `;
    const values = [indicatorId];

    try {
        const result = await client.query<{ name: string, strategy: string }>(queryText, values);

        if (result.rows.length > 0) {
            return {
                name: result.rows[0].name,
                strategy: result.rows[0].strategy
            };
        } else {
            console.log(`No indicator found with ID: ${indicatorId}`);
            return null;
        }
    } catch (err) {
        console.error(`Failed to get indicator details for ID: ${indicatorId}`, err);
        return null;
    }
}

export async function getIndicatorIdByNameAndStrategy(name: string, strategy: string, client: PostgresClient): Promise<string | null> {
    const queryText = `
        SELECT indicator_id
        FROM Indicators
        WHERE name = $1 AND strategy = $2
    `;
    const values = [name, strategy];

    try {
        const result = await client.query(queryText, values);
        console.log(result.rows);
        const indicatorId = result.rows[0].indicator_id;
        console.log(`Found indicator ID: ${indicatorId} for name: ${name} and strategy: ${strategy}`);

        if (indicatorId) {
            return indicatorId;
        } else {
            console.log(`No indicator found with name: ${name} and strategy: ${strategy}`);
            return null;
        }
    } catch (err) {
        console.error(`Failed to get indicator ID for name: ${name} and strategy: ${strategy}`, err);
        return null;
    }
}

export async function getAllIndicators(client: PostgresClient): 
Promise<{ indicatorId: string, name: string, strategy: string } []> {
    const queryText = `
        SELECT indicator_id, name, strategy
        FROM Indicators
    `;

    try {
        const result = await client.query<{ indicatorId: string, name: string, strategy: string }>(queryText);
        return result.rows.map(row => ({
                indicatorId: row.indicatorId,
                name: row.name,
                strategy: row.strategy
            
        }));

    } catch (err) {
        console.error('Failed to get all indicators:', err);
        return [];
    }
}

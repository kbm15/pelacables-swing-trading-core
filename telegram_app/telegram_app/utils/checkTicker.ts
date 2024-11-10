// checkTicker.ts
import yahooFinance from 'yahoo-finance2';

type Interval = '1mo' | '1m' | '2m' | '5m' | '15m' | '30m' | '60m' | '90m' | '1h' | '1d' | '5d' | '1wk' | '3mo';

/**
 * Checks if a ticker exists on Yahoo Finance.
 * @param ticker The ticker symbol to check, e.g., "AAPL" or "GOOGL".
 * @returns A promise that resolves to `true` if the ticker exists, or `false` if it does not.
 */
export async function doesTickerExist(ticker: string): Promise<boolean> {
    try {
        // Attempt to fetch the quote for the given ticker
        const queryOptions = {
            period1: new Date(Date.now() - 1000 * 60 * 60 * 24 * 365 * 2), // 2 years ago
            interval: '1mo' as Interval
        };
        const result = await yahooFinance.chart(ticker, queryOptions);
        return result.quotes.length > 0; // If quote data exists, the ticker is valid
    } catch (error) {
        
        console.error(`Error fetching ticker ${ticker}:`, error);
        return false;
        
    }
}
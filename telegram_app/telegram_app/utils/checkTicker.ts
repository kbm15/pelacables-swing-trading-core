// checkTicker.ts
import yahooFinance from 'yahoo-finance2';

/**
 * Checks if a ticker exists on Yahoo Finance.
 * @param ticker The ticker symbol to check, e.g., "AAPL" or "GOOGL".
 * @returns A promise that resolves to `true` if the ticker exists, or `false` if it does not.
 */
export async function doesTickerExist(ticker: string): Promise<boolean> {
    try {
        // Attempt to fetch the quote for the given ticker
        const quote = await yahooFinance.quote(ticker);
        return !!quote; // If quote data exists, the ticker is valid
    } catch (error) {
        // Handle specific error codes that indicate the ticker is invalid
        if (error instanceof yahooFinance.errors.NotFoundError) {
            console.error(`Ticker ${ticker} not found.`);
            return false;
        } else {
            console.error(`Error fetching ticker ${ticker}:`, error);
            throw error; // Rethrow error if it's not a "Not Found" error
        }
    }
}
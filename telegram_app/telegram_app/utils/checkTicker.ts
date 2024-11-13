// checkTicker.ts
import yahooFinance from 'yahoo-finance2';

type Interval = '1mo' | '1m' | '2m' | '5m' | '15m' | '30m' | '60m' | '90m' | '1h' | '1d' | '5d' | '1wk' | '3mo';

/**
 * Checks if a ticker exists on Yahoo Finance.
 * @param ticker The ticker symbol to check, e.g., "AAPL" or "GOOGL".
 * @returns A promise that resolves to `true` if the ticker exists, or `false` if it does not.
 */
export async function findTicker(ticker: string): Promise<Record<string, {longname: string, symbol: string}[]>> {
    const foundTickers: Record<string, {longname: string, symbol: string}[]> = {'quotes': []};
    try {
        // Attempt to fetch the quote for the given ticker        
        const result = await yahooFinance.search(ticker);
        
        if (result.quotes.length > 0){
            for(const quote of result.quotes){
                if(quote.isYahooFinance){
                    if(quote.symbol === ticker){
                        return {'quotes': [{longname: quote.longname ?? '', symbol: quote.symbol}]};
                    } else {
                        foundTickers.quotes.push({longname: quote.longname ?? '', symbol: quote.symbol});
                    }                    
                }
            }
            return foundTickers;
        }
        
    } catch (error) {
        
        console.error(`Error fetching ticker ${ticker}:`, error);
        return foundTickers;
        
    }
    return foundTickers;
}

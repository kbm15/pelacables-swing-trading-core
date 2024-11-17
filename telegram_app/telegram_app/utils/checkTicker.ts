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
    let result;
    try {     
        yahooFinance.setGlobalConfig({ validation: { logErrors: false} });
        result = await yahooFinance.search(ticker);
        
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
        console.error(`Error searching ticker ${ticker}:`, error);
        
    }
    return foundTickers;
}

export async function checkTicker(ticker: string): Promise<boolean> {
    const exchangeWhitelist = ['CCC','NMS','NYQ','PCX','NGM','MCE','PAR','MIL','GER','BRU','AMS','LSE','HKG','SHH','JPX','ASX']
    let result;
    try {
        yahooFinance.setGlobalConfig({ validation: { logErrors: false} });
        result = await yahooFinance.quote(ticker);
        if (result !== undefined && result.firstTradeDateMilliseconds !== undefined && result.exchange !== undefined && result.regularMarketPrice !== undefined) {
            if (exchangeWhitelist.includes(result.exchange)) {
                if (result.firstTradeDateMilliseconds <= new Date(Date.now() - 1 * 365 * 24 * 60 * 60 * 1000)) {
                    console.log(`Ticker ${ticker} first trade was in ${result.firstTradeDateMilliseconds.toUTCString()}`);
                    console.log(`Current price is ${result.regularMarketPrice} on ${result.exchange}`);
                    return true;            
                } else {
                    console.log(`Ticker ${ticker} is too new`);
                    return false;
                }
            } else {
                console.log(`Ticker ${ticker} is on ${result.exchange}`);
                return false;
            }
        }
    } catch (error) {
        if (error instanceof yahooFinance.errors.FailedYahooValidationError) {
            console.warn(`Skipping yf.quote("${ticker}"): [FailedYahooValidationError]`);
            return false; 
        } else if (error instanceof yahooFinance.errors.HTTPError) {
            console.warn(`Skipping yf.quote("${ticker}"): [HTTPError]`);
            return false; 
        } else {
            console.warn(`Skipping yf.quote("${ticker}"): [UnknownError]`);
            return false; 
        }
      }
      
    return false;    
}
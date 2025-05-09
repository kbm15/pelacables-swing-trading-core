// checkTicker.ts
import yahooFinance from 'yahoo-finance2';

type Interval = '1mo' | '1m' | '2m' | '5m' | '15m' | '30m' | '60m' | '90m' | '1h' | '1d' | '5d' | '1wk' | '3mo';

/**
 * Checks if a ticker exists on Yahoo Finance.
 * @param ticker The ticker symbol to check, e.g., "AAPL" or "GOOGL".
 * @returns A promise that resolves to `true` if the ticker exists, or `false` if it does not.
 */

export async function findTicker(ticker: string): Promise<Record<string, {longname: string, symbol: string}[]>> {
    console.log(`Searching for ticker ${ticker}`);
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
    console.log(`Checking ticker ${ticker}`);
    const exchangeWhitelist = ['CCC','NMS','NYQ','NCM','PCX','NGM','MCE','PAR','MIL','GER','BRU','AMS','LSE','HKG','SHH','JPX','ASX']
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

export async function getTickerExchange(ticker: string): Promise<string> {
    console.log(`Getting exchange for ${ticker}`);
    const exchangeNames: { [key: string]: string } = {
        "CCC": "CRYPTO",
        "NMS": "NASDAQ",
        "NYQ": "NYSE",
        "PCX": "AMEX",
        "NCM": "NASDAQ",
        "NGM": "NASDAQ",
        "MCE": "BME",
        "PAR": "EURONEXT",
        "MIL": "MIL",
        "GER": "XETR",
        "BRU": "EURONEXT",
        "AMS": "EURONEXT",
        "LSE": "LSE",
        "HKG": "HKEX",
        "SHH": "SSE",
        "JPX": "TSE",
        "ASX": "ASX"
    }
    let result;
    try {
        yahooFinance.setGlobalConfig({ validation: { logErrors: false} });
        result = await yahooFinance.quote(ticker);
        if (result !== undefined && result.exchange !== undefined) {
            return exchangeNames[result.exchange];
        }
    } catch (error) {
        console.warn(`Skipping yf.quote("${ticker}"): [UnknownError]`);
    }
    return '';
}

export async function formatTickerMessage(ticker: string): Promise<string> {
    console.log(`Formatting ticker ${ticker}`);
    try {
        yahooFinance.setGlobalConfig({ validation: { logErrors: false} });
        const data = await yahooFinance.quote(ticker);
        const summary = await yahooFinance.quoteSummary(ticker, { modules: [ "financialData" ] });
        const {
            longName,
            symbol,
            regularMarketDayRange,
            fiftyTwoWeekRange,
            marketCap,
            trailingPE,
            epsTrailingTwelveMonths,
            earningsTimestampStart,
            earningsTimestampEnd,
            trailingAnnualDividendRate,
            trailingAnnualDividendYield,
            dividendDate,
            beta
        } = data;

        const {
            targetHighPrice,
            targetLowPrice,
            targetMeanPrice,
            recommendationKey
        } = summary.financialData ?? {};
    
        // Helper: Format Market Cap with Suffix
        const formatMarketCap = (value: number): { formatted: string; category: string } => {
            if (value >= 1e12) return { formatted: `${(value / 1e12).toFixed(2)}T`, category: "Mega" };
            if (value >= 1e9) {
                if (value >= 2e11) return { formatted: `${(value / 1e9).toFixed(2)}B`, category: "Mega" };
                if (value >= 1e10) return { formatted: `${(value / 1e9).toFixed(2)}B`, category: "Large" };
            }
            if (value >= 1e9) return { formatted: `${(value / 1e9).toFixed(2)}B`, category: "Mid" };
            if (value >= 3e8) return { formatted: `${(value / 1e6).toFixed(2)}M`, category: "Small" };
            if (value >= 5e7) return { formatted: `${(value / 1e6).toFixed(2)}M`, category: "Micro" };
            return { formatted: `${(value / 1e6).toFixed(2)}M`, category: "Nano" };
        };
    
        const { formatted: formattedMarketCap, category: marketCapCategory } = formatMarketCap(marketCap ?? 0);
    
        // Determine Dividend Sustainability Color
        let dividendColor = "⚫"; // Default to black (⚫)
        if (trailingAnnualDividendRate && epsTrailingTwelveMonths) {
            const dividendRatio = (trailingAnnualDividendRate / epsTrailingTwelveMonths) * 100;
            if (dividendRatio >= 0 && dividendRatio <= 35) {
                dividendColor = "🔵"; // Blue 🔵
            } else if (dividendRatio > 35 && dividendRatio <= 55) {
                dividendColor = "🟢"; // Green 🟢
            } else if (dividendRatio <= 95) {
                dividendColor = "🟠"; // Orange 🟠
            } else {
                dividendColor = "🔴"; // Red 🔴
            }
        }

    
        const dividendInfo = trailingAnnualDividendRate
            ? `\$${trailingAnnualDividendRate.toFixed(2)} (${(trailingAnnualDividendYield ?? 0 * 100).toFixed(2)}%)`
            : "N/A";
        const exDividendDate = dividendDate ? new Date(dividendDate).toLocaleDateString() : "N/A";
        const earningsDate = earningsTimestampStart && earningsTimestampEnd
            ? `${new Date(earningsTimestampEnd).toLocaleDateString()}`
            : "N/A";
        const targetPrice = targetHighPrice && targetLowPrice && targetMeanPrice
            ? `\$${targetMeanPrice?.toFixed(2)} (\$${targetLowPrice.toFixed(2)} - \$${targetHighPrice.toFixed(2)})`
            : "N/A";
    
        const formattedMessage = 
            `📊 *${longName}* (\`${symbol}\`)\n\n` +
            `*🔑 Métricas Clave*\n` +
            `- *Rango diario:* $${regularMarketDayRange?.low.toFixed(2)} - $${regularMarketDayRange?.high.toFixed(2)}\n` +
            `- *Rango 52 sem:* $${fiftyTwoWeekRange?.low.toFixed(2)} - $${fiftyTwoWeekRange?.high.toFixed(2)}\n\n` +
            `*📈 Valoración*\n` +
            `- *Capitalización:* ${formattedMarketCap} (${marketCapCategory} Cap)\n` +
            `- *Beta (5a):* ${(beta ?? 0).toFixed(2)}\n` +
            `- *Ratio Precio/Beneficios:* ${(trailingPE ?? 0).toFixed(2)}\n` +
            `- *Beneficio por Acción:* $${(epsTrailingTwelveMonths ?? 0).toFixed(2)}\n\n` +
            `*💵 Ganancias y Dividendos*\n` +
            `- *Fecha de Resultados:* ${earningsDate}\n` +
            `- *Dividendos (Rentab):* ${dividendInfo}\n` +
            `- *Valoración Dividendo:* ${dividendColor}\n` +
            `- *Fecha Ex-Div:* ${exDividendDate}\n\n` +
            `*🎯 Estimación de Precio Objetivo*\n` +
            `- *1 Año:* ${targetPrice}`;
    
        return formattedMessage;
    }
    catch (error) {
        if (error instanceof yahooFinance.errors.FailedYahooValidationError) {
            console.warn(`Skipping yf.quote("${ticker}"): [FailedYahooValidationError]`);
            return ''; 
        } else if (error instanceof yahooFinance.errors.HTTPError) {
            console.warn(`Skipping yf.quote("${ticker}"): [HTTPError]`);
            return ''; 
        } else {
            console.warn(`Skipping yf.quote("${ticker}"): [UnknownError]`);
            return ''; 
        }
      }
    return '';
}
    
    
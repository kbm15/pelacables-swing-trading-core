export interface Request {
    ticker: string;
    indicator: string;
    strategy: string;
    backtest: boolean;
    userId: number;
    chatId: number;
}

export interface Response {
    ticker: string;
    indicator: string;
    strategy: string;
    backtest: boolean;
    signal: string;
    total_return: number | null;
    chatId: number | null;
}

export interface Operation {
    ticker: string;
    operation: string;
    indicator: string;
    strategy: string;
    timestamp: Date;
}

export interface TickerResponseAggregator {
    timestamp: number;
    responses: Response[];
}

export interface ResponseAggregator {
    [ticker: string]: TickerResponseAggregator;
}
export interface Request {
    ticker: string;
    indicator: string;
    strategy: string;
    flag: 'simple' | 'backtest' | 'notification';
    chatId: number;
}

export interface Response {
    ticker: string;
    indicator: string;
    strategy: string;
    flag: 'simple' | 'backtest' | 'notification';
    signal: string;
    total_return: number;
    chatId: number | null;
}

export interface Operation {
    ticker: string;
    operation: string;
    indicator: string;
    strategy: string;
    timestamp: Date;
}

export interface Subscription {
    ticker: string;
    userIds: string[];
}

export interface Indicator {
    indicatorId: string;
    name: string;
    description: string;
    strategy: string;
    configurations: Record<string, any>;
    createdAt: Date;
    updatedAt: Date;
}

export interface TickerIndicator {
    ticker: string;
    name: string;
    strategy: string;
    total_return: number;
    createdAt: Date;
    updatedAt: Date;
}

export interface TickerResponseAggregator {
    timestamp: number;
    responses: Response[];
}

export interface ResponseAggregator {
    [ticker: string]: TickerResponseAggregator;
}
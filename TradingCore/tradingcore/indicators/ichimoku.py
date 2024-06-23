import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import Indicator
from .psar import PSARIndicator


class IchimokuIndicator(Indicator):
    def __init__(self, strategy: str = None ):
        self.strategy = strategy
        self.components = pd.DataFrame(columns=['Ichimoku_Tenkan', 'Ichimoku_Kijun', 'Ichimoku_SenkouA', 'Ichimoku_SenkouB', 'Ichimoku_Chikou', 'Ichimoku_Signal'])

    def calculate(self, data: pd.DataFrame):
        # Calculate Ichimoku components
        ichimokudf, spandf = ta.ichimoku(data['High'], data['Low'], data['Close'])
         
        # If no strategy is specified, return the Ichimoku components
        if self.strategy is None:            
            return ichimokudf['ITS_9'], ichimokudf['IKS_26'], ichimokudf['ISA_9'], ichimokudf['ISB_26'], visible_period['ICS_26']
        
        # Assign Ichimoku components to the DataFrame
        self.components['Ichimoku_Tenkan'] = ichimokudf['ITS_9']
        self.components['Ichimoku_Kijun'] = ichimokudf['IKS_26']
        self.components['Ichimoku_SenkouA'] = ichimokudf['ISA_9']
        self.components['Ichimoku_SenkouB'] = ichimokudf['ISB_26']
        self.components['Ichimoku_Chikou'] = ichimokudf['ICS_26']
        self.components['Ichimoku_Signal'] = 0

        # Apply different strategies based on the strategy parameter
        if self.strategy == 'Ichimoku':
            # Buy signal: Tenkan-sen > Kijun-sen and price > Senkou Span A and price > Senkou Span B
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Tenkan'] > self.components['Ichimoku_Kijun']) & 
                (data['Close'] > self.components['Ichimoku_SenkouA']) & 
                (data['Close'] > self.components['Ichimoku_SenkouB']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Tenkan-sen < Kijun-sen and price < Senkou Span A and price < Senkou Span B
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Tenkan'] < self.components['Ichimoku_Kijun']) & 
                (data['Close'] < self.components['Ichimoku_SenkouA']) & 
                (data['Close'] < self.components['Ichimoku_SenkouB']), 
                -1, self.components['Ichimoku_Signal'])
        
        elif self.strategy == 'Kumo':
            # Buy signal: Price > Senkou Span A and price > Senkou Span B
            self.components['Ichimoku_Signal'] = np.where(
                (data['Close'] > self.components['Ichimoku_SenkouA']) & 
                (data['Close'] > self.components['Ichimoku_SenkouB']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Price < Senkou Span A and price > Senkou Span B
            self.components['Ichimoku_Signal'] = np.where(
                (data['Close'] < self.components['Ichimoku_SenkouA']) & 
                (data['Close'] > self.components['Ichimoku_SenkouB']), 
                -1, self.components['Ichimoku_Signal'])
        
        elif self.strategy == 'KumoChikou':
            # Buy signal: Price > Senkou Span A, price > Senkou Span B, and Chikou Span > price 26 periods ago
            self.components['Ichimoku_Signal'] = np.where(
                (data['Close'] > self.components['Ichimoku_SenkouA']) & 
                (data['Close'] > self.components['Ichimoku_SenkouB']) & 
                (self.components['Ichimoku_Chikou'] > data['Close'].shift(26)), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Price < Senkou Span A, price > Senkou Span B, and Chikou Span < price 26 periods ago
            self.components['Ichimoku_Signal'] = np.where(
                (data['Close'] < self.components['Ichimoku_SenkouA']) & 
                (data['Close'] > self.components['Ichimoku_SenkouB']) & 
                (self.components['Ichimoku_Chikou'] < data['Close'].shift(26)), 
                -1, self.components['Ichimoku_Signal'])
        
        elif self.strategy == 'TenkanKijun':
            # Buy signal: Tenkan-sen > Kijun-sen
            self.components['Ichimoku_Signal'] = np.where(
                self.components['Ichimoku_Tenkan'] > self.components['Ichimoku_Kijun'], 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Tenkan-sen < Kijun-sen
            self.components['Ichimoku_Signal'] = np.where(
                self.components['Ichimoku_Tenkan'] < self.components['Ichimoku_Kijun'], 
                -1, self.components['Ichimoku_Signal'])
        
        elif self.strategy == 'TenkanKijunPSAR':
            # Calculate PSAR indicator
            data['PSAR_Long'], data['PSAR_Short'] = PSARIndicator().calculate(data)
            
            # Buy signal: Tenkan-sen > Kijun-sen and price > PSAR
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Tenkan'] > self.components['Ichimoku_Kijun']) & 
                (data['Close'] > data['PSAR_Long']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Tenkan-sen < Kijun-sen and price < PSAR
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Tenkan'] < self.components['Ichimoku_Kijun']) & 
                (data['Close'] < data['PSAR_Short']), 
                -1, self.components['Ichimoku_Signal'])

        return self.components['Ichimoku_Signal']

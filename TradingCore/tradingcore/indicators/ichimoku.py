import pandas as pd
import pandas_ta as ta
import numpy as np
from .base import Indicator
from .psar import PSARIndicator
import hashlib


class IchimokuIndicator(Indicator):
    POSSIBLE_STRATEGIES=[None,'Ichimoku','Kumo','KumoChikou','Kijun','KijunPSAR','TenkanKijun','KumoTenkanKijun',
                        'TenkanKijunPSAR' ,'KumoTenkanKijunPSAR','KumoKiyunPSAR','KumoChikouPSAR','KumoKiyunChikouPSAR']
    # POSSIBLE_STRATEGIES+=['Ichimoku2', 'Kumo2', 'KumoChikou2', 'Kijun2', 'KijunPSAR2', 'TenkanKijun2', 'KumoTenkanKijun2', 'TenkanKijunPSAR2', 'KumoTenkanKijunPSAR2', 'KumoKiyunPSAR2', 'KumoChikouPSAR2', 'KumoKiyunChikouPSAR2']
    # POSSIBLE_STRATEGIES+=['KumoTenkanKijun2','KumoTenkanKijun3','KumoTenkanKijun4','KumoTenkanKijun5','KumoTenkanKijun6']
    def __init__(self, strategy: str = None, tenkan=9, kijun=26, senkou=52, include_chikou=True):
        self.strategy = strategy
        self.tenkan = tenkan
        self.kijun = kijun
        self.senkou = senkou
        self.chikou = include_chikou
        self.components = pd.DataFrame(columns=['Ichimoku_Tenkan', 'Ichimoku_Kijun', 'Ichimoku_SenkouA', 'Ichimoku_SenkouB', 'Ichimoku_Chikou', 'Ichimoku_Signal'])
        self.data_hash = None

    def _hash_data(self, data):
        return hashlib.sha256(pd.util.hash_pandas_object(data).values).hexdigest()

    def _compare(self, key, series1, series2, op):
        if key not in self.cache:
            self.cache[key] = op(series1, series2)
        return self.cache[key]
    
    def setStrategy(self, strategy: str = None):
        if strategy not in self.POSSIBLE_STRATEGIES:
            raise ValueError(f"Strategy {strategy} is not allowed. Possible strategies: {self.POSSIBLE_STRATEGIES}")
        self.strategy = strategy

    def calculate(self, data: pd.DataFrame):
        data_hash = self._hash_data(data)
        # Check if the data has changed
        if self.data_hash != data_hash:
            # print(f"Data has changed, old hash {self.data_hash} vs new hash {data_hash}. Recalculating Ichimoku parameters.")
            # Update the hash
            self.data_hash = data_hash
            # Calculate Ichimoku components
            ichimokudf, spandf = ta.ichimoku(data['High'], data['Low'], data['Close'],
                                             tenkan=self.tenkan, kijun=self.kijun, senkou=self.senkou, include_chikou=self.chikou)

            # Assign Ichimoku components to the DataFrame
            self.components['Ichimoku_Tenkan'] = ichimokudf['ITS_9']
            self.components['Ichimoku_Kijun'] = ichimokudf['IKS_26']
            self.components['Ichimoku_SenkouA'] = ichimokudf['ISA_9']
            self.components['Ichimoku_SenkouB'] = ichimokudf['ISB_26']
            self.components['Ichimoku_Chikou'] = ichimokudf['ICS_26']

        self.components['Ichimoku_Signal'] = 0
         
        # If no strategy is specified, return the Ichimoku components
        if self.strategy is None:            
            return self.components['Ichimoku_Tenkan'], self.components['Ichimoku_Kijun'], self.components['Ichimoku_SenkouA'], self.components['Ichimoku_SenkouB'], self.components['Ichimoku_Chikou']

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
                (data['Close'] > self.components['Ichimoku_SenkouA']) , 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Price < Senkou Span A and price > Senkou Span B
            self.components['Ichimoku_Signal'] = np.where(
                (data['Close'] < self.components['Ichimoku_SenkouA']) & 
                (data['Close'] < self.components['Ichimoku_SenkouB']), 
                -1, self.components['Ichimoku_Signal'])
        
        elif self.strategy == 'KumoChikou':
            # Buy signal: Price > Senkou Span A, price > Senkou Span B, and Chikou Span > price 26 periods ago
            self.components['Ichimoku_Signal'] = np.where(
                (data['Close'] > self.components['Ichimoku_SenkouA']) &  
                (self.components['Ichimoku_Chikou'].shift(26) > data['Close'].shift(26)), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Price < Senkou Span A, price > Senkou Span B, and Chikou Span < price 26 periods ago
            self.components['Ichimoku_Signal'] = np.where(
                (data['Close'] < self.components['Ichimoku_SenkouA']) & 
                (data['Close'] < self.components['Ichimoku_SenkouB']) &  
                (self.components['Ichimoku_Chikou'].shift(26) < data['Close'].shift(26)), 
                -1, self.components['Ichimoku_Signal'])
        
        elif self.strategy == 'Kijun':
            # Buy signal: Price > Kijun
            self.components['Ichimoku_Signal'] = np.where(
                self.components['Ichimoku_Kijun'] < data['Close'], 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Price < Kijun-sen
            self.components['Ichimoku_Signal'] = np.where(
                self.components['Ichimoku_Kijun'] > data['Close'], 
                -1, self.components['Ichimoku_Signal'])
        
        elif self.strategy == 'KijunPSAR':
            # Calculate PSAR indicator
            self.components['PSAR_Long'], self.components['PSAR_Short'] = PSARIndicator().calculate(data)
            # Buy signal: Price > Kijun
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] < data['Close']) &
                (data['Close'] > self.components['PSAR_Long']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Price < Kijun-sen
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] > data['Close']) &
                (data['Close'] < self.components['PSAR_Short']), 
                -1, self.components['Ichimoku_Signal'])
        
        # Bad strat
        elif self.strategy == 'TenkanKijun':
            # Buy signal: Tenkan-sen > Kijun-sen
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Tenkan'] > self.components['Ichimoku_Kijun']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Tenkan-sen < Kijun-sen
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] > data['Close']) &
                (self.components['Ichimoku_Tenkan'] < self.components['Ichimoku_Kijun']), 
                -1, self.components['Ichimoku_Signal'])

        elif self.strategy == 'KumoTenkanKijun':
            # Buy signal: Tenkan-sen > Kijun-sen
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Tenkan'] > self.components['Ichimoku_Kijun']) &
                (data['Close'] > self.components['Ichimoku_SenkouA']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Tenkan-sen < Kijun-sen
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Tenkan'] < self.components['Ichimoku_Kijun']) &
                (data['Close'] < self.components['Ichimoku_SenkouA']) & 
                (data['Close'] < self.components['Ichimoku_SenkouB']), 
                -1, self.components['Ichimoku_Signal'])   
            
        # Bad strat
        elif self.strategy == 'TenkanKijunPSAR':
            # Calculate PSAR indicator
            self.components['PSAR_Long'], self.components['PSAR_Short'] = PSARIndicator().calculate(data)
            
            # Buy signal: Tenkan-sen > Kijun-sen and price > PSAR
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] < data['Close']) &
                (self.components['Ichimoku_Tenkan'] > self.components['Ichimoku_Kijun']) & 
                (data['Close'] > self.components['PSAR_Long']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Tenkan-sen < Kijun-sen and price < PSAR
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] > data['Close']) &
                (self.components['Ichimoku_Tenkan'] < self.components['Ichimoku_Kijun']) & 
                (data['Close'] < self.components['PSAR_Short']), 
                -1, self.components['Ichimoku_Signal'])
            
        elif self.strategy == 'KumoTenkanKijunPSAR':
            # Calculate PSAR indicator
            self.components['PSAR_Long'], self.components['PSAR_Short'] = PSARIndicator().calculate(data)
            
            # Buy signal: Tenkan-sen > Kijun-sen and price > PSAR
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] < data['Close']) &
                (self.components['Ichimoku_Tenkan'] > self.components['Ichimoku_Kijun']) & 
                ((data['Close'] > self.components['Ichimoku_SenkouA']) & 
                (data['Close'] > self.components['Ichimoku_SenkouB'])) &
                (data['Close'] > self.components['PSAR_Long']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Tenkan-sen < Kijun-sen and price < PSAR
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Tenkan'] < self.components['Ichimoku_Kijun']) & 
                (data['Close'] < self.components['Ichimoku_SenkouA']) &
                (data['Close'] < self.components['Ichimoku_SenkouB']) &
                (data['Close'] < self.components['PSAR_Short']), 
                -1, self.components['Ichimoku_Signal'])
            
        elif self.strategy == 'KumoKiyunPSAR':
            # Calculate PSAR indicator
            self.components['PSAR_Long'], self.components['PSAR_Short'] = PSARIndicator().calculate(data)
            
            # Buy signal: Tenkan-sen > Kijun-sen and price > PSAR
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] < data['Close']) &
                (data['Close'] > self.components['Ichimoku_SenkouA']) &
                (data['Close'] > self.components['Ichimoku_SenkouB']) &
                (data['Close'] > self.components['PSAR_Long']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Tenkan-sen < Kijun-sen and price < PSAR
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] > data['Close']) &
                (data['Close'] < self.components['Ichimoku_SenkouA']) &
                (data['Close'] < self.components['Ichimoku_SenkouB']) &
                (data['Close'] < self.components['PSAR_Short']), 
                -1, self.components['Ichimoku_Signal'])
            
        elif self.strategy == 'KumoChikouPSAR':
            # Calculate PSAR indicator
            self.components['PSAR_Long'], self.components['PSAR_Short'] = PSARIndicator().calculate(data)
            
            # Buy signal: Price > Senkou Span A, price > Senkou Span B, and Chikou Span > price 26 periods ago
            self.components['Ichimoku_Signal'] = np.where(
                (data['Close'] > self.components['Ichimoku_SenkouA']) &  
                (self.components['Ichimoku_Chikou'].shift(26) > data['Close'].shift(26))&
                (data['Close'] > self.components['PSAR_Long']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Price < Senkou Span A, price > Senkou Span B, and Chikou Span < price 26 periods ago
            self.components['Ichimoku_Signal'] = np.where(
                (data['Close'] < self.components['Ichimoku_SenkouA']) & 
                (data['Close'] < self.components['Ichimoku_SenkouB']) &  
                (self.components['Ichimoku_Chikou'].shift(26) < data['Close'].shift(26)) &
                (data['Close'] < self.components['PSAR_Short']),  
                -1, self.components['Ichimoku_Signal'])
            
        elif self.strategy == 'KumoKiyunChikouPSAR':
            # Calculate PSAR indicator
            self.components['PSAR_Long'], self.components['PSAR_Short'] = PSARIndicator().calculate(data)
            
            # Buy signal: Price > Senkou Span A, price > Senkou Span B, and Chikou Span > price 26 periods ago
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] < data['Close']) &
                (data['Close'] > self.components['Ichimoku_SenkouA']) &  
                (self.components['Ichimoku_Chikou'].shift(26) > data['Close'].shift(26))&
                (data['Close'] > self.components['PSAR_Long']), 
                1, self.components['Ichimoku_Signal'])
            
            # Sell signal: Price < Senkou Span A, price > Senkou Span B, and Chikou Span < price 26 periods ago
            self.components['Ichimoku_Signal'] = np.where(
                (self.components['Ichimoku_Kijun'] > data['Close']) &
                (data['Close'] < self.components['Ichimoku_SenkouA']) & 
                (data['Close'] < self.components['Ichimoku_SenkouB']) &  
                (self.components['Ichimoku_Chikou'].shift(26) < data['Close'].shift(26)) &
                (data['Close'] < self.components['PSAR_Short']),  
                -1, self.components['Ichimoku_Signal'])
            
            ########################
            ########################
            #########TESTING########
            ########################
            ########################        
        
        
        return self.components['Ichimoku_Signal']

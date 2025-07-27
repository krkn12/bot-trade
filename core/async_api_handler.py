"""
Async API Handler para Trading Bot
Gerencia chamadas assíncronas para APIs
"""
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

class AsyncAPIHandler:
    def __init__(self, base_url: str = "https://api.binance.com", 
                 rate_limit_per_minute: int = 1200):
        self.base_url = base_url
        self.rate_limit = rate_limit_per_minute
        self.request_times = []
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _rate_limit_check(self):
        """Verifica e aplica rate limiting"""
        now = time.time()
        
        # Remove requests antigos (> 1 minuto)
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Se atingiu o limite, espera
        if len(self.request_times) >= self.rate_limit:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                return await self._rate_limit_check()
        
        self.request_times.append(now)
    
    async def get_price(self, symbol: str) -> Optional[float]:
        """Obtém preço atual de um símbolo"""
        await self._rate_limit_check()
        
        url = f"{self.base_url}/api/v3/ticker/price"
        params = {"symbol": symbol}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data['price'])
                else:
                    print(f"❌ Erro ao obter preço {symbol}: {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Erro na requisição de preço {symbol}: {e}")
            return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Obtém preços de múltiplos símbolos simultaneamente"""
        tasks = [self.get_price(symbol) for symbol in symbols]
        prices = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for symbol, price in zip(symbols, prices):
            if isinstance(price, Exception):
                print(f"❌ Erro ao obter preço de {symbol}: {price}")
                continue
            if price is not None:
                result[symbol] = price
        
        return result
    
    async def get_klines(self, symbol: str, interval: str = "1m", 
                        limit: int = 100) -> Optional[List[Dict]]:
        """Obtém dados de candlestick"""
        await self._rate_limit_check()
        
        url = f"{self.base_url}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Converte para formato mais amigável
                    klines = []
                    for kline in data:
                        klines.append({
                            'timestamp': datetime.fromtimestamp(kline[0] / 1000),
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5])
                        })
                    
                    return klines
                else:
                    print(f"❌ Erro ao obter klines {symbol}: {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Erro na requisição de klines {symbol}: {e}")
            return None
    
    async def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """Obtém estatísticas de 24h"""
        await self._rate_limit_check()
        
        url = f"{self.base_url}/api/v3/ticker/24hr"
        params = {"symbol": symbol}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'symbol': data['symbol'],
                        'price_change': float(data['priceChange']),
                        'price_change_percent': float(data['priceChangePercent']),
                        'high_price': float(data['highPrice']),
                        'low_price': float(data['lowPrice']),
                        'volume': float(data['volume']),
                        'count': int(data['count'])
                    }
                else:
                    print(f"❌ Erro ao obter ticker 24h {symbol}: {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Erro na requisição de ticker 24h {symbol}: {e}")
            return None
    
    async def get_multiple_timeframe_data(self, symbol: str, 
                                        timeframes: List[str]) -> Dict[str, List[Dict]]:
        """Obtém dados de múltiplos timeframes simultaneamente"""
        tasks = [self.get_klines(symbol, tf, 100) for tf in timeframes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for timeframe, result in zip(timeframes, results):
            if isinstance(result, Exception):
                print(f"❌ Erro ao obter dados {timeframe} de {symbol}: {result}")
                continue
            if result is not None:
                data[timeframe] = result
        
        return data

# Exemplo de uso
async def main():
    """Exemplo de uso do AsyncAPIHandler"""
    symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
    timeframes = ["1m", "5m", "15m", "1h"]
    
    async with AsyncAPIHandler() as api:
        # Preços atuais
        print("📊 Obtendo preços atuais...")
        prices = await api.get_multiple_prices(symbols)
        for symbol, price in prices.items():
            print(f"   {symbol}: ${price:.4f}")
        
        # Dados multi-timeframe para BTC
        print("\n📈 Obtendo dados multi-timeframe para BTCUSDT...")
        btc_data = await api.get_multiple_timeframe_data("BTCUSDT", timeframes)
        for tf, data in btc_data.items():
            if data:
                latest = data[-1]
                print(f"   {tf}: ${latest['close']:.4f} (Vol: {latest['volume']:.0f})")

if __name__ == "__main__":
    asyncio.run(main())

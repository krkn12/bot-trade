import requests
import time
from datetime import datetime, timedelta

def get_price(symbol="BTCUSDT"):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return float(response.json()["price"])
    except Exception as e:
        print(f"[ERRO] Binance API: {e}")
        return None

def get_24h_ticker(symbol="BTCUSDT"):
    """Obtém estatísticas de 24h incluindo volume, variação de preço, etc."""
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return {
            'volume': float(data['volume']),           # Volume em BTC
            'quoteVolume': float(data['quoteVolume']), # Volume em USDT
            'priceChange': float(data['priceChange']),
            'priceChangePercent': float(data['priceChangePercent']),
            'highPrice': float(data['highPrice']),
            'lowPrice': float(data['lowPrice']),
            'openPrice': float(data['openPrice']),
            'lastPrice': float(data['lastPrice']),
            'count': int(data['count'])  # Número de trades
        }
    except Exception as e:
        print(f"[ERRO] Binance API 24h ticker: {e}")
        return None

def get_daily_candles(symbol="BTCUSDT", limit=30):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERRO] Binance API candles diários: {e}")
        return None
        
def get_exchange_info():
    """Obtém informações sobre todos os pares de negociação disponíveis na Binance"""
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERRO] Binance API exchange info: {e}")
        return None

def get_all_symbols(quote_asset="USDT"):
    """Retorna todos os símbolos disponíveis para negociação com a moeda base especificada"""
    exchange_info = get_exchange_info()
    if not exchange_info:
        return []
    
    symbols = []
    for symbol_info in exchange_info.get("symbols", []):
        if symbol_info.get("status") == "TRADING" and symbol_info.get("quoteAsset") == quote_asset:
            symbols.append(symbol_info.get("symbol"))
    
    return symbols

def get_new_listings(days=7, quote_asset="USDT"):
    """Identifica novas listagens na Binance nos últimos X dias"""
    all_symbols = get_all_symbols(quote_asset)
    new_listings = []
    
    for symbol in all_symbols:
        # Verificar primeiro candle disponível para determinar quando foi listado
        candles = get_daily_candles(symbol, limit=1)
        if not candles or len(candles) == 0:
            continue
        
        # O timestamp do primeiro candle está na posição 0
        listing_time = datetime.fromtimestamp(candles[0][0] / 1000)  # Converter de milissegundos para segundos
        days_since_listing = (datetime.now() - listing_time).days
        
        if days_since_listing <= days:
            # Obter dados adicionais para análise
            ticker_24h = get_24h_ticker(symbol)
            if ticker_24h:
                new_listings.append({
                    "symbol": symbol,
                    "listing_date": listing_time,
                    "days_since_listing": days_since_listing,
                    "volume_24h": ticker_24h["quoteVolume"],
                    "price_change_24h": ticker_24h["priceChangePercent"],
                    "current_price": ticker_24h["lastPrice"]
                })
    
    # Ordenar por data de listagem (mais recentes primeiro)
    return sorted(new_listings, key=lambda x: x["days_since_listing"])

def analyze_potential(symbols, volume_min=1000000, volatility_min=5.0):
    """Analisa o potencial de lucro de uma lista de símbolos com base em volume e volatilidade"""
    high_potential = []
    
    for symbol in symbols:
        # Obter dados de 24h
        ticker_24h = get_24h_ticker(symbol)
        if not ticker_24h:
            continue
            
        # Obter candles para calcular volatilidade
        candles = get_daily_candles(symbol, limit=7)  # Últimos 7 dias
        if not candles or len(candles) < 3:  # Precisamos de pelo menos 3 dias para análise
            continue
            
        # Calcular volatilidade (desvio padrão dos movimentos percentuais diários)
        daily_changes = []
        for i in range(1, len(candles)):
            prev_close = float(candles[i-1][4])  # Close price do dia anterior
            curr_close = float(candles[i][4])    # Close price do dia atual
            daily_change = ((curr_close - prev_close) / prev_close) * 100
            daily_changes.append(daily_change)
            
        if not daily_changes:
            continue
            
        # Calcular volatilidade como desvio padrão
        import numpy as np
        volatility = np.std(daily_changes)
        
        # Verificar critérios de potencial
        volume_24h = ticker_24h["quoteVolume"]
        if volume_24h >= volume_min and volatility >= volatility_min:
            high_potential.append({
                "symbol": symbol,
                "volume_24h": volume_24h,
                "volatility": volatility,
                "price_change_24h": ticker_24h["priceChangePercent"],
                "current_price": ticker_24h["lastPrice"]
            })
    
    # Ordenar por volatilidade (maior primeiro)
    return sorted(high_potential, key=lambda x: x["volatility"], reverse=True)

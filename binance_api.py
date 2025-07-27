import requests

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

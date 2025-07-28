import requests
import time
import json
from datetime import datetime, timedelta
import logging

# Configurações da API corrigida
API_BASE_URL = "https://api.binance.com"
API_TESTNET_URL = "https://testnet.binance.vision"
TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIError(Exception):
    """Custom exception for API errors"""
    def __init__(self, message, status_code=None, error_code=None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

def make_request_with_retry(url, params=None, max_retries=MAX_RETRIES):
    """Faz requisição com retry automático e tratamento de erro melhorado"""
    for attempt in range(max_retries):
        try:
            logger.debug(f"Tentativa {attempt + 1}/{max_retries} para {url}")
            response = requests.get(url, params=params, timeout=TIMEOUT)
            
            # Tratamento específico de códigos de erro
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit exceeded
                retry_after = int(response.headers.get('Retry-After', RETRY_DELAY))
                logger.warning(f"Rate limit atingido. Aguardando {retry_after}s...")
                time.sleep(retry_after)
                continue
            elif response.status_code == 451:
                # Unavailable for legal reasons
                logger.error("API bloqueada por questões legais/geográficas (451)")
                return None
            elif response.status_code >= 500:
                # Server errors - retry
                logger.warning(f"Erro do servidor ({response.status_code}). Tentando novamente...")
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            else:
                # Client errors - don't retry
                logger.error(f"Erro da API: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout na tentativa {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
                continue
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Erro de conexão na tentativa {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            break
    
    logger.error(f"Falha após {max_retries} tentativas")
    return None

def get_price(symbol="BTCUSDT", use_testnet=False):
    """Obtém preço atual com tratamento de erro melhorado"""
    base_url = API_TESTNET_URL if use_testnet else API_BASE_URL
    url = f"{base_url}/api/v3/ticker/price"
    params = {"symbol": symbol}
    
    try:
        data = make_request_with_retry(url, params)
        if data and 'price' in data:
            return float(data["price"])
        else:
            logger.warning(f"Preço não encontrado para {symbol}")
            return None
    except Exception as e:
        logger.error(f"Erro ao obter preço de {symbol}: {e}")
        return None

def get_24h_ticker(symbol="BTCUSDT", use_testnet=False):
    """Obtém estatísticas de 24h com tratamento de erro melhorado"""
    base_url = API_TESTNET_URL if use_testnet else API_BASE_URL
    url = f"{base_url}/api/v3/ticker/24hr"
    params = {"symbol": symbol}
    
    try:
        data = make_request_with_retry(url, params)
        if data:
            return {
                'volume': float(data.get('volume', 0)),
                'quoteVolume': float(data.get('quoteVolume', 0)),
                'priceChange': float(data.get('priceChange', 0)),
                'priceChangePercent': float(data.get('priceChangePercent', 0)),
                'highPrice': float(data.get('highPrice', 0)),
                'lowPrice': float(data.get('lowPrice', 0)),
                'openPrice': float(data.get('openPrice', 0)),
                'lastPrice': float(data.get('lastPrice', 0)),
                'count': int(data.get('count', 0))
            }
        else:
            logger.warning(f"Dados 24h não encontrados para {symbol}")
            return None
    except Exception as e:
        logger.error(f"Erro ao obter ticker 24h de {symbol}: {e}")
        return None

def get_daily_candles(symbol="BTCUSDT", limit=30, use_testnet=False):
    """Obtém candles diários com tratamento de erro melhorado"""
    base_url = API_TESTNET_URL if use_testnet else API_BASE_URL
    url = f"{base_url}/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": "1d",
        "limit": limit
    }
    
    try:
        data = make_request_with_retry(url, params)
        if data:
            return data
        else:
            logger.warning(f"Candles não encontrados para {symbol}")
            return None
    except Exception as e:
        logger.error(f"Erro ao obter candles de {symbol}: {e}")
        return None

def get_exchange_info(use_testnet=False):
    """Obtém informações sobre todos os pares de negociação"""
    base_url = API_TESTNET_URL if use_testnet else API_BASE_URL
    url = f"{base_url}/api/v3/exchangeInfo"
    
    try:
        data = make_request_with_retry(url)
        if data:
            return data
        else:
            logger.warning("Informações de exchange não encontradas")
            return None
    except Exception as e:
        logger.error(f"Erro ao obter informações de exchange: {e}")
        return None

def get_all_symbols(quote_asset="USDT", use_testnet=False):
    """Obtém todos os símbolos disponíveis para uma moeda base"""
    try:
        exchange_info = get_exchange_info(use_testnet)
        if not exchange_info:
            return []
        
        symbols = []
        for symbol_info in exchange_info.get('symbols', []):
            if (symbol_info['quoteAsset'] == quote_asset and 
                symbol_info['status'] == 'TRADING'):
                symbols.append(symbol_info['symbol'])
        
        return symbols
    except Exception as e:
        logger.error(f"Erro ao obter símbolos: {e}")
        return []

def get_new_listings(days=7, quote_asset="USDT", use_testnet=False):
    """Obtém moedas listadas recentemente (simulado)"""
    try:
        # Como a API da Binance não tem endpoint específico para new listings,
        # vamos simular com algumas moedas conhecidas
        all_symbols = get_all_symbols(quote_asset, use_testnet)
        
        # Retorna uma amostra pequena para evitar problemas
        if all_symbols:
            return all_symbols[:10]  # Primeiros 10 símbolos
        else:
            # Fallback com símbolos conhecidos
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    except Exception as e:
        logger.error(f"Erro ao obter new listings: {e}")
        return ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

def analyze_potential(symbol, use_testnet=False):
    """Analisa o potencial de uma moeda"""
    try:
        ticker_data = get_24h_ticker(symbol, use_testnet)
        if not ticker_data:
            return None
        
        # Análise simples baseada em volume e volatilidade
        volume = ticker_data.get('quoteVolume', 0)
        price_change_percent = abs(ticker_data.get('priceChangePercent', 0))
        
        score = 0
        if volume > 1000000:  # Volume > 1M USDT
            score += 30
        if price_change_percent > 5:  # Volatilidade > 5%
            score += 40
        if ticker_data.get('count', 0) > 1000:  # Muitas transações
            score += 30
        
        return {
            'symbol': symbol,
            'score': score,
            'volume': volume,
            'volatility': price_change_percent,
            'trades_count': ticker_data.get('count', 0)
        }
    except Exception as e:
        logger.error(f"Erro ao analisar potencial de {symbol}: {e}")
        return None

def test_api_connection(use_testnet=False):
    """Testa a conexão com a API"""
    try:
        base_url = API_TESTNET_URL if use_testnet else API_BASE_URL
        url = f"{base_url}/api/v3/ping"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Conexão com API Binance OK")
            return True
        else:
            logger.error(f"❌ Falha na conexão com API: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao testar conexão: {e}")
        return False

# Função para obter dados mock quando API falha
def get_mock_data(symbol="BTCUSDT"):
    """Retorna dados simulados quando a API falha"""
    import random
    
    base_price = 50000 if symbol == "BTCUSDT" else 3000  # Preços base
    price = base_price + random.uniform(-1000, 1000)
    
    return {
        'price': price,
        'ticker_24h': {
            'volume': random.uniform(10000, 100000),
            'quoteVolume': random.uniform(1000000, 10000000),
            'priceChange': random.uniform(-500, 500),
            'priceChangePercent': random.uniform(-5, 5),
            'highPrice': price + random.uniform(0, 500),
            'lowPrice': price - random.uniform(0, 500),
            'openPrice': price + random.uniform(-200, 200),
            'lastPrice': price,
            'count': random.randint(1000, 10000)
        }
    }

if __name__ == "__main__":
    # Teste da API
    print("🧪 Testando API corrigida...")
    test_api_connection()
    
    # Teste de preço
    price = get_price("BTCUSDT")
    print(f"Preço BTC: {price}")
    
    if price is None:
        print("⚠️ Usando dados mock devido a falha na API")
        mock_data = get_mock_data("BTCUSDT")
        print(f"Mock Price: {mock_data['price']}")
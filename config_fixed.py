# Configurações Corrigidas do Trading Bot
# Relação risco/retorno desejada (ex: 2 = TP é 2x maior que SL)
RELACAO_RISCO_RETORNO = 2.0

# Ativa/desativa modo simulação (paper trading)
MODO_SIMULACAO = True  # True = não executa ordens reais

# 💰 CONFIGURAÇÃO AUTOMÁTICA BASEADA NO CAPITAL
CAPITAL_INICIAL = 100.00     # Seu capital inicial
RISCO_POR_TRADE = 0.02      # 2% de risco por operação
META_LUCRO_DIARIO = 0.10 * CAPITAL_INICIAL    # 10% de lucro diário

VARIACAO_ALVO = 0.003       # 0.3% variação (mais sensível)
INTERVALO = 10              # 10 segundos (reduzir stress na API)
PAR = "BTCUSDT"
VALOR_POR_OPERACAO = CAPITAL_INICIAL * 0.8  # 80% do capital por trade
ARQUIVO_LOG = "trading_log.csv"
SMA_PERIODOS = 10

# Configurações de alerta para capital pequeno
VARIACAO_MIN_ALERTA = 0.02 * CAPITAL_INICIAL   # 2% do capital
VARIACAO_MAX_ALERTA = 0.05 * CAPITAL_INICIAL   # 5% do capital

# Gestão de risco ajustada para o capital
STOP_LOSS_PCT = 0.02        # 2% stop loss (compensa taxas)
TAKE_PROFIT_PCT = 0.05      # 5% take profit (lucro real após taxas)
MAX_TRADES_DIA = 3          # Máximo 3 trades por dia (menos taxas)
TAXA_BINANCE = 0.002        # 0.2% taxa total por trade completo

# 🧠 Configurações de Machine Learning
USAR_ML = False             # Desabilitado temporariamente para debug
ML_CONFIANCA_MIN = 0.65     # Confiança mínima para considerar sinais ML (65%)
ML_TREINO_INTERVALO = 3600  # Intervalo para retreinar modelos (em segundos)
ML_MODELOS_DIR = "ml_models" # Diretório para salvar modelos treinados
ML_FEATURES = [             # Features para usar no treinamento
    "rsi", "macd", "ema_diff", "bollinger", "volume_change", 
    "price_change", "volatility", "trend_strength"
]
ML_TIMEFRAMES = [           # Timeframes para análise multi-timeframe
    "1m", "5m", "15m", "1h", "4h"
]
ML_JANELA_PREVISAO = 12     # Janela de previsão (em períodos)

# 🔄 Configurações do Seletor Automático de Moedas (DESABILITADO para debug)
USAR_SELECAO_AUTOMATICA = False  # Desabilitado temporariamente
SELECAO_INTERVALO = 3600 * 6    # Intervalo para buscar novas moedas (6 horas)
SELECAO_MAX_MOEDAS = 3          # Reduzido para 3 moedas
SELECAO_DIAS_NOVAS = 14         # Considerar moedas listadas nos últimos X dias
SELECAO_VOLUME_MIN = 1000000    # Volume mínimo em USDT (1 milhão)
SELECAO_VOLATILIDADE_MIN = 5.0  # Volatilidade mínima (5%)
MOEDA_BASE = "USDT"            # Moeda base para negociação

# 🌐 Configurações de API (NOVAS)
API_BASE_URL = "https://api.binance.com"
API_TESTNET_URL = "https://testnet.binance.vision"  # Para testes
USE_TESTNET = False         # Se True, usa testnet da Binance
API_TIMEOUT = 30            # Timeout em segundos
API_RETRY_ATTEMPTS = 3      # Tentativas de retry
API_RETRY_DELAY = 5         # Delay entre tentativas (segundos)

# 🔒 Rate Limiting (NOVOS)
RATE_LIMIT_REQUESTS_PER_MINUTE = 1200  # Limite da Binance
RATE_LIMIT_WEIGHT_PER_MINUTE = 6000    # Peso das requisições
ENABLE_RATE_LIMITING = True            # Habilitar controle de rate limit

# 🛡️ Configurações de Segurança e Error Handling (NOVAS)
MAX_CONSECUTIVE_ERRORS = 10  # Máximo de erros consecutivos antes de parar
ERROR_COOLDOWN_TIME = 60     # Tempo de espera após muitos erros (segundos)
ENABLE_DETAILED_LOGGING = True  # Log detalhado para debug
LOG_LEVEL = "INFO"          # DEBUG, INFO, WARNING, ERROR

# 📊 Configurações de Fallback (NOVAS)
USE_MOCK_DATA = False       # Se True, usa dados simulados quando API falha
FALLBACK_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]  # Pares de fallback
ENABLE_OFFLINE_MODE = False # Modo offline para desenvolvimento
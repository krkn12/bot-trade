# Relação risco/retorno desejada (ex: 2 = TP é 2x maior que SL)
RELACAO_RISCO_RETORNO = 2.0
# Ativa/desativa modo simulação (paper trading)
MODO_SIMULACAO = True  # True = não executa ordens reais
# 💰 CONFIGURAÇÃO AUTOMÁTICA BASEADA NO CAPITAL
CAPITAL_INICIAL = 100.00     # Seu capital inicial
RISCO_POR_TRADE = 0.02      # 2% de risco por operação
META_LUCRO_DIARIO = 0.10 * CAPITAL_INICIAL    # 10% de lucro diário

VARIACAO_ALVO = 0.003       # 0.3% variação (mais sensível)
INTERVALO = 3               # 3 segundos (ajuste para capital pequeno)
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

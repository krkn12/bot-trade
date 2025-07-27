# Estratégias de trading (ex: RSI, MACD, Bollinger, etc.)

def calcular_rsi(precos, periodo=14):
    """Calcula o RSI (Relative Strength Index)"""
    if len(precos) < periodo + 1:
        return None
    deltas = [precos[i] - precos[i-1] for i in range(1, len(precos))]
    ganhos = [delta if delta > 0 else 0 for delta in deltas]
    perdas = [-delta if delta < 0 else 0 for delta in deltas]
    if len(ganhos) < periodo:
        return None
    media_ganhos = sum(ganhos[-periodo:]) / periodo
    media_perdas = sum(perdas[-periodo:]) / periodo
    if media_perdas == 0:
        return 100
    rs = media_ganhos / media_perdas
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calcular_macd(precos, rapida=12, lenta=26, sinal=9):
    """Calcula MACD (Moving Average Convergence Divergence)"""
    if len(precos) < lenta:
        return None
    ema_rapida = calcular_ema(precos, rapida)
    ema_lenta = calcular_ema(precos, lenta)
    if ema_rapida is None or ema_lenta is None:
        return None
    macd_line = ema_rapida - ema_lenta
    return macd_line

def calcular_ema(precos, periodo):
    """Calcula EMA (Exponential Moving Average)"""
    if len(precos) < periodo:
        return None
    k = 2 / (periodo + 1)
    ema = precos[0]
    for preco in precos[1:]:
        ema = (preco * k) + (ema * (1 - k))
    return ema

def calcular_medias_moveis(candles):
    """Retorna dicionário com MA7, MA25 e MA99 calculadas com preços de fechamento"""
    if not candles or len(candles) < 7:
        return None
    fechamentos = [float(candle[4]) for candle in candles]
    def media_movel(periodo):
        if len(fechamentos) < periodo:
            return None
        return sum(fechamentos[-periodo:]) / periodo
    return {
        "MA7": media_movel(7),
        "MA25": media_movel(25),
        "MA99": media_movel(99)
    }
# Estratégias de trading (ex: RSI, MACD, Bollinger, etc.)

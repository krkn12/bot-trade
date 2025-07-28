# core/estrategias.py

def calcular_ema(precos, periodo):
    """Calcula EMA (Exponential Moving Average) de forma eficiente."""
    if len(precos) < periodo:
        return None
    k = 2 / (periodo + 1)
    ema = precos[0]
    for preco in precos[1:]:
        ema = (preco * k) + (ema * (1 - k))
    return ema

def calcular_rsi(precos, periodo=14):
    """Calcula o RSI (Relative Strength Index)."""
    if len(precos) < periodo + 1:
        return None
    deltas = [precos[i] - precos[i-1] for i in range(1, len(precos))]
    ganhos = [delta if delta > 0 else 0 for delta in deltas]
    perdas = [-delta if delta < 0 else 0 for delta in deltas]
    media_ganhos = sum(ganhos[-periodo:]) / periodo
    media_perdas = sum(perdas[-periodo:]) / periodo
    if media_perdas == 0:
        return 100
    rs = media_ganhos / media_perdas
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calcular_macd(precos, rapida=12, lenta=26):
    """Calcula MACD (Moving Average Convergence Divergence)."""
    if len(precos) < lenta:
        return None
    ema_rapida = calcular_ema(precos, rapida)
    ema_lenta = calcular_ema(precos, lenta)
    if ema_rapida is None or ema_lenta is None:
        return None
    macd_line = ema_rapida - ema_lenta
    return macd_line

def calcular_medias_moveis(candles):
    """Retorna dicionário com MA7, MA25 e MA99 calculadas com preços de fechamento"""
    # Verifica se candles existe e é uma lista
    if not candles or not isinstance(candles, list):
        print(f"Erro: Dados de candles inválidos ou vazios: {candles}")
        return None
    
    # Verifica se há candles suficientes
    if len(candles) < 7:
        print(f"Erro: Poucos candles recebidos ({len(candles)}/7 necessários)")
        return None
    
    try:
        # Filtra apenas candles com 5 ou mais itens e que sejam listas/tuplas
        validos = [candle for candle in candles if isinstance(candle, (list, tuple)) and len(candle) >= 5]
        if not validos:
            print("Erro: Nenhum candle válido encontrado (falta preço de fechamento)")
            return None
        
        # Extrai preços de fechamento (posição 4)
        fechamentos = [float(candle[4]) for candle in validos]
        if len(fechamentos) < 7:
            print(f"Erro: Poucos preços de fechamento válidos ({len(fechamentos)}/7 necessários)")
            return None
        
        # Calcula as médias móveis
        def media_movel(periodo):
            if len(fechamentos) < periodo:
                return None
            return sum(fechamentos[-periodo:]) / periodo
        
        return {
            "MA7": media_movel(7),
            "MA25": media_movel(25),
            "MA99": media_movel(99)
        }
    except Exception as e:
        print(f"Erro ao calcular médias móveis: {e}")
        return None

def calcular_indicadores(candles):
    """
    Calcula indicadores principais e retorna num dicionário.
    """
    fechamentos = []
    for candle in candles:
        try:
            fechamento = float(candle[4])
            fechamentos.append(fechamento)
        except (IndexError, ValueError, TypeError):
            continue

    if len(fechamentos) == 0:
        return None

    rsi = calcular_rsi(fechamentos)
    macd = calcular_macd(fechamentos)
    medias = calcular_medias_moveis(candles) or {}

    return {
        "rsi": rsi,
        "macd": macd,
        **medias
    }

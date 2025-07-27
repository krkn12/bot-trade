
from config import VARIACAO_ALVO
from core.estrategias import calcular_rsi, calcular_macd, calcular_ema, calcular_medias_moveis

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
    
    # EMA rápida e lenta
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

def analisar_basico(preco_atual, precos_historicos, medias, dados_24h):
    """Análise direta para compra/venda com alertas de variação"""
    preco_anterior = precos_historicos[-2] if len(precos_historicos) > 1 else preco_atual
    variacao_absoluta = abs(preco_atual - preco_anterior)
    variacao_pct = (preco_atual - preco_anterior) / preco_anterior * 100
    
    # Verificar se houve variação significativa ($5-10)
    alerta_variacao = ""
    if 5 <= variacao_absoluta <= 10:
        if preco_atual > preco_anterior:
            alerta_variacao = f"SUBIU ${variacao_absoluta:.2f}!"
        else:
            alerta_variacao = f"CAIU ${variacao_absoluta:.2f}!"
    elif variacao_absoluta > 10:
        if preco_atual > preco_anterior:
            alerta_variacao = f"SUBIDA FORTE ${variacao_absoluta:.2f}!"
        else:
            alerta_variacao = f"QUEDA FORTE ${variacao_absoluta:.2f}!"
    
    # Análise simplificada e direta
    if medias:
        # Condições de COMPRA (Preço Ideal)
        if (preco_atual > medias['MA99'] and  # Tendência de longo prazo positiva
            preco_atual < medias['MA7'] and   # Preço abaixo da média de curto prazo (oportunidade)
            variacao_pct < -1):               # Pequena correção
            
            stop_loss = preco_atual * 0.97   # 3% de stop loss
            take_profit = preco_atual * 1.05  # 5% de take profit
            motivo = "PREÇO IDEAL PARA COMPRA! Tendência de alta + correção temporária"
            
            if alerta_variacao:
                motivo += f" | {alerta_variacao}"
                
            return "COMPRA", motivo, stop_loss, take_profit
        
        # Condições de VENDA (Preço Ideal)
        elif (preco_atual > medias['MA7'] > medias['MA25'] and  # Tendência de alta confirmada
              variacao_pct > 2):                                # Alta significativa
            
            motivo = "PREÇO IDEAL PARA VENDA! Tendência de alta + valorização"
            
            if alerta_variacao:
                motivo += f" | {alerta_variacao}"
                
            return "VENDA", motivo, None, None
        
        # COMPRA em queda forte com volume
        elif (dados_24h and 
              dados_24h['priceChangePercent'] < -3 and
              dados_24h['quoteVolume'] > 1000000000 and
              preco_atual > medias['MA99']):
            
            stop_loss = preco_atual * 0.96
            take_profit = preco_atual * 1.08
            motivo = "OPORTUNIDADE DE COMPRA! Queda com volume alto em tendência de alta"
            
            if alerta_variacao:
                motivo += f" | {alerta_variacao}"
                
            return "COMPRA", motivo, stop_loss, take_profit
    
    # Se não há sinal claro, mas há variação significativa
    if alerta_variacao:
        return "ALERTA", f"Variação importante: {alerta_variacao}", None, None
    
    # Mercado estável
    return "AGUARDAR", "Aguardando preço ideal para entrada ou saída", None, None

def analisar_entrada_saida(preco_atual, precos_historicos, medias, dados_24h):
    """Análise avançada para pontos de entrada e saída"""
    dados_coletados = len(precos_historicos)
    
    if dados_coletados < 5:
        return "COLETANDO", f"Coletando dados... ({dados_coletados}/20 necessários)", None, None
    
    # Análise básica com poucos dados
    if dados_coletados < 20:
        return analisar_basico(preco_atual, precos_historicos, medias, dados_24h)
    
    # Calcular indicadores
    rsi = calcular_rsi(precos_historicos)
    macd = calcular_macd(precos_historicos)
    
    # Preços para cálculos
    preco_anterior = precos_historicos[-2] if len(precos_historicos) > 1 else preco_atual
    variacao = (preco_atual - preco_anterior) / preco_anterior * 100
    
    # Volume analysis
    volume_medio = dados_24h['quoteVolume'] / dados_24h['count'] if dados_24h else 0
    volume_alto = dados_24h and dados_24h['quoteVolume'] > 1000000000  # > 1B USDT
    
    # Condições de COMPRA (Entrada)
    condicoes_compra = []
    if rsi and rsi < 30:  # RSI oversold
        condicoes_compra.append("RSI sobrevenda (< 30)")
    
    if medias and preco_atual > medias['MA7'] > medias['MA25']:  # Tendência de alta
        condicoes_compra.append("Tendência de alta (MA7 > MA25)")
    
    if macd and macd > 0:  # MACD positivo
        condicoes_compra.append("MACD positivo")
    
    if variacao < -2 and volume_alto:  # Queda com volume
        condicoes_compra.append("Queda com volume alto")
    
    # Condições de VENDA (Saída)
    condicoes_venda = []
    if rsi and rsi > 70:  # RSI overbought
        condicoes_venda.append("RSI sobrecompra (> 70)")
    
    if medias and preco_atual < medias['MA7'] < medias['MA25']:  # Tendência de baixa
        condicoes_venda.append("Tendência de baixa (MA7 < MA25)")
    
    if macd and macd < 0:  # MACD negativo
        condicoes_venda.append("MACD negativo")
    
    if variacao > 3 and volume_alto:  # Alta com volume
        condicoes_venda.append("Alta com volume alto")
    
    # Calcular Stop Loss e Take Profit
    stop_loss = preco_atual * 0.98  # 2% abaixo do preço atual
    take_profit = preco_atual * 1.06  # 6% acima do preço atual
    
    # Decisão final
    if len(condicoes_compra) >= 2:
        return "COMPRA", "; ".join(condicoes_compra), stop_loss, take_profit
    elif len(condicoes_venda) >= 2:
        return "VENDA", "; ".join(condicoes_venda), None, None
    else:
        return "AGUARDAR", "Condições insuficientes", None, None

def analisar_mercado(preco_atual, preco_anterior):
    """Função original mantida para compatibilidade"""
    variacao = (preco_atual - preco_anterior) / preco_anterior

    if variacao >= VARIACAO_ALVO:
        return "venda", variacao
    elif variacao <= -VARIACAO_ALVO:
        return "compra", variacao
    else:
        return "neutro", variacao


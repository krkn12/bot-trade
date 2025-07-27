# Gestão de risco (tamanho de posição, stop, etc.)

def calcular_tamanho_posicao(capital_atual, preco_entrada, stop_loss, risco_por_trade=0.02):
    """Calcula tamanho ideal da posição baseado no risco"""
    if stop_loss is None:
        return capital_atual * 0.8  # 80% do capital
    risco_por_btc = abs(preco_entrada - stop_loss)
    risco_total_permitido = capital_atual * risco_por_trade
    quantidade_btc = risco_total_permitido / risco_por_btc
    valor_operacao = quantidade_btc * preco_entrada
    valor_maximo = capital_atual * 0.9
    return min(valor_operacao, valor_maximo)
# Gestão de risco (tamanho de posição, stop, etc.)

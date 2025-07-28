# Execução de ordens (compra, venda, simulação, etc.)

from config import MAX_TRADES_DIA, TAXA_BINANCE, STOP_LOSS_PCT, RELACAO_RISCO_RETORNO, MODO_SIMULACAO, CAPITAL_INICIAL

def executar_compra(bot, preco_atual):
    """Executa ordem de compra (real ou simulação) com taxa e slippage"""
    if bot.posicao_aberta or bot.trades_hoje >= MAX_TRADES_DIA:
        return False

    valor_bruto = bot.capital * 0.8

    if bot.capital < 2.0:
        print(f"\n⚠️ SALDO INSUFICIENTE: ${bot.capital:.2f} (mínimo $2.00)")
        return False
    if valor_bruto < 1.0:
        print(f"\n⚠️ VALOR DE TRADE MUITO BAIXO: ${valor_bruto:.2f} (mínimo $1.00)")
        return False

    preco_ajustado = preco_atual * (1 + bot.slippage)
    taxa_compra = valor_bruto * TAXA_BINANCE / 2
    valor_liquido = valor_bruto - taxa_compra

    if MODO_SIMULACAO:
        print("\n🟡 [SIMULAÇÃO] ORDEM DE COMPRA SIMULADA")
    else:
        print("\n🟢 ═══ ORDEM DE COMPRA EXECUTADA ═══")

    bot.quantidade_btc = valor_liquido / preco_ajustado
    bot.preco_entrada = preco_ajustado
    bot.posicao_aberta = 'LONG'
    bot.trades_hoje += 1
    bot.capital -= valor_bruto

    take_profit_pct = STOP_LOSS_PCT * RELACAO_RISCO_RETORNO
    take_profit = preco_ajustado * (1 + take_profit_pct)
    stop_loss = preco_ajustado * (1 - STOP_LOSS_PCT)

    print(f"💰 Preço (com slippage): ${preco_ajustado:.2f}")
    print(f"💵 Valor Bruto: ${valor_bruto:.2f}")
    print(f"💸 Taxa Binance: -${taxa_compra:.2f} (0.1%)")
    print(f"💰 Valor Líquido: ${valor_liquido:.2f}")
    print(f"₿ Quantidade: {bot.quantidade_btc:.6f} BTC")
    print(f"💰 Capital Restante: ${bot.capital:.2f}")
    print(f"🛑 Stop Loss: ${stop_loss:.2f} (-{STOP_LOSS_PCT*100:.1f}%)")
    print(f"🎯 Take Profit: ${take_profit:.2f} (+{take_profit_pct*100:.1f}%)")
    print(f"📊 Relação Risco/Retorno: {RELACAO_RISCO_RETORNO:.2f}x")
    print(f"⚙️ Slippage: {bot.slippage*100:.2f}% | Taxa total: {TAXA_BINANCE*100:.2f}%")

    bot.log_manager.registrar_trade(
        "COMPRA_SIMULADA" if MODO_SIMULACAO else "COMPRA",
        preco_ajustado, valor_bruto, bot.capital + valor_bruto,
        bot.lucro_hoje, (bot.lucro_hoje/CAPITAL_INICIAL)*100,
        f"SL: ${stop_loss:.2f} | TP: ${take_profit:.2f} | Risco/Retorno: {RELACAO_RISCO_RETORNO:.2f}x | Taxa: ${taxa_compra:.2f} | Slippage: {bot.slippage*100:.2f}% | Restante: ${bot.capital:.2f}"
    )

    bot.log_trades.append({
        'tipo': 'compra',
        'preco': preco_ajustado,
        'capital_antes': bot.capital + valor_bruto,
        'quantidade': bot.quantidade_btc,
        'taxa': taxa_compra,
        'slippage': bot.slippage
    })

    import winsound
    winsound.Beep(1000, 500)
    bot._salvar_estado()
    return True

def executar_venda(bot, preco_atual):
    """Executa ordem de venda (real ou simulação) com taxa e slippage"""
    if not bot.posicao_aberta or bot.posicao_aberta != 'LONG':
        return False

    preco_ajustado = preco_atual * (1 - bot.slippage)
    valor_atual = bot.quantidade_btc * preco_ajustado
    valor_investido = bot.quantidade_btc * bot.preco_entrada
    taxa_venda = valor_atual * TAXA_BINANCE / 2
    valor_liquido = valor_atual - taxa_venda
    lucro_bruto = valor_atual - valor_investido
    lucro_liquido = valor_liquido - (valor_investido - (valor_investido * TAXA_BINANCE / 2))

    if MODO_SIMULACAO:
        print("\n🟡 [SIMULAÇÃO] ORDEM DE VENDA SIMULADA")
    else:
        print("\n🔴 ═══ ORDEM DE VENDA EXECUTADA ═══")

    bot.capital += valor_liquido
    bot.lucro_hoje += lucro_liquido

    # Atualiza win rate
    if lucro_liquido > 0:
        bot.trades_ganhos += 1
    else:
        bot.trades_perdidos += 1

    print(f"💸 Preço de Venda (com slippage): ${preco_ajustado:.2f}")
    print(f"💸 Preço de Compra: ${bot.preco_entrada:.2f}")
    print(f"₿ Quantidade: {bot.quantidade_btc:.6f} BTC")
    print(f"💵 Valor Bruto: ${valor_atual:.2f}")
    print(f"💵 Valor Investido: ${valor_investido:.2f}")
    print(f"💸 Taxa Binance: -${taxa_venda:.2f} (0.1%)")
    print(f"💰 Valor Líquido: ${valor_liquido:.2f}")

    if lucro_liquido > 0:
        print(f"🟢 LUCRO LÍQUIDO: +${lucro_liquido:.2f} (+{(lucro_liquido/valor_investido)*100:.2f}%)")
    else:
        print(f"🔴 PERDA LÍQUIDA: ${lucro_liquido:.2f} ({(lucro_liquido/valor_investido)*100:.2f}%)")

    print(f"💰 Capital Total: ${bot.capital:.2f}")
    print(f"📈 Lucro do Dia: ${bot.lucro_hoje:.2f}")
    print(f"⚙️ Slippage: {bot.slippage*100:.2f}% | Taxa total: {TAXA_BINANCE*100:.2f}%")

    bot.log_manager.registrar_trade(
        "VENDA_SIMULADA" if MODO_SIMULACAO else "VENDA",
        preco_ajustado, valor_atual, bot.capital,
        bot.lucro_hoje, (bot.lucro_hoje/CAPITAL_INICIAL)*100,
        f"P&L: ${lucro_liquido:.2f} | Taxa: ${taxa_venda:.2f} | Slippage: {bot.slippage*100:.2f}% | Compra: ${bot.preco_entrada:.2f}"
    )

    bot.log_trades.append({
        'tipo': 'venda',
        'preco': preco_ajustado,
        'capital_depois': bot.capital,
        'lucro': lucro_liquido,
        'win': lucro_liquido > 0,
        'taxa': taxa_venda,
        'slippage': bot.slippage
    })

    bot.posicao_aberta = None
    bot.quantidade_btc = 0
    bot.preco_entrada = 0

    import winsound
    winsound.Beep(1500, 500)
    bot._salvar_estado()
    return True
# Execução de ordens (compra, venda, simulação, etc.)

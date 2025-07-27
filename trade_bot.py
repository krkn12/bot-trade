import time
import json
from datetime import datetime, timedelta
from binance_api import get_price, get_daily_candles, get_24h_ticker
from core.estrategias import calcular_rsi, calcular_macd, calcular_ema, calcular_medias_moveis
from core.execucao import executar_compra, executar_venda
from config import INTERVALO, PAR, CAPITAL_INICIAL, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_TRADES_DIA, MODO_SIMULACAO, RELACAO_RISCO_RETORNO, TAXA_BINANCE
from capital_log import CapitalLog

import winsound

import os

class TradingBot:
    STATE_FILE = "bot_state.json"

    def __init__(self, pares=None, estrategias=None):
        self.log_manager = CapitalLog()
        self.ultima_decisao = ""
        self.trades_ganhos = 0
        self.trades_perdidos = 0
        self.slippage = 0.0005  # 0.05% slippage padrão
        self.log_trades = []
        self.pares = pares if pares else [PAR]
        # Parâmetro adaptativo do RSI
        self.rsi_periodo = 14
        self._ajustar_rsi_periodo()
        # Dicionário: par -> função de estratégia
        self.estrategias = estrategias if estrategias else {par: self.analisar_mercado for par in self.pares}
        self.historico_precos = {par: [] for par in self.pares}
        self._carregar_estado()
        print("🟢 BOT TRADING PROFISSIONAL INICIADO")
        print(f"💰 Capital Inicial: ${self.capital:.2f}")
        print(f"🎯 Meta: {MAX_TRADES_DIA} trades/dia máx")
        print(f"📈 Pares monitorados: {', '.join(self.pares)}")
        print("═" * 50)

    def _ajustar_rsi_periodo(self):
        # Ajusta o período do RSI conforme o desempenho do dia anterior
        resumo = self.log_manager.get_resumo_hoje()
        lucro = resumo.get('lucro', 0)
        if lucro < 0:
            self.rsi_periodo = min(20, self.rsi_periodo + 2)  # Fica mais conservador
        elif lucro > 0:
            self.rsi_periodo = max(8, self.rsi_periodo - 2)   # Fica mais agressivo

    def _carregar_estado(self):
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r') as f:
                    state = json.load(f)
                self.capital = state.get('capital', CAPITAL_INICIAL)
                self.posicao_aberta = state.get('posicao_aberta', None)
                self.preco_entrada = state.get('preco_entrada', 0)
                self.quantidade_btc = state.get('quantidade_btc', 0)
                self.trades_hoje = state.get('trades_hoje', 0)
                self.lucro_hoje = state.get('lucro_hoje', 0.0)
            except Exception as e:
                print(f"⚠️ Erro ao carregar estado salvo: {e}")
                self.capital = CAPITAL_INICIAL
                self.posicao_aberta = None
                self.preco_entrada = 0
                self.quantidade_btc = 0
                self.trades_hoje = 0
                self.lucro_hoje = 0.0
        else:
            self.capital = CAPITAL_INICIAL
            self.posicao_aberta = None
            self.preco_entrada = 0
            self.quantidade_btc = 0
            self.trades_hoje = 0
            self.lucro_hoje = 0.0

    def _salvar_estado(self):
        state = {
            'capital': self.capital,
            'posicao_aberta': self.posicao_aberta,
            'preco_entrada': self.preco_entrada,
            'quantidade_btc': self.quantidade_btc,
            'trades_hoje': self.trades_hoje,
            'lucro_hoje': self.lucro_hoje
        }
        try:
            with open(self.STATE_FILE, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            print(f"⚠️ Erro ao salvar estado: {e}")
    
    def calcular_indicadores(self, precos):
        """Calcula todos os indicadores técnicos (RSI adaptativo)"""
        if len(precos) < 26:
            return None
        rsi = calcular_rsi(precos, self.rsi_periodo)
        macd = calcular_macd(precos)
        ema_12 = calcular_ema(precos, 12)
        ema_26 = calcular_ema(precos, 26)
        return {
            'rsi': rsi,
            'macd': macd,
            'ema_12': ema_12,
            'ema_26': ema_26,
            'tendencia': 'ALTA' if ema_12 > ema_26 else 'BAIXA',
            'rsi_periodo': self.rsi_periodo
        }
    
    def analisar_mercado(self, preco_atual, dados_24h, medias, par=None):
        """Análise profissional do mercado"""
        # Suporte para multiativo: usa histórico correto
        historico = self.historico_precos[par] if par else self.historico_precos[PAR]
        if len(historico) < 26:
            return "COLETANDO", f"Coletando dados... ({len(historico)}/26)"
        indicadores = self.calcular_indicadores(historico)
        if not indicadores:
            return "AGUARDAR", "Indicadores insuficientes"
        
        # Se já tem posição aberta, só analisa para venda
        if self.posicao_aberta:
            condicoes_venda = 0
            motivos_venda = []
            
            # MODO RECUPERAÇÃO: Se teve prejuízo, seja mais conservador na venda
            modo_recuperacao = self.lucro_hoje < -0.01
            limite_venda = 5 if modo_recuperacao else 4  # Mais difícil vender em recuperação
            
            if modo_recuperacao:
                motivos_venda.append("MODO RECUPERAÇÃO - Aguardando lucro maior")
            
            # RSI overbought (mais conservador em modo recuperação)
            if modo_recuperacao:
                if indicadores['rsi'] and indicadores['rsi'] > 80:
                    condicoes_venda += 3
                    motivos_venda.append(f"RSI extremo recuperação ({indicadores['rsi']:.1f})")
                elif indicadores['rsi'] and indicadores['rsi'] > 70:
                    condicoes_venda += 2
                    motivos_venda.append(f"RSI alto recuperação ({indicadores['rsi']:.1f})")
            else:
                if indicadores['rsi'] and indicadores['rsi'] > 75:
                    condicoes_venda += 3
                    motivos_venda.append(f"RSI muito overbought ({indicadores['rsi']:.1f})")
                elif indicadores['rsi'] and indicadores['rsi'] > 65:
                    condicoes_venda += 2
                    motivos_venda.append(f"RSI overbought ({indicadores['rsi']:.1f})")
            
            # MACD negativo
            if indicadores['macd'] and indicadores['macd'] < 0:
                condicoes_venda += 1
                motivos_venda.append("MACD negativo")
            
            # Tendência de baixa
            if indicadores['tendencia'] == 'BAIXA':
                condicoes_venda += 1
                motivos_venda.append("Tendência de baixa (EMA)")
            
            # Lucro significativo (compensa taxas)
            if dados_24h and dados_24h['priceChangePercent'] > 4:
                condicoes_venda += 2
                motivos_venda.append("Alta forte (+4%)")
            elif dados_24h and dados_24h['priceChangePercent'] > 2:
                condicoes_venda += 1
                motivos_venda.append("Alta moderada (+2%)")
            
            # Decisão para posição aberta (mais conservador em modo recuperação)
            if condicoes_venda >= limite_venda:
                return "VENDA", "; ".join(motivos_venda)
            else:
                status = "RECUPERAÇÃO" if modo_recuperacao else "NORMAL"
                return "MANTER", f"Mantendo {status} (V:{condicoes_venda}/{limite_venda})"
        
        # Se não tem posição, analisa para compra
        else:
            condicoes_compra = 0
            motivos_compra = []
            
            # ESTRATÉGIA ANTI-PERDA: Evitar taxas desnecessárias
            modo_recuperacao = self.lucro_hoje < -0.01
            primeiro_trade = self.trades_hoje == 0
            
            # Primeiro trade: MUITO SELETIVO para evitar perda
            if primeiro_trade:
                limite_condicoes = 5  # Muito rigoroso no primeiro
                motivos_compra.append("PRIMEIRO TRADE - MÁXIMA SELETIVIDADE")
            elif modo_recuperacao:
                limite_condicoes = 3  # Agressivo em recuperação
                motivos_compra.append("MODO RECUPERAÇÃO ATIVO")
                condicoes_compra += 1
            else:
                limite_condicoes = 4  # Normal
            
            # RSI oversold (MUITO rigoroso no primeiro trade)
            if primeiro_trade:
                # Primeiro trade: SÓ com RSI extremamente baixo
                if indicadores['rsi'] and indicadores['rsi'] < 20:
                    condicoes_compra += 3
                    motivos_compra.append(f"RSI EXTREMO primeiro trade ({indicadores['rsi']:.1f})")
                elif indicadores['rsi'] and indicadores['rsi'] < 25:
                    condicoes_compra += 2
                    motivos_compra.append(f"RSI muito baixo primeiro trade ({indicadores['rsi']:.1f})")
            elif modo_recuperacao:
                # Recuperação: Mais flexível
                if indicadores['rsi'] and indicadores['rsi'] < 35:
                    condicoes_compra += 2
                    motivos_compra.append(f"RSI oversold recuperação ({indicadores['rsi']:.1f})")
                elif indicadores['rsi'] and indicadores['rsi'] < 45:
                    condicoes_compra += 1
                    motivos_compra.append(f"RSI baixo recuperação ({indicadores['rsi']:.1f})")
            else:
                # Normal: Rigoroso
                if indicadores['rsi'] and indicadores['rsi'] < 25:
                    condicoes_compra += 3
                    motivos_compra.append(f"RSI muito oversold ({indicadores['rsi']:.1f})")
                elif indicadores['rsi'] and indicadores['rsi'] < 35:
                    condicoes_compra += 2
                    motivos_compra.append(f"RSI oversold ({indicadores['rsi']:.1f})")
            
            # MACD positivo
            if indicadores['macd'] and indicadores['macd'] > 0:
                condicoes_compra += 1
                motivos_compra.append("MACD positivo")
            
            # Tendência de alta
            if indicadores['tendencia'] == 'ALTA':
                condicoes_compra += 1
                motivos_compra.append("Tendência de alta (EMA)")
            
            # Preço acima das médias
            if medias and preco_atual > medias['MA99']:
                condicoes_compra += 1
                motivos_compra.append("Acima MA99 (longo prazo positivo)")
            
            # Volume e queda (EXTREMAMENTE rigoroso no primeiro trade)
            if primeiro_trade:
                # Primeiro trade: SÓ com quedas MUITO significativas
                if dados_24h and dados_24h['priceChangePercent'] < -5 and dados_24h['quoteVolume'] > 2000000000:
                    condicoes_compra += 4
                    motivos_compra.append("CRASH EXTREMO primeiro trade (-5%+)")
                elif dados_24h and dados_24h['priceChangePercent'] < -3 and dados_24h['quoteVolume'] > 1500000000:
                    condicoes_compra += 3
                    motivos_compra.append("Queda forte primeiro trade (-3%+)")
                elif dados_24h and dados_24h['priceChangePercent'] < -2:
                    condicoes_compra += 1
                    motivos_compra.append("Queda moderada primeiro trade")
            elif modo_recuperacao:
                # Recuperação: Mais agressivo
                if dados_24h and dados_24h['priceChangePercent'] < -1:
                    condicoes_compra += 2
                    motivos_compra.append("Queda recuperação (-1%)")
                elif dados_24h and dados_24h['priceChangePercent'] < -0.5:
                    condicoes_compra += 1
                    motivos_compra.append("Queda leve recuperação")
            else:
                # Normal: Rigoroso
                if dados_24h and dados_24h['priceChangePercent'] < -3 and dados_24h['quoteVolume'] > 1000000000:
                    condicoes_compra += 3
                    motivos_compra.append("Queda forte com volume alto (oportunidade)")
                elif dados_24h and dados_24h['priceChangePercent'] < -1.5:
                    condicoes_compra += 1
                    motivos_compra.append("Queda moderada")
            
            # Decisão para sem posição (flexível em modo recuperação)
            if condicoes_compra >= limite_condicoes:
                return "COMPRA", "; ".join(motivos_compra)
            else:
                status = "RECUPERAÇÃO" if modo_recuperacao else "NORMAL"
                return "AGUARDAR", f"Aguardando entrada {status} (C:{condicoes_compra}/{limite_condicoes})"
    
    def executar_compra(self, preco_atual):
        return executar_compra(self, preco_atual)
    
    def executar_venda(self, preco_atual):
        return executar_venda(self, preco_atual)
    
    def verificar_stop_loss_take_profit(self, preco_atual):
        """Verifica se deve fechar posição por SL ou TP"""
        if not self.posicao_aberta:
            return False
        

        take_profit_pct = STOP_LOSS_PCT * RELACAO_RISCO_RETORNO
        stop_loss = self.preco_entrada * (1 - STOP_LOSS_PCT)
        take_profit = self.preco_entrada * (1 + take_profit_pct)
        
        if preco_atual <= stop_loss:
            print(f"\n🛑 STOP LOSS ATIVADO! Preço: ${preco_atual:.2f} <= ${stop_loss:.2f}")
            self.executar_venda(preco_atual)
            self._salvar_estado()
            return True
        elif preco_atual >= take_profit:
            print(f"\n🎯 TAKE PROFIT ATIVADO! Preço: ${preco_atual:.2f} >= ${take_profit:.2f}")
            self.executar_venda(preco_atual)
            self._salvar_estado()
            return True
        
        return False
    
    def exibir_status(self, preco_atual, dados_24h, medias, decisao, motivo):
        """Exibe status atual do bot"""
        print(f"\n📈 {PAR} = ${preco_atual:.2f}")

        if dados_24h:
            print(f"📊 Volume 24h: ${dados_24h['quoteVolume']:,.0f} USDT")
            print(f"📈 24h: {dados_24h['priceChangePercent']:+.2f}%")

        if medias:
            print(f"📅 MA7: ${medias['MA7']:.2f} | MA25: ${medias['MA25']:.2f} | MA99: ${medias['MA99']:.2f}")

        # Status da posição
        if self.posicao_aberta:
            valor_investido = self.quantidade_btc * self.preco_entrada  # Valor em dólares investido
            valor_atual = self.quantidade_btc * preco_atual  # Valor atual em dólares
            pnl = valor_atual - valor_investido  # Lucro/perda em dólares
            pnl_pct = (preco_atual - self.preco_entrada) / self.preco_entrada * 100

            print(f"💹 POSIÇÃO ABERTA: {self.quantidade_btc:.6f} BTC @ ${self.preco_entrada:.2f}")
            print(f"💰 Valor Investido: ${valor_investido:.2f} | Valor Atual: ${valor_atual:.2f}")
            if pnl > 0:
                print(f"🟢 P&L: +${pnl:.2f} (+{pnl_pct:.2f}%)")
            else:
                print(f"🔴 P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
        else:
            print("💵 SEM POSIÇÃO ABERTA")

        print(f"🎯 {decisao}: {motivo}")

        # Status do capital
        modo_recuperacao = self.lucro_hoje < -0.01
        max_trades = MAX_TRADES_DIA + 2 if modo_recuperacao else MAX_TRADES_DIA

        if self.capital < 2.0:
            status_capital = f"🔴 Capital: ${self.capital:.2f} (INSUFICIENTE)"
        else:
            status_capital = f"💰 Capital: ${self.capital:.2f}"

        if modo_recuperacao:
            status_modo = f" | 🔄 RECUPERAÇÃO | Trades: {self.trades_hoje}/{max_trades}"
        else:
            status_modo = f" | Trades: {self.trades_hoje}/{max_trades}"

        # Exibe win rate
        total_trades = self.trades_ganhos + self.trades_perdidos
        if total_trades > 0:
            win_rate = (self.trades_ganhos / total_trades) * 100
            print(f"🏆 Win Rate: {win_rate:.2f}% ({self.trades_ganhos} acertos / {total_trades} trades)")
        else:
            print("🏆 Win Rate: -- (nenhum trade finalizado)")

        print(f"{status_capital}{status_modo} | Lucro hoje: ${self.lucro_hoje:.2f}")
    
    def run(self):
        """Loop principal do bot - multiativo e multiestratégia"""
        import requests
        while True:
            try:
                for par in self.pares:
                    preco_atual = get_price(par)
                    dados_24h = get_24h_ticker(par)

                    if not preco_atual:
                        print(f"⚠️ Erro ao obter preço de {par}")
                        self.log_manager.registrar_trade(
                            "ERRO", 0, 0, self.capital, self.lucro_hoje, (self.lucro_hoje/self.CAPITAL_INICIAL)*100,
                            f"Erro ao obter preço do ativo {par}"
                        )
                        continue

                    # Atualizar histórico
                    self.historico_precos[par].append(preco_atual)
                    if len(self.historico_precos[par]) > 100:
                        self.historico_precos[par].pop(0)

                    # Obter médias móveis
                    candles = get_daily_candles(par, limit=100)
                    medias = calcular_medias_moveis(candles) if candles else None

                    # Verificar stop loss / take profit primeiro
                    if self.verificar_stop_loss_take_profit(preco_atual):
                        continue

                    # Selecionar estratégia para o par
                    estrategia = self.estrategias.get(par, self.analisar_mercado)
                    # Passa o par para a estratégia se ela aceitar
                    try:
                        decisao, motivo = estrategia(preco_atual, dados_24h, medias, par=par)
                    except TypeError:
                        decisao, motivo = estrategia(preco_atual, dados_24h, medias)

                    # Exibir status
                    self.exibir_status(preco_atual, dados_24h, medias, decisao, motivo)

                    # Executar trades (mais flexível em modo recuperação)
                    modo_recuperacao = self.lucro_hoje < -0.01
                    max_trades = MAX_TRADES_DIA + 2 if modo_recuperacao else MAX_TRADES_DIA

                    if decisao == "COMPRA" and not self.posicao_aberta and self.trades_hoje < max_trades and self.capital >= 2.0:
                        if modo_recuperacao:
                            print(f"\n🔄 MODO RECUPERAÇÃO ATIVO - Trade {self.trades_hoje + 1}/{max_trades}")
                        self.executar_compra(preco_atual)
                    elif decisao == "VENDA" and self.posicao_aberta:
                        self.executar_venda(preco_atual)
                    elif decisao == "COMPRA" and self.capital < 2.0:
                        print(f"\n⚠️ NÃO PODE COMPRAR: Saldo insuficiente (${self.capital:.2f})")
                    elif decisao == "COMPRA" and self.trades_hoje >= max_trades:
                        status = "RECUPERAÇÃO" if modo_recuperacao else "NORMAL"
                        print(f"\n⚠️ LIMITE DE TRADES {status}: {self.trades_hoje}/{max_trades}")

                time.sleep(INTERVALO)

            except KeyboardInterrupt:
                print("\n🛑 Bot interrompido pelo usuário")
                break
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Erro de conexão com a API: {e}")
                self.log_manager.registrar_trade(
                    "ERRO_CONEXAO", 0, 0, self.capital, self.lucro_hoje, (self.lucro_hoje/self.CAPITAL_INICIAL)*100,
                    f"Erro de conexão: {e}"
                )
                time.sleep(INTERVALO * 2)
            except Exception as e:
                print(f"⚠️ Erro inesperado: {e}")
                self.log_manager.registrar_trade(
                    "ERRO_DESCONHECIDO", 0, 0, self.capital, self.lucro_hoje, (self.lucro_hoje/self.CAPITAL_INICIAL)*100,
                    f"Erro inesperado: {e}"
                )
                time.sleep(INTERVALO)

def main():
    bot = TradingBot()
    bot.run()

if __name__ == "__main__":
    main()

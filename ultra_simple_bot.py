#!/usr/bin/env python3
"""
Trading Bot Ultra-Simplificado
Funciona apenas com Python padrão + requests
"""

import time
import json
import logging
import traceback
import random
from datetime import datetime
from binance_api_fixed import get_price, get_24h_ticker, test_api_connection, get_mock_data
from simple_database_manager import DatabaseManager

# Configurações simplificadas
CAPITAL_INICIAL = 100.00
RISCO_POR_TRADE = 0.02
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.05
MAX_TRADES_DIA = 3
INTERVALO = 10
MODO_SIMULACAO = True

# Pares para trading
PARES = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleTradingBot:
    def __init__(self):
        """Inicialização ultra-simples"""
        self.db_manager = DatabaseManager()
        self.capital = CAPITAL_INICIAL
        self.trades_hoje = 0
        self.posicao_aberta = {par: False for par in PARES}
        self.precos_entrada = {par: 0 for par in PARES}
        self.stop_loss = {par: 0 for par in PARES}
        self.take_profit = {par: 0 for par in PARES}
        self.historico_precos = {par: [] for par in PARES}
        self.api_available = True
        
        # Carregar estado
        self._carregar_estado()
        
        # Testar API
        self._test_api()
        
        logger.info("✅ Bot ultra-simples inicializado")
    
    def _test_api(self):
        """Testa API de forma simples"""
        try:
            self.api_available = test_api_connection()
            status = "✅ OK" if self.api_available else "❌ Falhou"
            logger.info(f"🌐 API Status: {status}")
        except:
            self.api_available = False
            logger.warning("⚠️ API não disponível - usando dados simulados")
    
    def _carregar_estado(self):
        """Carrega estado do banco"""
        try:
            self.capital = self.db_manager.get_config('capital', CAPITAL_INICIAL)
            self.trades_hoje = self.db_manager.get_config('trades_hoje', 0)
            logger.info(f"💰 Capital carregado: ${self.capital:.2f}")
        except:
            logger.warning("⚠️ Usando valores padrão")
    
    def _salvar_estado(self):
        """Salva estado no banco"""
        try:
            self.db_manager.set_config('capital', self.capital)
            self.db_manager.set_config('trades_hoje', self.trades_hoje)
        except Exception as e:
            logger.error(f"Erro ao salvar: {e}")
    
    def obter_preco_seguro(self, par):
        """Obtém preço com fallback"""
        try:
            if self.api_available:
                preco = get_price(par)
                if preco:
                    return preco
            
            # Fallback para dados simulados
            mock_data = get_mock_data(par)
            return mock_data['price']
            
        except:
            # Último recurso: preço simulado básico
            base_prices = {"BTCUSDT": 50000, "ETHUSDT": 3000, "BNBUSDT": 300}
            base = base_prices.get(par, 100)
            return base + random.uniform(-base*0.02, base*0.02)
    
    def calcular_rsi_simples(self, precos, periodo=14):
        """RSI ultra-simplificado"""
        if len(precos) < periodo + 1:
            return 50  # Neutro
        
        deltas = [precos[i] - precos[i-1] for i in range(1, len(precos))]
        ganhos = [d if d > 0 else 0 for d in deltas[-periodo:]]
        perdas = [-d if d < 0 else 0 for d in deltas[-periodo:]]
        
        media_ganhos = sum(ganhos) / periodo
        media_perdas = sum(perdas) / periodo
        
        if media_perdas == 0:
            return 100
        
        rs = media_ganhos / media_perdas
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def analisar_simples(self, par, preco):
        """Análise ultra-simplificada"""
        try:
            # Atualizar histórico
            self.historico_precos[par].append(preco)
            if len(self.historico_precos[par]) > 50:
                self.historico_precos[par] = self.historico_precos[par][-50:]
            
            if len(self.historico_precos[par]) < 15:
                return "AGUARDAR", "Construindo histórico"
            
            # RSI simples
            rsi = self.calcular_rsi_simples(self.historico_precos[par])
            
            # Tendência simples (últimos 5 vs 5 anteriores)
            recentes = self.historico_precos[par][-5:]
            anteriores = self.historico_precos[par][-10:-5]
            
            if len(recentes) == 5 and len(anteriores) == 5:
                media_recente = sum(recentes) / 5
                media_anterior = sum(anteriores) / 5
                tendencia_alta = media_recente > media_anterior
            else:
                tendencia_alta = True  # Default
            
            # Decisão simples
            if rsi < 30 and tendencia_alta:
                return "COMPRA", f"RSI oversold ({rsi:.1f}) + tendência alta"
            elif rsi > 70 and not tendencia_alta:
                return "VENDA", f"RSI overbought ({rsi:.1f}) + tendência baixa"
            else:
                return "AGUARDAR", f"RSI neutro ({rsi:.1f})"
                
        except Exception as e:
            logger.error(f"Erro na análise: {e}")
            return "AGUARDAR", "Erro na análise"
    
    def executar_compra(self, preco, par, motivo):
        """Compra simplificada"""
        try:
            if MODO_SIMULACAO and not self.posicao_aberta[par]:
                quantidade = (self.capital * 0.1) / preco
                
                self.posicao_aberta[par] = True
                self.precos_entrada[par] = preco
                self.stop_loss[par] = preco * (1 - STOP_LOSS_PCT)
                self.take_profit[par] = preco * (1 + TAKE_PROFIT_PCT)
                self.trades_hoje += 1
                
                logger.info(f"🟢 COMPRA {par}")
                logger.info(f"   💰 Preço: ${preco:.4f}")
                logger.info(f"   📊 Quantidade: {quantidade:.6f}")
                logger.info(f"   🛑 Stop: ${self.stop_loss[par]:.4f}")
                logger.info(f"   🎯 Target: ${self.take_profit[par]:.4f}")
                logger.info(f"   📋 {motivo}")
                
                # Salvar no banco
                self.db_manager.add_trade(par, "BUY", preco, quantidade, 0, motivo)
                
                return True
        except Exception as e:
            logger.error(f"Erro na compra: {e}")
        return False
    
    def executar_venda(self, preco, par, motivo):
        """Venda simplificada"""
        try:
            if MODO_SIMULACAO and self.posicao_aberta[par]:
                preco_entrada = self.precos_entrada[par]
                quantidade = (self.capital * 0.1) / preco_entrada
                lucro = (preco - preco_entrada) * quantidade
                lucro_pct = ((preco - preco_entrada) / preco_entrada) * 100
                
                self.posicao_aberta[par] = False
                self.capital += lucro
                
                status = "LUCRO 🟢" if lucro > 0 else "PREJUÍZO 🔴"
                
                logger.info(f"🔴 VENDA {par} - {status}")
                logger.info(f"   💰 Entrada: ${preco_entrada:.4f}")
                logger.info(f"   💰 Saída: ${preco:.4f}")
                logger.info(f"   📊 Resultado: ${lucro:.2f} ({lucro_pct:.2f}%)")
                logger.info(f"   💼 Capital: ${self.capital:.2f}")
                logger.info(f"   📋 {motivo}")
                
                # Salvar no banco
                self.db_manager.add_trade(par, "SELL", preco, quantidade, lucro, motivo)
                
                return True
        except Exception as e:
            logger.error(f"Erro na venda: {e}")
        return False
    
    def verificar_sl_tp(self, preco, par):
        """Verifica Stop Loss e Take Profit"""
        if not self.posicao_aberta[par]:
            return False
        
        if preco <= self.stop_loss[par]:
            self.executar_venda(preco, par, "Stop Loss")
            return True
        elif preco >= self.take_profit[par]:
            self.executar_venda(preco, par, "Take Profit")
            return True
        
        return False
    
    def exibir_status(self, par, preco, decisao, motivo):
        """Status simplificado"""
        status_pos = "🟢 ABERTA" if self.posicao_aberta[par] else "⚪ FECHADA"
        
        print(f"\n📊 {par} - {status_pos}")
        print(f"   💰 Preço: ${preco:.4f}")
        print(f"   🎯 Decisão: {decisao}")
        print(f"   📋 {motivo}")
        
        if self.posicao_aberta[par]:
            entrada = self.precos_entrada[par]
            pnl = ((preco - entrada) / entrada) * 100
            print(f"   📈 P&L: {pnl:+.2f}%")
    
    def mostrar_estatisticas(self):
        """Mostra estatísticas simples"""
        try:
            stats = self.db_manager.get_performance_stats()
            
            print("\n" + "="*50)
            print("📊 ESTATÍSTICAS")
            print(f"💼 Capital atual: ${self.capital:.2f}")
            print(f"📈 Trades hoje: {self.trades_hoje}/{MAX_TRADES_DIA}")
            print(f"🎯 Total trades: {stats['total_trades']}")
            print(f"✅ Wins: {stats['winning_trades']}")
            print(f"❌ Losses: {stats['losing_trades']}")
            print(f"📊 Win Rate: {stats['win_rate']:.1f}%")
            print(f"💰 Lucro total: ${stats['total_profit']:.2f}")
            print("="*50)
            
        except Exception as e:
            logger.error(f"Erro ao mostrar stats: {e}")
    
    def run(self):
        """Loop principal ultra-simples"""
        logger.info("🚀 BOT ULTRA-SIMPLES INICIADO")
        logger.info(f"💰 Capital: ${self.capital:.2f}")
        logger.info(f"📈 Pares: {', '.join(PARES)}")
        logger.info(f"⏰ Intervalo: {INTERVALO}s")
        logger.info("="*50)
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                
                # Mostrar estatísticas a cada 10 ciclos
                if cycle_count % 10 == 1:
                    self.mostrar_estatisticas()
                
                for par in PARES:
                    try:
                        # Obter preço
                        preco = self.obter_preco_seguro(par)
                        
                        # Verificar SL/TP primeiro
                        if self.verificar_sl_tp(preco, par):
                            continue
                        
                        # Análise
                        decisao, motivo = self.analisar_simples(par, preco)
                        
                        # Exibir status
                        self.exibir_status(par, preco, decisao, motivo)
                        
                        # Executar trades
                        if (decisao == "COMPRA" and 
                            not self.posicao_aberta[par] and 
                            self.trades_hoje < MAX_TRADES_DIA):
                            self.executar_compra(preco, par, motivo)
                        
                        elif decisao == "VENDA" and self.posicao_aberta[par]:
                            self.executar_venda(preco, par, motivo)
                    
                    except Exception as e:
                        logger.error(f"Erro processando {par}: {e}")
                        continue
                
                # Salvar estado
                self._salvar_estado()
                
                # Aguardar
                time.sleep(INTERVALO)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Bot parado pelo usuário")
                self.mostrar_estatisticas()
                break
            except Exception as e:
                logger.error(f"⚠️ Erro no loop: {e}")
                traceback.print_exc()
                time.sleep(INTERVALO * 2)  # Aguardar mais em caso de erro

def main():
    """Função principal"""
    try:
        print("🤖 Trading Bot Ultra-Simples")
        print("=" * 40)
        
        # Verificar dependências mínimas
        try:
            import requests
            print("✅ requests: OK")
        except ImportError:
            print("❌ requests não encontrado")
            print("💡 Execute: pip3 install --break-system-packages requests")
            return
        
        # Inicializar e executar bot
        bot = SimpleTradingBot()
        bot.run()
        
    except Exception as e:
        logger.critical(f"❌ Erro crítico: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
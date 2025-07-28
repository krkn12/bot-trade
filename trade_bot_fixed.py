import time
import json
import logging
import traceback
from datetime import datetime, timedelta
from binance_api_fixed import get_price, get_daily_candles, get_24h_ticker, test_api_connection, get_mock_data
from core.estrategias import calcular_rsi, calcular_macd, calcular_ema, calcular_medias_moveis
from core.database_manager import DatabaseManager
from config_fixed import *

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, pares=None, estrategias=None, capital_inicial=CAPITAL_INICIAL, moeda_base=MOEDA_BASE):
        """Inicialização do bot com tratamento de erro melhorado"""
        try:
            self.db_manager = DatabaseManager()
            self.ultima_decisao = ""
            self.trades_ganhos = 0
            self.trades_perdidos = 0
            self.slippage = 0.0005
            self.log_trades = []
            self.capital_inicial = capital_inicial
            self.moeda_base = moeda_base
            self.pares = pares if pares else [PAR]
            self.rsi_periodo = 14
            
            # Controle de erros
            self.consecutive_errors = 0
            self.last_error_time = 0
            self.api_available = True
            
            # Inicializar configurações principais
            self.usar_ml = USAR_ML
            self.usar_selecao_automatica = USAR_SELECAO_AUTOMATICA
            
            # Carregar estado
            self._carregar_estado()
            
            # Estratégias
            self.estrategias = estrategias if estrategias else {par: self.analisar_mercado for par in self.pares}
            self.historico_precos = {par: [] for par in self.pares}
            self.historico_volumes = {par: [] for par in self.pares}
            
            # Estado multi-ativo
            self.posicao_aberta = {par: False for par in self.pares}
            self.precos_entrada = {par: 0 for par in self.pares}
            self.quantidades_compradas = {par: 0 for par in self.pares}
            self.stop_loss = {par: 0 for par in self.pares}
            self.take_profit = {par: 0 for par in self.pares}
            
            # Testar conectividade da API
            self._test_api_connectivity()
            
            logger.info("✅ TradingBot inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização do bot: {e}")
            traceback.print_exc()
            raise
    
    def _test_api_connectivity(self):
        """Testa a conectividade com a API"""
        try:
            self.api_available = test_api_connection(USE_TESTNET)
            if not self.api_available:
                logger.warning("⚠️ API não disponível. Bot funcionará em modo limitado.")
        except Exception as e:
            logger.error(f"Erro ao testar API: {e}")
            self.api_available = False
    
    def _handle_api_error(self, error, operation="API call"):
        """Gerencia erros da API de forma centralizada"""
        self.consecutive_errors += 1
        self.last_error_time = time.time()
        
        logger.error(f"Erro em {operation}: {error}")
        
        if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.critical(f"Muitos erros consecutivos ({self.consecutive_errors}). Entrando em cooldown...")
            time.sleep(ERROR_COOLDOWN_TIME)
            self.consecutive_errors = 0
        
        # Se API não está disponível, tentar dados mock se habilitado
        if USE_MOCK_DATA and not self.api_available:
            logger.info("🔄 Usando dados mock devido a problemas na API")
            return True
        
        return False
    
    def _reset_error_counter(self):
        """Reseta contador de erros quando operação é bem-sucedida"""
        if self.consecutive_errors > 0:
            logger.info("✅ Conectividade restaurada")
            self.consecutive_errors = 0
    
    def get_price_safe(self, symbol):
        """Obtém preço com fallback seguro"""
        try:
            if self.api_available:
                price = get_price(symbol, USE_TESTNET)
                if price is not None:
                    self._reset_error_counter()
                    return price
            
            # Fallback para dados mock se habilitado
            if USE_MOCK_DATA:
                mock_data = get_mock_data(symbol)
                return mock_data['price']
            
            return None
            
        except Exception as e:
            if self._handle_api_error(e, f"get_price({symbol})"):
                mock_data = get_mock_data(symbol)
                return mock_data['price']
            return None
    
    def get_24h_ticker_safe(self, symbol):
        """Obtém ticker 24h com fallback seguro"""
        try:
            if self.api_available:
                ticker = get_24h_ticker(symbol, USE_TESTNET)
                if ticker is not None:
                    self._reset_error_counter()
                    return ticker
            
            # Fallback para dados mock se habilitado
            if USE_MOCK_DATA:
                mock_data = get_mock_data(symbol)
                return mock_data['ticker_24h']
            
            return None
            
        except Exception as e:
            if self._handle_api_error(e, f"get_24h_ticker({symbol})"):
                mock_data = get_mock_data(symbol)
                return mock_data['ticker_24h']
            return None
    
    def get_candles_safe(self, symbol, limit=100):
        """Obtém candles com fallback seguro"""
        try:
            if self.api_available:
                candles = get_daily_candles(symbol, limit, USE_TESTNET)
                if candles is not None:
                    self._reset_error_counter()
                    return candles
            
            # Fallback para dados simulados básicos
            if USE_MOCK_DATA:
                # Gerar candles simulados simples
                mock_price = get_mock_data(symbol)['price']
                mock_candles = []
                for i in range(limit):
                    # Gerar OHLCV simulado
                    base = mock_price + (i - limit/2) * 10
                    mock_candles.append([
                        int(time.time() * 1000) - (i * 86400000),  # timestamp
                        str(base + 50),   # open
                        str(base + 100),  # high
                        str(base - 50),   # low
                        str(base),        # close
                        str(1000),        # volume
                        int(time.time() * 1000) - (i * 86400000),  # close time
                        str(50000),       # quote volume
                        100,              # trades
                        str(500),         # taker buy base
                        str(25000),       # taker buy quote
                        "0"               # ignore
                    ])
                return mock_candles[::-1]  # Reverse para ordem cronológica
            
            return None
            
        except Exception as e:
            if self._handle_api_error(e, f"get_candles({symbol})"):
                # Retornar dados simulados em caso de erro
                mock_price = get_mock_data(symbol)['price']
                return [[0, str(mock_price), str(mock_price), str(mock_price), str(mock_price), "1000", 0, "50000", 100, "500", "25000", "0"]]
            return None
    
    def analisar_mercado(self, preco_atual, dados_24h, medias, par="BTCUSDT"):
        """Análise de mercado com tratamento de erro melhorado"""
        try:
            if not preco_atual or not dados_24h:
                logger.warning(f"Dados insuficientes para análise de {par}")
                return "AGUARDAR", "Dados insuficientes"
            
            # Atualizar histórico
            self.historico_precos[par].append(preco_atual)
            if len(self.historico_precos[par]) > 100:
                self.historico_precos[par] = self.historico_precos[par][-100:]
            
            # Análise técnica básica
            if len(self.historico_precos[par]) < 14:
                return "AGUARDAR", "Histórico insuficiente"
            
            rsi = calcular_rsi(self.historico_precos[par], self.rsi_periodo)
            if rsi is None:
                return "AGUARDAR", "Erro no cálculo RSI"
            
            macd = calcular_macd(self.historico_precos[par])
            
            # Lógica de decisão simplificada
            motivos_compra = []
            motivos_venda = []
            
            # RSI
            if rsi < 30:
                motivos_compra.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                motivos_venda.append(f"RSI overbought ({rsi:.1f})")
            
            # MACD
            if macd and macd > 0:
                motivos_compra.append("MACD positivo")
            elif macd and macd < 0:
                motivos_venda.append("MACD negativo")
            
            # Decisão final
            if len(motivos_compra) >= 2:
                return "COMPRA", " | ".join(motivos_compra)
            elif len(motivos_venda) >= 2:
                return "VENDA", " | ".join(motivos_venda)
            else:
                return "AGUARDAR", "Sinais insuficientes"
                
        except Exception as e:
            logger.error(f"Erro na análise de mercado para {par}: {e}")
            return "AGUARDAR", f"Erro na análise: {e}"
    
    def executar_compra(self, preco, par, motivo):
        """Executa compra com logging melhorado"""
        try:
            if MODO_SIMULACAO:
                quantidade = (self.capital * 0.1) / preco  # 10% do capital
                self.posicao_aberta[par] = True
                self.precos_entrada[par] = preco
                self.quantidades_compradas[par] = quantidade
                self.stop_loss[par] = preco * (1 - STOP_LOSS_PCT)
                self.take_profit[par] = preco * (1 + TAKE_PROFIT_PCT)
                
                logger.info(f"🟢 COMPRA SIMULADA - {par}")
                logger.info(f"   💰 Preço: ${preco:.4f} | Qtd: {quantidade:.6f}")
                logger.info(f"   🛑 Stop Loss: ${self.stop_loss[par]:.4f}")
                logger.info(f"   🎯 Take Profit: ${self.take_profit[par]:.4f}")
                logger.info(f"   📋 Motivo: {motivo}")
                
                self.trades_hoje += 1
                return True
            else:
                logger.info(f"⚠️ Compra real desabilitada para {par}")
                return False
                
        except Exception as e:
            logger.error(f"Erro na execução de compra para {par}: {e}")
            return False
    
    def executar_venda(self, preco, par, motivo):
        """Executa venda com logging melhorado"""
        try:
            if MODO_SIMULACAO and self.posicao_aberta.get(par, False):
                preco_entrada = self.precos_entrada[par]
                quantidade = self.quantidades_compradas[par]
                lucro = (preco - preco_entrada) * quantidade
                lucro_pct = ((preco - preco_entrada) / preco_entrada) * 100
                
                self.posicao_aberta[par] = False
                self.capital += lucro
                
                if lucro > 0:
                    self.trades_ganhos += 1
                    logger.info(f"🟢 VENDA SIMULADA - {par} - LUCRO")
                else:
                    self.trades_perdidos += 1
                    logger.info(f"🔴 VENDA SIMULADA - {par} - PREJUÍZO")
                
                logger.info(f"   💰 Preço entrada: ${preco_entrada:.4f}")
                logger.info(f"   💰 Preço saída: ${preco:.4f}")
                logger.info(f"   📊 Lucro: ${lucro:.2f} ({lucro_pct:.2f}%)")
                logger.info(f"   📋 Motivo: {motivo}")
                logger.info(f"   💼 Capital atual: ${self.capital:.2f}")
                
                return True
            else:
                logger.info(f"⚠️ Venda real desabilitada para {par}")
                return False
                
        except Exception as e:
            logger.error(f"Erro na execução de venda para {par}: {e}")
            return False
    
    def verificar_stop_loss_take_profit(self, preco_atual, par):
        """Verifica stop loss e take profit"""
        try:
            if not self.posicao_aberta.get(par, False):
                return False
            
            if preco_atual <= self.stop_loss[par]:
                self.executar_venda(preco_atual, par, "Stop Loss atingido")
                return True
            elif preco_atual >= self.take_profit[par]:
                self.executar_venda(preco_atual, par, "Take Profit atingido")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro na verificação de SL/TP para {par}: {e}")
            return False
    
    def exibir_status(self, par, preco, dados_24h, medias, decisao, motivo):
        """Exibe status atual de forma limpa"""
        try:
            variacao_24h = dados_24h.get('priceChangePercent', 0) if dados_24h else 0
            volume_24h = dados_24h.get('quoteVolume', 0) if dados_24h else 0
            
            status_posicao = "🟢 ABERTA" if self.posicao_aberta.get(par, False) else "⚪ FECHADA"
            
            print(f"\n📊 {par} - {status_posicao}")
            print(f"   💰 Preço: ${preco:.4f} ({variacao_24h:+.2f}%)")
            print(f"   📈 Volume 24h: ${volume_24h:,.0f}")
            print(f"   🎯 Decisão: {decisao}")
            print(f"   📋 Motivo: {motivo}")
            
            if self.posicao_aberta.get(par, False):
                preco_entrada = self.precos_entrada[par]
                lucro_nao_realizado = ((preco - preco_entrada) / preco_entrada) * 100
                print(f"   💼 Entrada: ${preco_entrada:.4f}")
                print(f"   📊 P&L: {lucro_nao_realizado:+.2f}%")
                
        except Exception as e:
            logger.error(f"Erro ao exibir status para {par}: {e}")
    
    def _carregar_estado(self):
        """Carrega estado do banco com fallback"""
        try:
            self.capital = self.db_manager.get_config('capital', CAPITAL_INICIAL)
            self.trades_hoje = self.db_manager.get_config('trades_hoje', 0)
            self.lucro_hoje = self.db_manager.get_config('lucro_hoje', 0.0)
            logger.info("✅ Estado carregado do banco de dados")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar estado: {e}. Usando valores padrão.")
            self.capital = CAPITAL_INICIAL
            self.trades_hoje = 0
            self.lucro_hoje = 0.0
    
    def _salvar_estado(self):
        """Salva estado no banco"""
        try:
            self.db_manager.set_config('capital', self.capital)
            self.db_manager.set_config('trades_hoje', self.trades_hoje)
            self.db_manager.set_config('lucro_hoje', self.lucro_hoje)
        except Exception as e:
            logger.error(f"Erro ao salvar estado: {e}")
    
    def run_simple(self):
        """Loop principal simplificado para debug"""
        logger.info("🟢 BOT TRADING INICIADO (Modo Simples)")
        logger.info(f"💰 Capital: ${self.capital:.2f}")
        logger.info(f"📈 Pares: {', '.join(self.pares)}")
        logger.info(f"🤖 ML: {'ATIVADO' if self.usar_ml else 'DESATIVADO'}")
        logger.info("=" * 50)
        
        while True:
            try:
                for par in self.pares:
                    # Obter dados com fallback
                    preco_atual = self.get_price_safe(par)
                    dados_24h = self.get_24h_ticker_safe(par)
                    candles = self.get_candles_safe(par, 100)
                    
                    if not preco_atual:
                        logger.warning(f"⚠️ Dados não disponíveis para {par}")
                        continue
                    
                    # Calcular médias móveis
                    medias = calcular_medias_moveis(candles) if candles else None
                    
                    # Verificar SL/TP
                    if self.verificar_stop_loss_take_profit(preco_atual, par):
                        continue
                    
                    # Análise e decisão
                    decisao, motivo = self.analisar_mercado(preco_atual, dados_24h, medias, par)
                    
                    # Exibir status
                    self.exibir_status(par, preco_atual, dados_24h, medias, decisao, motivo)
                    
                    # Executar trades
                    if decisao == "COMPRA" and not self.posicao_aberta.get(par, False) and self.trades_hoje < MAX_TRADES_DIA:
                        self.executar_compra(preco_atual, par, motivo)
                    elif decisao == "VENDA" and self.posicao_aberta.get(par, False):
                        self.executar_venda(preco_atual, par, motivo)
                
                # Salvar estado
                self._salvar_estado()
                
                # Aguardar próximo ciclo
                time.sleep(INTERVALO)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Bot interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"⚠️ Erro no loop principal: {e}")
                traceback.print_exc()
                
                # Implementar backoff exponencial em caso de erro
                time.sleep(min(INTERVALO * 2, 60))

def main():
    try:
        # Inicializar bot com configurações simplificadas
        bot = TradingBot(
            pares=FALLBACK_PAIRS if not USAR_SELECAO_AUTOMATICA else None,
            capital_inicial=CAPITAL_INICIAL,
            moeda_base=MOEDA_BASE
        )
        
        # Executar em modo simples
        bot.run_simple()
        
    except Exception as e:
        logger.critical(f"❌ Erro crítico: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
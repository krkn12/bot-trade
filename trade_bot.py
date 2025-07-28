import time
import json
from datetime import datetime, timedelta
from binance_api import get_price, get_daily_candles, get_24h_ticker
from core.estrategias import calcular_rsi, calcular_macd, calcular_ema, calcular_medias_moveis
from core.database_manager import DatabaseManager
from core.async_api_handler import AsyncAPIHandler
from core.execucao import executar_compra, executar_venda
from config import INTERVALO, PAR, CAPITAL_INICIAL, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_TRADES_DIA, MODO_SIMULACAO, RELACAO_RISCO_RETORNO, TAXA_BINANCE, USAR_ML, ML_CONFIANCA_MIN, ML_TREINO_INTERVALO, ML_MODELOS_DIR, ML_FEATURES, ML_TIMEFRAMES, ML_JANELA_PREVISAO, USAR_SELECAO_AUTOMATICA, SELECAO_INTERVALO, SELECAO_MAX_MOEDAS, SELECAO_DIAS_NOVAS, SELECAO_VOLUME_MIN, SELECAO_VOLATILIDADE_MIN, MOEDA_BASE
from core.ml_predictor import MLPredictor
from core.coin_selector import CoinSelector

import winsound
import asyncio

import os

class TradingBot:

    def __init__(self, pares=None, estrategias=None, capital_inicial=CAPITAL_INICIAL, moeda_base=MOEDA_BASE, usar_ml=USAR_ML, usar_selecao_automatica=USAR_SELECAO_AUTOMATICA):
        self.db_manager = DatabaseManager()
        self.ultima_decisao = ""
        self.trades_ganhos = 0
        self.trades_perdidos = 0
        self.slippage = 0.0005  # 0.05% slippage padrão
        self.log_trades = []
        self.capital_inicial = capital_inicial
        self.moeda_base = moeda_base
        self.pares = pares if pares else [PAR]
        # Parâmetro adaptativo do RSI
        self.rsi_periodo = 14

        # Inicializar configurações principais ANTES de carregar o estado
        self.usar_ml = usar_ml
        self.usar_selecao_automatica = usar_selecao_automatica

        self._ajustar_rsi_periodo()
        self._carregar_estado()
        # Dicionário: par -> função de estratégia
        self.estrategias = estrategias if estrategias else {par: self.analisar_mercado for par in self.pares}
        self.historico_precos = {par: [] for par in self.pares}
        self.historico_volumes = {par: [] for par in self.pares}
        self.intervalo_treino_ml = ML_TREINO_INTERVALO
        
        # --- Variáveis de estado multi-ativo ---
        self.posicao_aberta = {par: False for par in self.pares}
        self.precos_entrada = {par: 0 for par in self.pares}
        self.quantidades_compradas = {par: 0 for par in self.pares}
        self.stop_loss = {par: 0 for par in self.pares}
        self.take_profit = {par: 0 for par in self.pares}
        
        # Inicializar preditor de ML
        if self.usar_ml:
            try:
                self.ml_predictor = MLPredictor(modelos_dir=ML_MODELOS_DIR, 
                                               features=ML_FEATURES, 
                                               timeframes=ML_TIMEFRAMES, 
                                               janela_previsao=ML_JANELA_PREVISAO)
                print("✅ Preditor de Machine Learning inicializado")
                print(f"📊 Features: {', '.join(ML_FEATURES)}")
                print(f"⏱️ Timeframes: {', '.join(ML_TIMEFRAMES)}")
                print(f"🎯 Confiança mínima: {ML_CONFIANCA_MIN*100:.1f}%")
            except Exception as e:
                print(f"⚠️ Erro ao inicializar ML Predictor: {e}")
                self.usar_ml = False
        
        # Inicializar seletor automático de moedas
        if self.usar_selecao_automatica:
            try:
                self.coin_selector = CoinSelector()
                # Configurar o seletor com os parâmetros do config.py
                self.coin_selector.set_scan_interval(SELECAO_INTERVALO)
                self.coin_selector.set_max_coins(SELECAO_MAX_MOEDAS)
                self.coin_selector.set_volume_threshold(SELECAO_VOLUME_MIN)
                self.coin_selector.set_volatility_threshold(SELECAO_VOLATILIDADE_MIN)
                # Definir a moeda base para o seletor
                self.coin_selector.quote_asset = self.moeda_base
                print("✅ Seletor automático de moedas inicializado")
                print(f"🔍 Intervalo de busca: {SELECAO_INTERVALO/3600:.1f} horas")
                print(f"🔢 Máximo de moedas: {SELECAO_MAX_MOEDAS}")
                print(f"📊 Volume mínimo: ${SELECAO_VOLUME_MIN:,.2f}")
                print(f"📈 Volatilidade mínima: {SELECAO_VOLATILIDADE_MIN:.1f}%")
                print(f"💱 Moeda base: {self.moeda_base}")
                
                # Atualizar pares iniciais se necessário
                self._atualizar_pares_negociacao()
            except Exception as e:
                print(f"⚠️ Erro ao inicializar seletor automático de moedas: {e}")
                self.usar_selecao_automatica = False
        
        print("🟢 BOT TRADING PROFISSIONAL INICIADO")
        print(f"💰 Capital Inicial: ${self.capital:.2f}")
        print(f"🎯 Meta: {MAX_TRADES_DIA} trades/dia máx")
        print(f"📈 Pares monitorados: {', '.join(self.pares)}")
        print(f"🧠 Machine Learning: {'ATIVADO' if self.usar_ml else 'DESATIVADO'}")
        print("═" * 50)

    def _ajustar_rsi_periodo(self):
        try:
            # Ajusta o período do RSI conforme o desempenho do dia anterior
            stats = self.db_manager.get_trade_statistics(days=1)
            lucro_hoje = stats.get('net_profit') or 0 # Garante que None se torne 0
            if lucro_hoje < 0:
                self.rsi_periodo = min(20, self.rsi_periodo + 2)  # Fica mais conservador
            elif lucro_hoje > 0:
                self.rsi_periodo = max(8, self.rsi_periodo - 2)   # Fica mais agressivo
        except Exception as e:
            print(f"⚠️ Erro ao ajustar RSI: {e}")
            self.db_manager.log("ERROR", "TradingBot", f"Erro ao ajustar RSI: {e}")
            
    def _atualizar_pares_negociacao(self):
        """Atualiza os pares de negociação com base no seletor automático de moedas"""
        if not self.usar_selecao_automatica:
            return
                
        # Verificar se é hora de atualizar os pares
        tempo_atual = time.time()
        if tempo_atual - self.ultima_atualizacao_moedas < SELECAO_INTERVALO:
            return
                
        print("🔄 Atualizando pares de negociação...")
        self.ultima_atualizacao_moedas = tempo_atual
        
        # Obter moedas selecionadas pelo seletor
        moedas_selecionadas = self.coin_selector.get_selected_coins()
        
        if not moedas_selecionadas:
            print("⚠️ Nenhuma moeda selecionada pelo seletor automático")
            return
        
        # Verificar se os pares são válidos na Binance
        async def verificar_par_valido(par):
            try:
                async with AsyncAPIHandler() as api:
                    preco = await api.get_price(par)
                    if preco and not isinstance(preco, Exception):
                        return True
                    print(f"⚠️ Par {par} inválido ou sem preço disponível")
                    return False
            except Exception as e:
                print(f"⚠️ Erro ao verificar par {par}: {e}")
                return False
        
        # Filtrar apenas pares válidos
        loop = asyncio.get_event_loop()
        tarefas = [verificar_par_valido(par) for par in moedas_selecionadas]
        resultados = loop.run_until_complete(asyncio.gather(*tarefas))
        moedas_validas = [par for par, valido in zip(moedas_selecionadas, resultados) if valido]
        
        if not moedas_validas:
            print("⚠️ Nenhum par válido encontrado. Mantendo pares atuais.")
            return
        
        # Verificar se há mudanças nos pares
        if set(moedas_validas) == set(self.pares):
            print("ℹ️ Pares de negociação já estão atualizados")
            return
        
        # Salvar posições abertas para não perder o rastreamento
        posicoes_abertas = {par: self.posicao_aberta.get(par, False) for par in self.pares}
        
        # Atualizar pares
        novos_pares = []
        removidos = []
        
        for par in moedas_validas:
            if par not in self.pares:
                novos_pares.append(par)
                
        for par in self.pares:
            if par not in moedas_validas and not posicoes_abertas.get(par, False):
                removidos.append(par)
        
        # Manter pares com posições abertas e adicionar novos pares selecionados
        pares_atualizados = [par for par in self.pares if par in moedas_validas or posicoes_abertas.get(par, False)]
        for par in novos_pares:
            if par not in pares_atualizados:
                pares_atualizados.append(par)
        
        # Atualizar a lista de pares
        self.pares = pares_atualizados
        
        # Atualizar estratégias para os novos pares
        self.estrategias = {par: self.analisar_mercado for par in self.pares}
        
        # Inicializar histórico para novos pares
        for par in novos_pares:
            self.historico_precos[par] = []
            self.historico_volumes[par] = []
            self.posicao_aberta[par] = posicoes_abertas.get(par, False)
            self.precos_entrada[par] = 0
            self.stop_loss[par] = 0
            self.take_profit[par] = 0
        
        # Limpar histórico de pares removidos para economizar memória
        for par in removidos:
            if par in self.historico_precos:
                del self.historico_precos[par]
            if par in self.historico_volumes:
                del self.historico_volumes[par]
        
        print(f"✅ Pares de negociação atualizados: {len(self.pares)} pares ativos")
        print(f"📈 Novos pares: {', '.join(novos_pares) if novos_pares else 'Nenhum'}")
        print(f"📉 Pares removidos: {', '.join(removidos) if removidos else 'Nenhum'}")
        print(f"🔍 Pares atuais: {', '.join(self.pares)}")
        
        # Salvar estado atualizado
        self._salvar_estado()


    def _carregar_estado(self):
        """Carrega o estado do bot a partir do banco de dados."""
        try:
            self.capital = self.db_manager.get_config('capital', CAPITAL_INICIAL)
            self.trades_hoje = self.db_manager.get_config('trades_hoje', 0)
            self.lucro_hoje = self.db_manager.get_config('lucro_hoje', 0.0)
            self.posicao_aberta = self.db_manager.get_config('posicao_aberta', {par: False for par in self.pares})
            self.precos_entrada = self.db_manager.get_config('precos_entrada', {par: 0 for par in self.pares})
            self.quantidades_compradas = self.db_manager.get_config('quantidades_compradas', {par: 0 for par in self.pares})
            self.usar_ml = self.db_manager.get_config('usar_ml', self.usar_ml)
            self.ultimo_treino_ml = self.db_manager.get_config('ultimo_treino_ml', 0)
            self.rsi_periodo = self.db_manager.get_config('rsi_periodo', 14)
            self.usar_selecao_automatica = self.db_manager.get_config('usar_selecao_automatica', self.usar_selecao_automatica)
            self.ultima_atualizacao_moedas = self.db_manager.get_config('ultima_atualizacao_moedas', 0)
            
            pares_salvos = self.db_manager.get_config('pares', self.pares)
            if pares_salvos:
                self.pares = pares_salvos
                self.estrategias = {par: self.analisar_mercado for par in self.pares}

            print("✅ Estado do bot carregado do banco de dados.")
        except Exception as e:
            print(f"⚠️ Erro ao carregar estado do DB: {e}. Usando valores padrão.")
            self.db_manager.log("ERROR", "TradingBot", f"Falha ao carregar estado: {e}")
            # Definir valores padrão em caso de falha
            self.capital = CAPITAL_INICIAL
            self.trades_hoje = 0
            self.posicao_aberta = {par: False for par in self.pares}
            self.lucro_hoje = 0.0

    def _salvar_estado(self):
        """Salva o estado atual do bot no banco de dados."""
        try:
            self.db_manager.set_config('capital', self.capital)
            self.db_manager.set_config('trades_hoje', self.trades_hoje)
            self.db_manager.set_config('lucro_hoje', self.lucro_hoje)
            self.db_manager.set_config('posicao_aberta', self.posicao_aberta)
            self.db_manager.set_config('precos_entrada', self.precos_entrada)
            self.db_manager.set_config('quantidades_compradas', self.quantidades_compradas)
            self.db_manager.set_config('usar_ml', self.usar_ml)
            self.db_manager.set_config('ultimo_treino_ml', self.ultimo_treino_ml)
            self.db_manager.set_config('rsi_periodo', self.rsi_periodo)
            self.db_manager.set_config('usar_selecao_automatica', self.usar_selecao_automatica)
            self.db_manager.set_config('ultima_atualizacao_moedas', self.ultima_atualizacao_moedas)
            self.db_manager.set_config('pares', self.pares)
        except Exception as e:
            print(f"⚠️ Erro ao salvar estado no DB: {e}")
            self.db_manager.log("ERROR", "TradingBot", f"Falha ao salvar estado: {e}")

    
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
    
    def treinar_modelo_ml(self, par, force_retrain=False):
        """Treina o modelo de ML para um par específico"""
        if not self.usar_ml or not hasattr(self, 'ml_predictor'):
            return {"error": "ML não está ativado"}
        
        if len(self.historico_precos[par]) < 200:
            return {"error": "Dados históricos insuficientes para treinar modelo"}
        
        volumes = self.historico_volumes.get(par, None)
        if volumes and len(volumes) != len(self.historico_precos[par]):
            volumes = None
        
        try:
            # Criar features adicionais para o treinamento
            features_extras = {}
            
            # Adicionar indicadores técnicos como features
            indicadores = self.calcular_indicadores(self.historico_precos[par])
            if indicadores:
                for indicador, valor in indicadores.items():
                    if isinstance(valor, (int, float)):
                        features_extras[indicador] = valor
            
            # Treinar o modelo com as features configuradas
            resultado = self.ml_predictor.train(
                par, 
                self.historico_precos[par], 
                volumes, 
                force_retrain=force_retrain,
                features_extras=features_extras
            )
            
            if resultado.get('retrained', False):
                print(f"✅ Modelo para {par} treinado com acurácia de {resultado.get('accuracy', 0):.2%}")
                if 'feature_importance' in resultado:
                    print("📊 Importância das features:")
                    for feature, importance in resultado['feature_importance'].items():
                        print(f"   - {feature}: {importance:.2%}")
            return resultado
        except Exception as e:
            print(f"⚠️ Erro ao treinar modelo para {par}: {e}")
            return {"error": str(e)}
    
    def analisar_mercado(self, preco_atual, dados_24h, medias, par=None):
        """Análise profissional do mercado"""
        # Suporte para multiativo: usa histórico correto
        historico = self.historico_precos[par] if par else self.historico_precos[PAR]
        if len(historico) < 26:
            return "COLETANDO", f"Coletando dados... ({len(historico)}/26)"
        indicadores = self.calcular_indicadores(historico)
        if not indicadores:
            return "AGUARDAR", "Indicadores insuficientes"
        
        # Usar ML para previsão se disponível
        ml_signal = "NEUTRO"
        ml_confidence = 0.0
        
        if self.usar_ml and hasattr(self, 'ml_predictor') and len(historico) >= 100:
            try:
                # Treinar modelo se necessário
                if par not in self.ml_predictor.models:
                    self.treinar_modelo_ml(par)
                
                # Fazer previsão
                volumes = self.historico_volumes.get(par, None)
                if volumes and len(volumes) != len(historico):
                    volumes = None
                    
                prediction = self.ml_predictor.predict(par, historico, volumes)
                
                if 'error' not in prediction:
                    ml_signal = prediction.get('signal', 'NEUTRO')
                    ml_confidence = prediction.get('confidence', 0.0)
                    
                    print(f"🧠 ML Previsão: {ml_signal} (confiança: {ml_confidence:.2%})")
            except Exception as e:
                print(f"⚠️ Erro na previsão ML: {e}")
        
        # Se já tem posição aberta, só analisa para venda
        if self.posicao_aberta.get(par, False):
            condicoes_venda = 0
            motivos_venda = []
            
            # MODO RECUPERAÇÃO: Se teve prejuízo, seja mais conservador na venda
            modo_recuperacao = self.lucro_hoje < -0.01
            limite_venda = 5 if modo_recuperacao else 4  # Mais difícil vender em recuperação
            
            if modo_recuperacao:
                motivos_venda.append("MODO RECUPERAÇÃO - Aguardando lucro maior")
            
            # Adicionar sinal ML se disponível
            if ml_signal == "VENDA" and ml_confidence > 0.7:
                condicoes_venda += 2
                motivos_venda.append(f"ML recomenda venda (confiança: {ml_confidence:.2%})")
            
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
            
            # Adicionar sinal ML se disponível
            if ml_signal == "COMPRA" and ml_confidence > 0.7:
                condicoes_compra += 2
                motivos_compra.append(f"ML recomenda compra (confiança: {ml_confidence:.2%})")
            
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

    def executar_compra(self, preco_atual, par, motivo=""):
        resultado = executar_compra(self, preco_atual, par)
        if resultado:
            trade_data = {
                'symbol': par,
                'position_type': 'LONG',
                'entry_price': self.precos_entrada.get(par, 0),
                'quantity': self.quantidades_compradas.get(par, 0),
                'entry_time': datetime.now(),
                'stop_loss': self.stop_loss.get(par, 0),
                'take_profit': self.take_profit.get(par, 0),
                'strategy_used': 'analisar_mercado',
                'confidence': motivo.count('ML recomenda'), # Exemplo simples de confiança
                'is_simulation': MODO_SIMULACAO,
                'notes': motivo
            }
            self.db_manager.save_trade(trade_data)
        return resultado

    def executar_venda(self, preco_atual, par, motivo=""):
        preco_entrada = self.precos_entrada.get(par, 0)
        quantidade = self.quantidades_compradas.get(par, 0)
        resultado = executar_venda(self, preco_atual, par)
        if resultado:
            pnl = (preco_atual - preco_entrada) * quantidade if preco_entrada > 0 else 0
            pnl_pct = (pnl / (preco_entrada * quantidade)) * 100 if preco_entrada > 0 and quantidade > 0 else 0
            
            trade_data = {
                'symbol': par,
                'exit_price': preco_atual,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'exit_time': datetime.now(),
                'exit_reason': motivo
            }
            # Aqui precisaríamos de uma forma de atualizar o trade aberto, não criar um novo.
            # Isso será melhorado com o PortfolioManager. Por agora, vamos logar um evento.
            self.db_manager.log("INFO", "TradingBot", f"Venda executada para {par} com PnL de ${pnl:.2f}. Motivo: {motivo}")
        return resultado

    def verificar_stop_loss_take_profit(self, preco_atual, par):
        """Verifica se deve fechar posição por SL ou TP para um par específico"""
        if not self.posicao_aberta.get(par, False):
            return False
        
        # Obter preço de entrada para o par específico
        preco_entrada = self.precos_entrada.get(par, 0)
        if preco_entrada <= 0:
            return False
            
        take_profit_pct = STOP_LOSS_PCT * RELACAO_RISCO_RETORNO
        stop_loss = preco_entrada * (1 - STOP_LOSS_PCT)
        take_profit = preco_entrada * (1 + take_profit_pct)
        
        if preco_atual <= stop_loss:
            print(f"\n🛑 STOP LOSS ATIVADO para {par}! Preço: ${preco_atual:.2f} <= ${stop_loss:.2f}")
            self.executar_venda(preco_atual, par, motivo="STOP_LOSS")
            self._salvar_estado()
            return True
        elif preco_atual >= take_profit:
            print(f"\n🎯 TAKE PROFIT ATIVADO para {par}! Preço: ${preco_atual:.2f} >= ${take_profit:.2f}")
            self.executar_venda(preco_atual, par, motivo="TAKE_PROFIT")
            self._salvar_estado()
            return True
        
        return False
    
    def exibir_status(self, par, preco_atual, dados_24h, medias, decisao, motivo):
        """Exibe status atual do bot"""
        preco_str = f"${preco_atual:.2f}" if preco_atual is not None else "Preço indisponível"
        print(f"\n📈 {par} = {preco_str}")

        if dados_24h:
            volume_str = f"${dados_24h['quoteVolume']:,.0f}" if dados_24h.get('quoteVolume') is not None else "Volume indisponível"
            change_str = f"{dados_24h['priceChangePercent']:+.2f}%" if dados_24h.get('priceChangePercent') is not None else "Variação indisponível"
            print(f"📊 Volume 24h: {volume_str} USDT")
            print(f"📈 24h: {change_str}")

        if medias:
            ma7_str = f"${medias['MA7']:.2f}" if medias.get('MA7') is not None else "N/A"
            ma25_str = f"${medias['MA25']:.2f}" if medias.get('MA25') is not None else "N/A"
            ma99_str = f"${medias['MA99']:.2f}" if medias.get('MA99') is not None else "N/A"
            print(f"📅 MA7: {ma7_str} | MA25: {ma25_str} | MA99: {ma99_str}")

        # Status da posição
        if self.posicao_aberta.get(par, False):
            quantidade = self.quantidades_compradas.get(par, 0)
            preco_entrada = self.precos_entrada.get(par, 0)
            valor_investido = quantidade * preco_entrada
            valor_atual = quantidade * preco_atual
            pnl = valor_atual - valor_investido  # Lucro/perda em dólares
            pnl_pct = (pnl / valor_investido) * 100 if valor_investido > 0 else 0

            print(f"💹 POSIÇÃO ABERTA: {quantidade:.6f} {par.replace(self.moeda_base, '')} @ ${preco_entrada:.2f}")
            print(f"💰 Valor Investido: ${valor_investido:.2f} | Valor Atual: ${valor_atual:.2f}")
            if pnl > 0:
                print(f"🟢 P&L: +${pnl:.2f} ({pnl_pct:+.2f}%)")
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
    
    def atualizar_dados_mercado(self, par, preco_atual, volume_24h=None):
        """Atualiza os dados de mercado com o preço atual e volume"""
        self.historico_precos[par].append(preco_atual)
        
        # Atualizar histórico de volumes se disponível (para ML)
        if volume_24h is not None and par in self.historico_volumes:
            self.historico_volumes[par].append(volume_24h)
            # Manter o mesmo tamanho que o histórico de preços
            if len(self.historico_volumes[par]) > len(self.historico_precos[par]):
                self.historico_volumes[par] = self.historico_volumes[par][-len(self.historico_precos[par]):]
        
        # Manter apenas os últimos 500 preços para ML (mais dados para treinamento)
        if len(self.historico_precos[par]) > 500:
            self.historico_precos[par] = self.historico_precos[par][-500:]
            if par in self.historico_volumes and len(self.historico_volumes[par]) > 0:
                self.historico_volumes[par] = self.historico_volumes[par][-500:]
        
        # Verificar se é hora de treinar o modelo ML
        if self.usar_ml and hasattr(self, 'ml_predictor'):
            tempo_atual = time.time()
            if tempo_atual - self.ultimo_treino_ml > self.intervalo_treino_ml and len(self.historico_precos[par]) >= 200:
                print(f"🧠 Treinando modelo ML para {par}...")
                self.treinar_modelo_ml(par)
                self.ultimo_treino_ml = tempo_atual
                
    async def run(self):
        """Loop principal do bot - multiativo e multiestratégia"""
        import requests
        async with AsyncAPIHandler() as api:
            while True:
                try:
                    # Atualizar pares de negociação se a seleção automática estiver ativada
                    if self.usar_selecao_automatica:
                        self._atualizar_pares_negociacao()

                    # --- Otimização aqui: buscar todos os dados em paralelo ---
                    tasks = [api.get_price(p) for p in self.pares]
                    tasks += [api.get_24h_ticker(p) for p in self.pares]
                    tasks += [api.get_klines(p, "1d", 100) for p in self.pares]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Separar os resultados
                    num_pares = len(self.pares)
                    precos = dict(zip(self.pares, results[0:num_pares]))
                    tickers_24h = dict(zip(self.pares, results[num_pares:num_pares*2]))
                    candles_data = dict(zip(self.pares, results[num_pares*2:num_pares*3]))
                    # ---------------------------------------------------------

                    for par in self.pares:
                        preco_atual = precos.get(par)
                        dados_24h = tickers_24h.get(par)
                        candles = candles_data.get(par)

                        if not preco_atual or isinstance(preco_atual, Exception):
                            print(f"⚠️ Erro ao obter preço de {par}: {preco_atual}")
                            continue

                        # Log para verificar os dados de candles
                        print(f"📊 Dados de candles para {par}: {candles[:5] if candles else 'Nenhum dado'}")

                        # Atualizar histórico
                        self.atualizar_dados_mercado(par, preco_atual, dados_24h.get('quoteVolume') if dados_24h and not isinstance(dados_24h, Exception) else None)

                        # Obter médias móveis com verificação
                        medias = calcular_medias_moveis(candles) if candles and not isinstance(candles, Exception) else None
                        if medias is None:
                            print(f"⚠️ Não foi possível calcular médias móveis para {par}. Continuando...")
                            continue                  
                        
                        preco_atual = precos.get(par)
                        dados_24h = tickers_24h.get(par)
                        candles = candles_data.get(par)

                        if not preco_atual or isinstance(preco_atual, Exception):
                            print(f"⚠️ Erro ao obter preço de {par}: {preco_atual}")
                            continue

                        # Adicionar log para inspecionar candles
                        print(f"📊 Dados de candles para {par}: {candles[:5] if candles else 'Nenhum dado'}")

                        # Atualizar histórico
                        self.atualizar_dados_mercado(par, preco_atual, dados_24h.get('quoteVolume') if dados_24h and not isinstance(dados_24h, Exception) else None)

                        # Obter médias móveis com verificação
                        medias = calcular_medias_moveis(candles) if candles and not isinstance(candles, Exception) else None
                        if medias is None:
                            print(f"⚠️ Não foi possível calcular médias móveis para {par}. Continuando...")
                            continue
                    await asyncio.sleep(INTERVALO)

                except KeyboardInterrupt:
                    print("\n🛑 Bot interrompido pelo usuário")
                    break
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Erro de conexão com a API: {e}")
                    self.db_manager.log("ERROR", "API", f"Erro de conexão: {e}")
                    await asyncio.sleep(INTERVALO * 2)
                except Exception as e:
                    print(f"⚠️ Erro inesperado: {e}")
                    self.db_manager.log("CRITICAL", "TradingBot", f"Erro inesperado no loop principal: {e}")
                    await asyncio.sleep(INTERVALO)

def main():
    # Inicializar o bot com as configurações do config.py
    bot = TradingBot(
        pares=None,  # Usar os pares padrão do config.py ou os selecionados automaticamente
        estrategias=None,  # Usar a estratégia padrão do config.py
        capital_inicial=CAPITAL_INICIAL,
        moeda_base=MOEDA_BASE,
        usar_ml=USAR_ML,
        usar_selecao_automatica=USAR_SELECAO_AUTOMATICA
    )
    asyncio.run(bot.run())

if __name__ == "__main__":
    main()

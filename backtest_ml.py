import os
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from config import (
    CAPITAL_INICIAL, STOP_LOSS_PCT, TAKE_PROFIT_PCT, 
    MAX_TRADES_DIA, TAXA_BINANCE, USAR_ML, ML_CONFIANCA_MIN,
    ML_FEATURES, ML_TIMEFRAMES, ML_JANELA_PREVISAO, ML_MODELOS_DIR
)
from core.ml_predictor import MLPredictor
from core.estrategias import calcular_rsi, calcular_macd, calcular_ema, calcular_medias_moveis

class BacktestML:
    def __init__(self, dados_historicos, capital_inicial=CAPITAL_INICIAL, usar_ml=True):
        self.dados = dados_historicos
        self.capital_inicial = capital_inicial
        self.capital_atual = capital_inicial
        self.posicao_aberta = False
        self.preco_entrada = 0
        self.quantidade = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trades = []
        self.trades_vencedores = 0
        self.trades_perdedores = 0
        self.lucro_total = 0
        self.maior_drawdown = 0
        self.capital_maximo = capital_inicial
        self.historico_capital = []
        self.usar_ml = usar_ml
        self.ml_confianca_min = ML_CONFIANCA_MIN
        
        # Inicializar preditor ML
        if self.usar_ml:
            try:
                self.ml_predictor = MLPredictor(
                    modelos_dir=ML_MODELOS_DIR,
                    features=ML_FEATURES,
                    timeframes=ML_TIMEFRAMES,
                    janela_previsao=ML_JANELA_PREVISAO
                )
                print(f"🧠 Machine Learning ativado para backtest")
            except Exception as e:
                print(f"⚠️ Erro ao inicializar ML: {e}")
                self.usar_ml = False
    
    def preparar_dados(self):
        """Prepara os dados para o backtest"""
        # Converter para DataFrame se for uma lista
        if isinstance(self.dados, list):
            self.dados = pd.DataFrame(self.dados)
        
        # Garantir que temos as colunas necessárias
        colunas_necessarias = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for coluna in colunas_necessarias:
            if coluna not in self.dados.columns:
                raise ValueError(f"Coluna {coluna} não encontrada nos dados")
        
        # Ordenar por timestamp
        self.dados = self.dados.sort_values('timestamp')
        
        # Calcular indicadores técnicos
        precos = self.dados['close'].values
        self.dados['rsi'] = calcular_rsi(precos)
        macd, sinal, hist = calcular_macd(precos)
        self.dados['macd'] = macd
        self.dados['macd_sinal'] = sinal
        self.dados['macd_hist'] = hist
        self.dados['ema_12'] = calcular_ema(precos, 12)
        self.dados['ema_26'] = calcular_ema(precos, 26)
        
        # Calcular Bollinger Bands
        self.dados['sma_20'] = self.dados['close'].rolling(window=20).mean()
        self.dados['std_20'] = self.dados['close'].rolling(window=20).std()
        self.dados['banda_superior'] = self.dados['sma_20'] + (2 * self.dados['std_20'])
        self.dados['banda_inferior'] = self.dados['sma_20'] - (2 * self.dados['std_20'])
        
        # Calcular variação percentual
        self.dados['variacao_pct'] = self.dados['close'].pct_change() * 100
        
        # Calcular volatilidade (ATR simplificado)
        self.dados['atr'] = self.dados['high'] - self.dados['low']
        
        # Remover NaN
        self.dados = self.dados.dropna()
        
        # Treinar modelo ML com os primeiros 70% dos dados
        if self.usar_ml:
            self.treinar_modelo_ml()
        
        return self.dados
    
    def treinar_modelo_ml(self):
        """Treina o modelo ML com parte dos dados históricos"""
        if not self.usar_ml or not hasattr(self, 'ml_predictor'):
            return
        
        # Usar 70% dos dados para treinamento
        n_treino = int(len(self.dados) * 0.7)
        dados_treino = self.dados.iloc[:n_treino]
        
        precos = dados_treino['close'].values
        volumes = dados_treino['volume'].values
        
        # Criar features extras para o treinamento
        features_extras = {
            'rsi': dados_treino['rsi'].values,
            'macd': dados_treino['macd'].values,
            'macd_hist': dados_treino['macd_hist'].values,
            'ema_diff': dados_treino['ema_12'].values - dados_treino['ema_26'].values,
            'bollinger_pos': (dados_treino['close'].values - dados_treino['banda_inferior'].values) / 
                            (dados_treino['banda_superior'].values - dados_treino['banda_inferior'].values),
            'volatilidade': dados_treino['atr'].values / dados_treino['close'].values
        }
        
        try:
            resultado = self.ml_predictor.train(
                'BACKTEST', 
                precos, 
                volumes, 
                force_retrain=True,
                features_extras=features_extras
            )
            
            if resultado.get('retrained', False):
                print(f"✅ Modelo treinado com acurácia de {resultado.get('accuracy', 0):.2%}")
                if 'feature_importance' in resultado:
                    print("📊 Importância das features:")
                    for feature, importance in resultado['feature_importance'].items():
                        print(f"   - {feature}: {importance:.2%}")
            return resultado
        except Exception as e:
            print(f"⚠️ Erro ao treinar modelo: {e}")
            return {"error": str(e)}
    
    def analisar_mercado(self, idx):
        """Analisa o mercado e retorna decisão de compra/venda"""
        if idx < 26:
            return "AGUARDAR"
        
        # Obter dados até o índice atual (simulando dados disponíveis até o momento)
        dados_atuais = self.dados.iloc[:idx+1]
        preco_atual = dados_atuais.iloc[-1]['close']
        
        # Obter indicadores do último candle
        rsi = dados_atuais.iloc[-1]['rsi']
        macd = dados_atuais.iloc[-1]['macd']
        macd_sinal = dados_atuais.iloc[-1]['macd_sinal']
        banda_superior = dados_atuais.iloc[-1]['banda_superior']
        banda_inferior = dados_atuais.iloc[-1]['banda_inferior']
        
        # Usar ML para previsão se disponível
        ml_signal = "NEUTRO"
        ml_confidence = 0.0
        
        if self.usar_ml and hasattr(self, 'ml_predictor'):
            try:
                # Preparar dados para previsão
                precos = dados_atuais['close'].values[-100:]
                volumes = dados_atuais['volume'].values[-100:]
                
                # Criar features extras para a previsão
                features_extras = {
                    'rsi': dados_atuais['rsi'].values[-100:],
                    'macd': dados_atuais['macd'].values[-100:],
                    'macd_hist': dados_atuais['macd_hist'].values[-100:],
                    'ema_diff': dados_atuais['ema_12'].values[-100:] - dados_atuais['ema_26'].values[-100:],
                    'bollinger_pos': (dados_atuais['close'].values[-100:] - dados_atuais['banda_inferior'].values[-100:]) / 
                                    (dados_atuais['banda_superior'].values[-100:] - dados_atuais['banda_inferior'].values[-100:]),
                    'volatilidade': dados_atuais['atr'].values[-100:] / dados_atuais['close'].values[-100:]
                }
                
                prediction = self.ml_predictor.predict(
                    'BACKTEST', 
                    precos, 
                    volumes,
                    features_extras=features_extras
                )
                
                if 'error' not in prediction:
                    ml_signal = prediction.get('signal', 'NEUTRO')
                    ml_confidence = prediction.get('confidence', 0.0)
            except Exception as e:
                print(f"⚠️ Erro na previsão ML: {e}")
        
        # Lógica de decisão combinando indicadores técnicos e ML
        if not self.posicao_aberta:
            # Condições de compra
            if ml_signal == "COMPRA" and ml_confidence > self.ml_confianca_min:
                # Alta confiança do ML para compra
                return "COMPRA"
            elif rsi < 30 and preco_atual < banda_inferior:
                # Condição técnica tradicional
                if ml_signal != "VENDA" or ml_confidence < 0.6:
                    return "COMPRA"
        else:
            # Já tem posição aberta, verificar condições de venda
            stop_loss = self.preco_entrada * (1 - STOP_LOSS_PCT)
            take_profit = self.preco_entrada * (1 + TAKE_PROFIT_PCT)
            
            if preco_atual <= stop_loss:
                return "VENDA_STOP"
            elif preco_atual >= take_profit:
                return "VENDA_PROFIT"
            elif ml_signal == "VENDA" and ml_confidence > 0.75:
                return "VENDA_ML"
            elif rsi > 70 and preco_atual > banda_superior:
                # Condição técnica tradicional
                if ml_signal != "COMPRA" or ml_confidence < 0.6:
                    return "VENDA_TECNICA"
        
        return "AGUARDAR"
    
    def executar_compra(self, preco, idx, motivo=""):
        """Executa uma ordem de compra"""
        if self.posicao_aberta:
            return False
        
        # Calcular quantidade a comprar (90% do capital disponível)
        valor_compra = self.capital_atual * 0.9
        self.quantidade = valor_compra / preco
        
        # Descontar taxa
        self.quantidade = self.quantidade * (1 - TAXA_BINANCE/2)
        
        # Registrar compra
        self.posicao_aberta = True
        self.preco_entrada = preco
        self.stop_loss = preco * (1 - STOP_LOSS_PCT)
        self.take_profit = preco * (1 + TAKE_PROFIT_PCT)
        
        # Registrar trade
        timestamp = self.dados.iloc[idx]['timestamp']
        data_hora = datetime.fromtimestamp(timestamp / 1000) if timestamp > 1e10 else datetime.fromtimestamp(timestamp)
        
        trade = {
            'tipo': 'COMPRA',
            'preco': preco,
            'quantidade': self.quantidade,
            'valor': self.quantidade * preco,
            'timestamp': timestamp,
            'data_hora': data_hora.strftime('%Y-%m-%d %H:%M:%S'),
            'motivo': motivo
        }
        
        self.trades.append(trade)
        return True
    
    def executar_venda(self, preco, idx, motivo=""):
        """Executa uma ordem de venda"""
        if not self.posicao_aberta:
            return False
        
        # Calcular resultado
        valor_venda = self.quantidade * preco
        valor_venda = valor_venda * (1 - TAXA_BINANCE/2)  # Descontar taxa
        valor_compra = self.quantidade * self.preco_entrada
        lucro = valor_venda - valor_compra
        lucro_percentual = (preco / self.preco_entrada - 1) * 100
        
        # Atualizar capital
        self.capital_atual = self.capital_atual + lucro
        
        # Registrar resultado
        if lucro > 0:
            self.trades_vencedores += 1
        else:
            self.trades_perdedores += 1
        
        self.lucro_total += lucro
        
        # Atualizar drawdown
        if self.capital_atual > self.capital_maximo:
            self.capital_maximo = self.capital_atual
        drawdown_atual = (self.capital_maximo - self.capital_atual) / self.capital_maximo
        if drawdown_atual > self.maior_drawdown:
            self.maior_drawdown = drawdown_atual
        
        # Registrar trade
        timestamp = self.dados.iloc[idx]['timestamp']
        data_hora = datetime.fromtimestamp(timestamp / 1000) if timestamp > 1e10 else datetime.fromtimestamp(timestamp)
        
        trade = {
            'tipo': 'VENDA',
            'preco': preco,
            'quantidade': self.quantidade,
            'valor': valor_venda,
            'lucro': lucro,
            'lucro_percentual': lucro_percentual,
            'timestamp': timestamp,
            'data_hora': data_hora.strftime('%Y-%m-%d %H:%M:%S'),
            'motivo': motivo
        }
        
        self.trades.append(trade)
        
        # Resetar posição
        self.posicao_aberta = False
        self.preco_entrada = 0
        self.quantidade = 0
        self.stop_loss = 0
        self.take_profit = 0
        
        return True
    
    def executar_backtest(self):
        """Executa o backtest completo"""
        # Preparar dados
        self.preparar_dados()
        
        # Inicializar histórico de capital
        self.historico_capital = [self.capital_atual]
        
        # Loop pelos dados
        for idx in range(len(self.dados)):
            # Registrar capital atual
            self.historico_capital.append(self.capital_atual)
            
            # Obter preço atual
            preco_atual = self.dados.iloc[idx]['close']
            
            # Analisar mercado
            decisao = self.analisar_mercado(idx)
            
            # Executar decisão
            if decisao == "COMPRA" and not self.posicao_aberta:
                self.executar_compra(preco_atual, idx, motivo="Sinal de compra")
            elif decisao.startswith("VENDA") and self.posicao_aberta:
                self.executar_venda(preco_atual, idx, motivo=decisao)
            elif self.posicao_aberta:
                # Verificar stop loss e take profit
                if preco_atual <= self.stop_loss:
                    self.executar_venda(preco_atual, idx, motivo="Stop Loss")
                elif preco_atual >= self.take_profit:
                    self.executar_venda(preco_atual, idx, motivo="Take Profit")
        
        # Fechar posição aberta no final do backtest
        if self.posicao_aberta:
            ultimo_idx = len(self.dados) - 1
            ultimo_preco = self.dados.iloc[ultimo_idx]['close']
            self.executar_venda(ultimo_preco, ultimo_idx, motivo="Fim do backtest")
        
        # Calcular métricas
        self.calcular_metricas()
        
        return {
            'capital_final': self.capital_atual,
            'lucro_total': self.lucro_total,
            'retorno_percentual': (self.capital_atual / self.capital_inicial - 1) * 100,
            'trades_total': self.trades_vencedores + self.trades_perdedores,
            'trades_vencedores': self.trades_vencedores,
            'trades_perdedores': self.trades_perdedores,
            'taxa_acerto': self.trades_vencedores / (self.trades_vencedores + self.trades_perdedores) if (self.trades_vencedores + self.trades_perdedores) > 0 else 0,
            'maior_drawdown': self.maior_drawdown * 100,
            'historico_capital': self.historico_capital,
            'trades': self.trades
        }
    
    def calcular_metricas(self):
        """Calcula métricas adicionais de desempenho"""
        # Calcular lucros e perdas médias
        lucros = [trade['lucro'] for trade in self.trades if 'lucro' in trade and trade['lucro'] > 0]
        perdas = [trade['lucro'] for trade in self.trades if 'lucro' in trade and trade['lucro'] < 0]
        
        self.lucro_medio = np.mean(lucros) if lucros else 0
        self.perda_media = np.mean(perdas) if perdas else 0
        
        # Calcular fator de lucro
        self.fator_lucro = abs(self.lucro_medio / self.perda_media) if self.perda_media != 0 else float('inf')
        
        # Calcular expectativa matemática
        self.expectativa = (self.trades_vencedores * self.lucro_medio + self.trades_perdedores * self.perda_media) / (self.trades_vencedores + self.trades_perdedores) if (self.trades_vencedores + self.trades_perdedores) > 0 else 0
        
        # Calcular Sharpe Ratio (simplificado)
        retornos_diarios = np.diff(self.historico_capital) / self.historico_capital[:-1]
        self.sharpe_ratio = np.mean(retornos_diarios) / np.std(retornos_diarios) * np.sqrt(252) if np.std(retornos_diarios) != 0 else 0
        
        return {
            'lucro_medio': self.lucro_medio,
            'perda_media': self.perda_media,
            'fator_lucro': self.fator_lucro,
            'expectativa': self.expectativa,
            'sharpe_ratio': self.sharpe_ratio
        }
    
    def plotar_resultados(self):
        """Plota os resultados do backtest"""
        plt.figure(figsize=(14, 10))
        
        # Plot 1: Preço e trades
        plt.subplot(2, 1, 1)
        plt.plot(self.dados['close'], label='Preço')
        
        # Marcar compras e vendas
        for trade in self.trades:
            if trade['tipo'] == 'COMPRA':
                plt.scatter(trade['timestamp'], trade['preco'], color='green', marker='^', s=100)
            elif trade['tipo'] == 'VENDA':
                plt.scatter(trade['timestamp'], trade['preco'], color='red', marker='v', s=100)
        
        plt.title('Preço e Trades')
        plt.ylabel('Preço')
        plt.legend()
        
        # Plot 2: Evolução do capital
        plt.subplot(2, 1, 2)
        plt.plot(self.historico_capital, label='Capital')
        plt.title('Evolução do Capital')
        plt.ylabel('Capital')
        plt.xlabel('Candles')
        plt.legend()
        
        plt.tight_layout()
        plt.savefig('backtest_resultados.png')
        plt.show()
    
    def imprimir_resultados(self):
        """Imprime os resultados do backtest"""
        print("="*50)
        print("📊 RESULTADOS DO BACKTEST")
        print("="*50)
        print(f"💰 Capital inicial: ${self.capital_inicial:.2f}")
        print(f"💰 Capital final: ${self.capital_atual:.2f}")
        print(f"📈 Retorno: {(self.capital_atual / self.capital_inicial - 1) * 100:.2f}%")
        print(f"📉 Maior drawdown: {self.maior_drawdown * 100:.2f}%")
        print(f"🔄 Total de trades: {self.trades_vencedores + self.trades_perdedores}")
        print(f"✅ Trades vencedores: {self.trades_vencedores}")
        print(f"❌ Trades perdedores: {self.trades_perdedores}")
        print(f"🎯 Taxa de acerto: {self.trades_vencedores / (self.trades_vencedores + self.trades_perdedores) * 100:.2f}% (com ML: {'✅' if self.usar_ml else '❌'})")
        print(f"💵 Lucro médio: ${self.lucro_medio:.2f}")
        print(f"💸 Perda média: ${self.perda_media:.2f}")
        print(f"📊 Fator de lucro: {self.fator_lucro:.2f}")
        print(f"📈 Expectativa: ${self.expectativa:.2f}")
        print(f"📊 Sharpe Ratio: {self.sharpe_ratio:.2f}")
        print("="*50)

# Função para carregar dados históricos
def carregar_dados_historicos(arquivo):
    """Carrega dados históricos de um arquivo CSV ou JSON"""
    if arquivo.endswith('.csv'):
        return pd.read_csv(arquivo)
    elif arquivo.endswith('.json'):
        with open(arquivo, 'r') as f:
            return json.load(f)
    else:
        raise ValueError("Formato de arquivo não suportado. Use CSV ou JSON.")

# Função principal
def main(arquivo_dados=None):
    # Verificar se o arquivo de dados existe
    if arquivo_dados is None:
        arquivo_dados = 'dados_historicos.csv'
    
    if not os.path.exists(arquivo_dados):
        print(f"❌ Arquivo {arquivo_dados} não encontrado.")
        print("Por favor, crie um arquivo de dados históricos com as colunas: timestamp, open, high, low, close, volume")
        print("Você pode usar o script coletar_dados_historicos.py para obter dados da Binance.")
        return
    
    # Carregar dados históricos
    dados = carregar_dados_historicos(arquivo_dados)
    print(f"📊 Dados carregados de {arquivo_dados}: {len(dados)} registros")
    
    # Executar backtest com e sem ML para comparação
    print("🧠 Executando backtest com Machine Learning...")
    backtest_ml = BacktestML(dados, usar_ml=True)
    resultados_ml = backtest_ml.executar_backtest()
    backtest_ml.imprimir_resultados()
    backtest_ml.plotar_resultados()
    
    print("\n🔄 Executando backtest sem Machine Learning para comparação...")
    backtest_sem_ml = BacktestML(dados, usar_ml=False)
    resultados_sem_ml = backtest_sem_ml.executar_backtest()
    backtest_sem_ml.imprimir_resultados()
    
    # Comparar resultados
    print("\n📊 COMPARAÇÃO DE RESULTADOS")
    print("="*50)
    print(f"📈 Retorno com ML: {(resultados_ml['capital_final'] / CAPITAL_INICIAL - 1) * 100:.2f}%")
    print(f"📈 Retorno sem ML: {(resultados_sem_ml['capital_final'] / CAPITAL_INICIAL - 1) * 100:.2f}%")
    print(f"🎯 Taxa de acerto com ML: {resultados_ml['taxa_acerto'] * 100:.2f}%")
    print(f"🎯 Taxa de acerto sem ML: {resultados_sem_ml['taxa_acerto'] * 100:.2f}%")
    print(f"📉 Drawdown com ML: {resultados_ml['maior_drawdown']:.2f}%")
    print(f"📉 Drawdown sem ML: {resultados_sem_ml['maior_drawdown']:.2f}%")
    print("="*50)
    
    # Salvar resultados em arquivo
    resultados = {
        'com_ml': {
            'capital_final': resultados_ml['capital_final'],
            'retorno_percentual': (resultados_ml['capital_final'] / CAPITAL_INICIAL - 1) * 100,
            'taxa_acerto': resultados_ml['taxa_acerto'] * 100,
            'maior_drawdown': resultados_ml['maior_drawdown'],
            'trades_total': resultados_ml['trades_total']
        },
        'sem_ml': {
            'capital_final': resultados_sem_ml['capital_final'],
            'retorno_percentual': (resultados_sem_ml['capital_final'] / CAPITAL_INICIAL - 1) * 100,
            'taxa_acerto': resultados_sem_ml['taxa_acerto'] * 100,
            'maior_drawdown': resultados_sem_ml['maior_drawdown'],
            'trades_total': resultados_sem_ml['trades_total']
        }
    }
    
    with open('resultados_backtest.json', 'w') as f:
        json.dump(resultados, f, indent=4)
    
    print(f"✅ Resultados salvos em resultados_backtest.json")
    
    return resultados

if __name__ == "__main__":
    main()
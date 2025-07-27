import csv
from core.estrategias import calcular_rsi, calcular_macd, calcular_ema, calcular_medias_moveis
import numpy as np
from capital_log import CapitalLog
def calcular_bollinger_bands(precos, periodo=20, num_std=2):
    if len(precos) < periodo:
        return None, None, None
    arr = np.array(precos[-periodo:])
    sma = np.mean(arr)
    std = np.std(arr)
    upper = sma + num_std * std
    lower = sma - num_std * std
    return sma, upper, lower
from config import CAPITAL_INICIAL, RELACAO_RISCO_RETORNO

# Exemplo: use um arquivo CSV com colunas: timestamp,open,high,low,close,volume
ARQUIVO_DADOS = 'historico.csv'  # Substitua pelo seu arquivo de dados históricos
PAR = 'BTCUSDT'

class BacktestBot:
    def __init__(self, precos, stop_loss_pct=0.02, take_profit_pct=0.05, rsi_period=14, macd_fast=12, macd_slow=26, bb_period=20, bb_std=2, taxa=0.002, slippage=0.0005):
        self.capital = CAPITAL_INICIAL
        self.posicao_aberta = False
        self.preco_entrada = 0
        self.quantidade = 0
        self.trades_ganhos = 0
        self.trades_perdidos = 0
        self.trades_total = 0
        self.precos = precos
        self.historico_precos = []
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.log_trades = []
        self.taxa = taxa  # taxa total (ex: 0.002 = 0.2%)
        self.slippage = slippage  # slippage percentual (ex: 0.0005 = 0.05%)
        self.log_manager = CapitalLog("capital_log_backtest.csv")

    def run(self):
        for preco in self.precos:
            self.historico_precos.append(preco)
            if len(self.historico_precos) < max(self.rsi_period, self.macd_slow, self.bb_period):
                continue
            indicadores = self.calcular_indicadores(self.historico_precos)
            sma, upper, lower = calcular_bollinger_bands(self.historico_precos, self.bb_period, self.bb_std)
            if not self.posicao_aberta:
                # Exemplo: compra se preço fechar abaixo da banda inferior e RSI < 30
                if indicadores['rsi'] < 30 and preco < lower:
                    self.executar_compra(preco)
            else:
                stop_loss = self.preco_entrada * (1 - self.stop_loss_pct)
                take_profit = self.preco_entrada * (1 + self.take_profit_pct)
                # Exemplo: venda se preço fechar acima da banda superior ou atingir SL/TP
                if preco >= upper or preco <= stop_loss or preco >= take_profit:
                    self.executar_venda(preco)
        # Fecha posição aberta ao final
        if self.posicao_aberta:
            self.executar_venda(self.precos[-1])
        self.resultado()

    def calcular_indicadores(self, precos):
        rsi = calcular_rsi(precos, self.rsi_period)
        macd = calcular_macd(precos)  # Supondo que calcular_macd já use os períodos padrão
        ema_12 = calcular_ema(precos, self.macd_fast)
        ema_26 = calcular_ema(precos, self.macd_slow)
        return {'rsi': rsi, 'macd': macd, 'ema_12': ema_12, 'ema_26': ema_26}

    def executar_compra(self, preco):
        preco_ajustado = preco * (1 + self.slippage)
        taxa_compra = self.capital * self.taxa / 2  # metade na compra
        valor_liquido = self.capital - taxa_compra
        self.preco_entrada = preco_ajustado
        self.quantidade = valor_liquido / preco_ajustado
        self.posicao_aberta = True
        self.trades_total += 1
        self.capital -= taxa_compra  # desconta taxa de compra
        self.log_trades.append({
            'tipo': 'compra',
            'preco': preco_ajustado,
            'capital_antes': self.capital + taxa_compra,
            'quantidade': self.quantidade,
            'taxa': taxa_compra,
            'slippage': self.slippage
        })
        self.log_manager.registrar_trade(
            "COMPRA_BACKTEST",
            preco_ajustado, self.capital + taxa_compra, self.capital,
            0, 0, f"Taxa: {taxa_compra:.2f} | Slippage: {self.slippage*100:.2f}%"
        )

    def executar_venda(self, preco):
        preco_ajustado = preco * (1 - self.slippage)
        valor_bruto = self.quantidade * preco_ajustado
        taxa_venda = valor_bruto * self.taxa / 2  # metade na venda
        valor_liquido = valor_bruto - taxa_venda
        lucro = valor_liquido - (self.quantidade * self.preco_entrada)
        if lucro > 0:
            self.trades_ganhos += 1
        else:
            self.trades_perdidos += 1
        self.capital += valor_liquido
        self.log_trades.append({
            'tipo': 'venda',
            'preco': preco_ajustado,
            'capital_depois': self.capital,
            'lucro': lucro,
            'win': lucro > 0,
            'taxa': taxa_venda,
            'slippage': self.slippage
        })
        self.log_manager.registrar_trade(
            "VENDA_BACKTEST",
            preco_ajustado, valor_bruto, self.capital,
            lucro, 0, f"Taxa: {taxa_venda:.2f} | Slippage: {self.slippage*100:.2f}%"
        )
        self.posicao_aberta = False
        self.quantidade = 0

    def resultado(self):
        win_rate = (self.trades_ganhos / self.trades_total) * 100 if self.trades_total > 0 else 0
        print(f'Capital final: ${self.capital:.2f}')
        print(f'Trades ganhos: {self.trades_ganhos}')
        print(f'Trades perdidos: {self.trades_perdidos}')
        print(f'Win rate: {win_rate:.2f}%')
        print(f'Taxa simulada: {self.taxa*100:.2f}% | Slippage simulado: {self.slippage*100:.2f}%')
        print('\nLog detalhado de trades:')
        for i, log in enumerate(self.log_trades):
            if log['tipo'] == 'compra':
                print(f"{i+1}. COMPRA  | Preço: {log['preco']:.2f} | Qtd: {log['quantidade']:.6f} | Capital antes: {log['capital_antes']:.2f} | Taxa: {log['taxa']:.2f} | Slippage: {log['slippage']*100:.2f}%")
            else:
                print(f"{i+1}. VENDA   | Preço: {log['preco']:.2f} | Lucro: {log['lucro']:.2f} | Capital após: {log['capital_depois']:.2f} | {'WIN' if log['win'] else 'LOSS'} | Taxa: {log['taxa']:.2f} | Slippage: {log['slippage']*100:.2f}%")


def carregar_precos_csv(arquivo):
    precos = []
    with open(arquivo, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            precos.append(float(row['close']))
    return precos

def otimizar_parametros(precos):
    melhores = None
    melhor_capital = -float('inf')
    print('Testando combinações de parâmetros...')
    for stop_loss in [0.01, 0.02, 0.03]:
        for take_profit in [0.02, 0.04, 0.06]:
            for rsi_period in [10, 14, 20]:
                bot = BacktestBot(precos, stop_loss_pct=stop_loss, take_profit_pct=take_profit, rsi_period=rsi_period)
                bot.run()
                if bot.capital > melhor_capital:
                    melhor_capital = bot.capital
                    melhores = (stop_loss, take_profit, rsi_period)
    print(f'\nMelhores parâmetros: Stop Loss={melhores[0]*100:.1f}%, Take Profit={melhores[1]*100:.1f}%, RSI={melhores[2]}')
    print(f'Capital final: ${melhor_capital:.2f}')

if __name__ == '__main__':
    precos = carregar_precos_csv(ARQUIVO_DADOS)
    print('1 - Rodar backtest padrão')
    print('2 - Otimizar parâmetros')
    escolha = input('Escolha uma opção: ')
    if escolha == '2':
        otimizar_parametros(precos)
    else:
        bot = BacktestBot(precos)
        bot.run()

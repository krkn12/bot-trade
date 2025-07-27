from datetime import datetime, date
import csv
import os
from config import CAPITAL_INICIAL, RISCO_POR_TRADE, META_LUCRO_DIARIO, MAX_TRADES_DIA
from core.risco import calcular_tamanho_posicao

class GestorCapital:
    def __init__(self):
        self.capital_atual = CAPITAL_INICIAL
        self.trades_hoje = 0
        self.lucro_hoje = 0.0
        self.data_hoje = date.today()
        self.arquivo_capital = "trading_log.csv"
        self.carregar_dados()
    
    def carregar_dados(self):
        """Carrega dados do arquivo de tracking"""
        if os.path.exists(self.arquivo_capital):
            try:
                with open(self.arquivo_capital, 'r', newline='') as file:
                    reader = csv.DictReader(file)
                    ultima_linha = None
                    for linha in reader:
                        ultima_linha = linha
                    
                    if ultima_linha:
                        data_arquivo = datetime.strptime(ultima_linha['Data'], '%Y-%m-%d').date()
                        
                        if data_arquivo == self.data_hoje:
                            # Mesmo dia, carregar dados
                            self.capital_atual = float(ultima_linha['Capital'])
                            self.trades_hoje = int(ultima_linha['Trades_Hoje'])
                            self.lucro_hoje = float(ultima_linha['Lucro_Hoje'])
                        else:
                            # Novo dia, resetar contadores
                            self.capital_atual = float(ultima_linha['Capital'])
                            self.trades_hoje = 0
                            self.lucro_hoje = 0.0
            except:
                pass
    
    def pode_fazer_trade(self):
        """Verifica se pode fazer mais trades hoje"""
        if self.trades_hoje >= MAX_TRADES_DIA:
            return False, f"Limite de {MAX_TRADES_DIA} trades diários atingido"
        
        if self.lucro_hoje >= (CAPITAL_INICIAL * META_LUCRO_DIARIO):
            return False, f"Meta de lucro diário atingida: ${self.lucro_hoje:.2f}"
        
        if self.capital_atual < 5.0:  # Capital mínimo
            return False, "Capital insuficiente para continuar trading"
        
        return True, "OK"
    
    def calcular_tamanho_posicao(self, preco_entrada, stop_loss):
        return calcular_tamanho_posicao(self.capital_atual, preco_entrada, stop_loss, RISCO_POR_TRADE)
    
    def registrar_trade(self, tipo, preco, valor, resultado=None):
        """Registra um trade e atualiza capital"""
        self.trades_hoje += 1
        
        if resultado:  # Trade fechado
            if resultado > 0:
                self.capital_atual += resultado
                self.lucro_hoje += resultado
            else:
                self.capital_atual += resultado  # resultado é negativo
                self.lucro_hoje += resultado
        
        # Salvar no arquivo
        self.salvar_dados()
        
        return {
            'capital_atual': self.capital_atual,
            'trades_hoje': self.trades_hoje,
            'lucro_hoje': self.lucro_hoje,
            'pode_continuar': self.pode_fazer_trade()[0]
        }
    
    def salvar_dados(self):
        """Salva dados no arquivo"""
        arquivo_existe = os.path.exists(self.arquivo_capital)
        
        with open(self.arquivo_capital, 'a', newline='') as file:
            fieldnames = ['Data', 'Capital', 'Trades_Hoje', 'Lucro_Hoje', 'ROI_Diario']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            if not arquivo_existe:
                writer.writeheader()
            
            roi_diario = (self.lucro_hoje / CAPITAL_INICIAL) * 100
            
            writer.writerow({
                'Data': self.data_hoje.strftime('%Y-%m-%d'),
                'Capital': f"{self.capital_atual:.2f}",
                'Trades_Hoje': self.trades_hoje,
                'Lucro_Hoje': f"{self.lucro_hoje:.2f}",
                'ROI_Diario': f"{roi_diario:.2f}%"
            })
    
    def get_status(self):
        """Retorna status atual do capital"""
        roi_total = ((self.capital_atual - CAPITAL_INICIAL) / CAPITAL_INICIAL) * 100
        roi_diario = (self.lucro_hoje / CAPITAL_INICIAL) * 100
        
        return {
            'capital_inicial': CAPITAL_INICIAL,
            'capital_atual': self.capital_atual,
            'lucro_total': self.capital_atual - CAPITAL_INICIAL,
            'lucro_hoje': self.lucro_hoje,
            'roi_total': roi_total,
            'roi_diario': roi_diario,
            'trades_hoje': self.trades_hoje,
            'trades_restantes': MAX_TRADES_DIA - self.trades_hoje,
            'meta_diaria': CAPITAL_INICIAL * META_LUCRO_DIARIO
        }

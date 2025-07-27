import csv
import os
from datetime import datetime

class LogManager:
    def __init__(self):
        self.arquivo_principal = "trading_log.csv"
        self.inicializar_arquivo()
    
    def inicializar_arquivo(self):
        """Inicializa o arquivo principal se não existir"""
        if not os.path.exists(self.arquivo_principal):
            with open(self.arquivo_principal, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Data/Hora", "Tipo", "Preço_BTC", "Ação", "Valor_Operacao", 
                    "Capital_Atual", "Lucro_Hoje", "ROI_Diario", "Observações"
                ])
    
    def registrar_trade(self, acao, preco, valor_operacao, capital_atual, lucro_hoje, roi_diario, observacoes=""):
        """Registra um trade no arquivo principal"""
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.arquivo_principal, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                agora, "TRADE", f"${preco:.2f}", acao.upper(), 
                f"${valor_operacao:.2f}", f"${capital_atual:.2f}", 
                f"${lucro_hoje:.2f}", f"{roi_diario:.1f}%", observacoes
            ])
    
    def registrar_status_diario(self, capital_atual, trades_hoje, lucro_hoje, roi_diario):
        """Registra status diário"""
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.arquivo_principal, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                agora, "STATUS", "-", f"TRADES_HOJE: {trades_hoje}", 
                "-", f"${capital_atual:.2f}", f"${lucro_hoje:.2f}", 
                f"{roi_diario:.1f}%", "Status diário"
            ])
    
    def registrar_alerta(self, preco, variacao, motivo):
        """Registra alertas de variação"""
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.arquivo_principal, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                agora, "ALERTA", f"${preco:.2f}", f"VARIAÇÃO: ${variacao:.2f}", 
                "-", "-", "-", "-", motivo
            ])
    
    def limpar_arquivos_antigos(self):
        """Remove arquivos CSV antigos desnecessários"""
        arquivos_para_remover = [
            "registro_trades.csv",
            "registro_trades_10usd.csv",
            "capital_tracking.csv"
        ]
        
        for arquivo in arquivos_para_remover:
            if os.path.exists(arquivo):
                try:
                    os.remove(arquivo)
                    print(f"✅ Arquivo antigo removido: {arquivo}")
                except:
                    print(f"⚠️ Não foi possível remover: {arquivo}")
    
    def get_resumo_hoje(self):
        """Retorna resumo dos trades de hoje"""
        if not os.path.exists(self.arquivo_principal):
            return {"trades": 0, "lucro": 0.0, "capital": 10.0}
        
        hoje = datetime.now().strftime("%Y-%m-%d")
        trades_hoje = 0
        ultimo_capital = 10.0
        ultimo_lucro = 0.0
        
        try:
            with open(self.arquivo_principal, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for linha in reader:
                    if linha["Data/Hora"].startswith(hoje) and linha["Tipo"] == "TRADE":
                        trades_hoje += 1
                        if linha["Capital_Atual"] != "-":
                            ultimo_capital = float(linha["Capital_Atual"].replace("$", ""))
                        if linha["Lucro_Hoje"] != "-":
                            ultimo_lucro = float(linha["Lucro_Hoje"].replace("$", ""))
        except:
            pass
        
        return {
            "trades": trades_hoje,
            "lucro": ultimo_lucro,
            "capital": ultimo_capital
        }

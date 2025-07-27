import csv
import os
from datetime import datetime, date

class CapitalLog:
    def __init__(self, arquivo="capital_log.csv"):
        self.arquivo = arquivo
        self._inicializar_arquivo()

    def _inicializar_arquivo(self):
        if not os.path.exists(self.arquivo):
            with open(self.arquivo, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Data/Hora", "Tipo", "Preço", "Ação", "Valor_Operacao",
                    "Capital_Atual", "Lucro_Hoje", "ROI_Diario", "Observações"
                ])

    def registrar_trade(self, acao, preco, valor_operacao, capital_atual, lucro_hoje, roi_diario, observacoes=""):
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.arquivo, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                agora, "TRADE", f"${preco:.2f}", acao.upper(),
                f"${valor_operacao:.2f}", f"${capital_atual:.2f}",
                f"${lucro_hoje:.2f}", f"{roi_diario:.1f}%", observacoes
            ])

    def registrar_status_diario(self, capital_atual, trades_hoje, lucro_hoje, roi_diario):
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.arquivo, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                agora, "STATUS", "-", f"TRADES_HOJE: {trades_hoje}",
                "-", f"${capital_atual:.2f}", f"${lucro_hoje:.2f}",
                f"{roi_diario:.1f}%", "Status diário"
            ])

    def get_resumo_hoje(self):
        if not os.path.exists(self.arquivo):
            return {"trades": 0, "lucro": 0.0, "capital": 10.0}
        hoje = datetime.now().strftime("%Y-%m-%d")
        trades_hoje = 0
        ultimo_capital = 10.0
        ultimo_lucro = 0.0
        try:
            with open(self.arquivo, 'r', newline='', encoding='utf-8') as file:
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

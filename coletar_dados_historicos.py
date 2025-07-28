import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import PAR, INTERVALO

# Configurações
INTERVALOS_BINANCE = {
    '1m': Client.KLINE_INTERVAL_1MINUTE,
    '3m': Client.KLINE_INTERVAL_3MINUTE,
    '5m': Client.KLINE_INTERVAL_5MINUTE,
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '2h': Client.KLINE_INTERVAL_2HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR,
    '6h': Client.KLINE_INTERVAL_6HOUR,
    '8h': Client.KLINE_INTERVAL_8HOUR,
    '12h': Client.KLINE_INTERVAL_12HOUR,
    '1d': Client.KLINE_INTERVAL_1DAY,
    '3d': Client.KLINE_INTERVAL_3DAY,
    '1w': Client.KLINE_INTERVAL_1WEEK,
    '1M': Client.KLINE_INTERVAL_1MONTH
}

def coletar_dados_historicos(par=PAR, intervalo='1h', dias=30, arquivo_saida='dados_historicos.csv'):
    """Coleta dados históricos da Binance e salva em um arquivo CSV"""
    try:
        # Inicializar cliente Binance (sem chaves para dados públicos)
        client = Client()
        
        # Converter intervalo para formato Binance
        intervalo_binance = INTERVALOS_BINANCE.get(intervalo, Client.KLINE_INTERVAL_1HOUR)
        
        # Calcular data de início
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=dias)
        
        # Converter para timestamp em milissegundos
        inicio_ms = int(data_inicio.timestamp() * 1000)
        fim_ms = int(data_fim.timestamp() * 1000)
        
        print(f"📊 Coletando dados históricos para {par} em intervalo {intervalo}...")
        print(f"📅 Período: {data_inicio.strftime('%Y-%m-%d')} até {data_fim.strftime('%Y-%m-%d')}")
        
        # Coletar dados históricos
        klines = client.get_historical_klines(
            par, intervalo_binance, inicio_ms, fim_ms
        )
        
        # Converter para DataFrame
        colunas = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ]
        
        df = pd.DataFrame(klines, columns=colunas)
        
        # Converter tipos de dados
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        # Adicionar coluna de data formatada
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Salvar em CSV
        df.to_csv(arquivo_saida, index=False)
        
        print(f"✅ Dados salvos em {arquivo_saida}")
        print(f"📈 Total de candles coletados: {len(df)}")
        print(f"📅 Primeiro candle: {df['date'].iloc[0]}")
        print(f"📅 Último candle: {df['date'].iloc[-1]}")
        
        return df
    
    except BinanceAPIException as e:
        print(f"❌ Erro na API da Binance: {e}")
    except Exception as e:
        print(f"❌ Erro ao coletar dados: {e}")

def main():
    # Parâmetros para coleta de dados
    par = input("Digite o par (ex: BTCUSDT) [padrão: BTCUSDT]: ") or PAR
    intervalo = input("Digite o intervalo (1m, 5m, 15m, 1h, 4h, 1d) [padrão: 1h]: ") or '1h'
    dias = int(input("Digite o número de dias para coletar [padrão: 30]: ") or 30)
    arquivo_saida = input("Digite o nome do arquivo de saída [padrão: dados_historicos.csv]: ") or 'dados_historicos.csv'
    
    # Coletar dados
    coletar_dados_historicos(par, intervalo, dias, arquivo_saida)
    
    # Perguntar se deseja executar o backtest
    executar_backtest = input("Deseja executar o backtest com os dados coletados? (s/n): ").lower() == 's'
    
    if executar_backtest:
        try:
            from backtest_ml import main as backtest_main
            backtest_main()
        except ImportError:
            print("❌ Módulo de backtest não encontrado. Execute 'python backtest_ml.py' manualmente.")
        except Exception as e:
            print(f"❌ Erro ao executar backtest: {e}")

if __name__ == "__main__":
    main()
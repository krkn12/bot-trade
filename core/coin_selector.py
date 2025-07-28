# Módulo para seleção automática de moedas com potencial de lucro
# Identifica novas listagens e moedas com alta volatilidade e volume

import time
import json
import os
from datetime import datetime, timedelta
import numpy as np
from binance_api import get_new_listings, analyze_potential, get_all_symbols, get_24h_ticker

class CoinSelector:
    def __init__(self, config_file="coin_selector_config.json"):
        self.config_file = config_file
        self.selected_coins = []
        self.last_scan_time = 0
        self.scan_interval = 3600  # 1 hora por padrão
        self.max_coins = 5  # Número máximo de moedas para monitorar
        self.new_listing_days = 14  # Considerar moedas listadas nos últimos 14 dias
        self.min_volume = 1000000  # Volume mínimo em USDT (1 milhão)
        self.min_volatility = 5.0  # Volatilidade mínima (5%)
        self.blacklist = []  # Moedas a serem ignoradas
        self.quote_asset = "USDT"  # Moeda base para negociação
        
        # Carregar configurações se existirem
        self._load_config()
    
    def _load_config(self):
        """Carrega configurações do arquivo"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    
                self.selected_coins = config.get("selected_coins", [])
                self.last_scan_time = config.get("last_scan_time", 0)
                self.scan_interval = config.get("scan_interval", 3600)
                self.max_coins = config.get("max_coins", 5)
                self.new_listing_days = config.get("new_listing_days", 14)
                self.min_volume = config.get("min_volume", 1000000)
                self.min_volatility = config.get("min_volatility", 5.0)
                self.blacklist = config.get("blacklist", [])
                self.quote_asset = config.get("quote_asset", "USDT")
                
                print(f"✅ Configurações de seleção de moedas carregadas")
            except Exception as e:
                print(f"⚠️ Erro ao carregar configurações de seleção de moedas: {e}")
    
    def _save_config(self):
        """Salva configurações no arquivo"""
        config = {
            "selected_coins": self.selected_coins,
            "last_scan_time": self.last_scan_time,
            "scan_interval": self.scan_interval,
            "max_coins": self.max_coins,
            "new_listing_days": self.new_listing_days,
            "min_volume": self.min_volume,
            "min_volatility": self.min_volatility,
            "blacklist": self.blacklist,
            "quote_asset": self.quote_asset
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"⚠️ Erro ao salvar configurações de seleção de moedas: {e}")
    
    def should_scan(self):
        """Verifica se é hora de fazer uma nova varredura"""
        current_time = time.time()
        return (current_time - self.last_scan_time) >= self.scan_interval
    
    def scan_new_listings(self):
        """Busca novas listagens na Binance"""
        print(f"🔍 Buscando novas listagens na Binance (últimos {self.new_listing_days} dias)...")
        new_coins = get_new_listings(days=self.new_listing_days, quote_asset=self.quote_asset)
        
        if not new_coins:
            print("ℹ️ Nenhuma nova listagem encontrada")
            return []
        
        print(f"✅ Encontradas {len(new_coins)} novas listagens")
        
        # Filtrar moedas na blacklist
        filtered_coins = [coin for coin in new_coins if coin["symbol"] not in self.blacklist]
        
        # Analisar potencial das novas moedas
        symbols = [coin["symbol"] for coin in filtered_coins]
        high_potential = analyze_potential(
            symbols, 
            volume_min=self.min_volume, 
            volatility_min=self.min_volatility
        )
        
        if high_potential:
            print(f"🚀 {len(high_potential)} novas moedas com alto potencial identificadas")
            for coin in high_potential[:3]:  # Mostrar apenas as 3 primeiras
                print(f"  - {coin['symbol']}: Vol: ${coin['volume_24h']:,.2f}, Volatilidade: {coin['volatility']:.2f}%")
        
        return high_potential
    
    def scan_existing_coins(self):
        """Analisa moedas existentes para encontrar oportunidades"""
        print("🔍 Analisando moedas existentes com alto potencial...")
        
        # Obter todos os símbolos disponíveis
        all_symbols = get_all_symbols(self.quote_asset)
        
        # Filtrar moedas na blacklist
        filtered_symbols = [symbol for symbol in all_symbols if symbol not in self.blacklist]
        
        # Analisar potencial de todas as moedas
        high_potential = analyze_potential(
            filtered_symbols, 
            volume_min=self.min_volume, 
            volatility_min=self.min_volatility
        )
        
        if high_potential:
            print(f"🚀 {len(high_potential)} moedas existentes com alto potencial identificadas")
            for coin in high_potential[:3]:  # Mostrar apenas as 3 primeiras
                print(f"  - {coin['symbol']}: Vol: ${coin['volume_24h']:,.2f}, Volatilidade: {coin['volatility']:.2f}%")
        
        return high_potential
    
    def select_best_coins(self):
        """Seleciona as melhores moedas para negociação"""
        if not self.should_scan():
            return self.selected_coins
        
        print("🔄 Iniciando seleção automática de moedas...")
        
        # Atualizar timestamp da última varredura
        self.last_scan_time = time.time()
        
        # Buscar moedas existentes com potencial (todas, não apenas amostra)
        existing_coins = self.scan_existing_coins()
        
        # Combinar resultados (agora usando apenas moedas existentes)
        all_potential_coins = existing_coins
        
        # Ordenar por potencial (usando volatilidade como métrica principal)
        sorted_coins = sorted(all_potential_coins, key=lambda x: x["volatility"], reverse=True)
        
        # Selecionar as melhores moedas (até o limite máximo)
        best_coins = sorted_coins[:self.max_coins]
        
        # Atualizar lista de moedas selecionadas
        self.selected_coins = [coin["symbol"] for coin in best_coins]
        
        # Salvar configuração atualizada
        self._save_config()
        
        print(f"✅ Selecionadas {len(self.selected_coins)} moedas para negociação")
        for symbol in self.selected_coins:
            print(f"  - {symbol}")
        
        return self.selected_coins
    
    def get_selected_coins(self):
        """Retorna a lista atual de moedas selecionadas"""
        # Se for hora de fazer uma nova varredura, atualiza a lista
        if self.should_scan():
            return self.select_best_coins()
        return self.selected_coins
    
    def add_to_blacklist(self, symbol):
        """Adiciona uma moeda à blacklist"""
        if symbol not in self.blacklist:
            self.blacklist.append(symbol)
            self._save_config()
            print(f"⛔ {symbol} adicionado à blacklist")
    
    def remove_from_blacklist(self, symbol):
        """Remove uma moeda da blacklist"""
        if symbol in self.blacklist:
            self.blacklist.remove(symbol)
            self._save_config()
            print(f"✅ {symbol} removido da blacklist")
    
    def set_scan_interval(self, interval_seconds):
        """Define o intervalo entre varreduras"""
        self.scan_interval = interval_seconds
        self._save_config()
        print(f"⏱️ Intervalo de varredura definido para {interval_seconds} segundos")
    
    def set_max_coins(self, max_coins):
        """Define o número máximo de moedas para monitorar"""
        self.max_coins = max_coins
        self._save_config()
        print(f"🔢 Número máximo de moedas definido para {max_coins}")
    
    def set_volume_threshold(self, min_volume):
        """Define o volume mínimo para considerar uma moeda"""
        self.min_volume = min_volume
        self._save_config()
        print(f"💰 Volume mínimo definido para ${min_volume:,.2f}")
    
    def set_volatility_threshold(self, min_volatility):
        """Define a volatilidade mínima para considerar uma moeda"""
        self.min_volatility = min_volatility
        self._save_config()
        print(f"📊 Volatilidade mínima definida para {min_volatility:.2f}%")
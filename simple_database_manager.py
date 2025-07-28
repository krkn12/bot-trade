"""
Database Manager Simplificado - Sem dependência do pandas
"""
import sqlite3
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_file="trading_bot_simple.db"):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Tabela de configurações
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de logs simples
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT,
                    source TEXT,
                    message TEXT
                )
            ''')
            
            # Tabela de trades simples
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    side TEXT,
                    price REAL,
                    quantity REAL,
                    profit REAL,
                    reason TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Database inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar database: {e}")
    
    def get_config(self, key, default=None):
        """Obtém valor de configuração"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                try:
                    return json.loads(result[0])
                except:
                    return result[0]
            return default
            
        except Exception as e:
            logger.error(f"Erro ao obter config {key}: {e}")
            return default
    
    def set_config(self, key, value):
        """Define valor de configuração"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            json_value = json.dumps(value)
            cursor.execute('''
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, json_value, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar config {key}: {e}")
            return False
    
    def log(self, level, source, message):
        """Adiciona log ao banco"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO logs (level, source, message)
                VALUES (?, ?, ?)
            ''', (level, source, message))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Erro ao salvar log: {e}")
    
    def add_trade(self, symbol, side, price, quantity, profit=0, reason=""):
        """Adiciona trade ao banco"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (symbol, side, price, quantity, profit, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, side, price, quantity, profit, reason))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Erro ao salvar trade: {e}")
    
    def get_recent_trades(self, limit=10):
        """Obtém trades recentes"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            trades = cursor.fetchall()
            conn.close()
            
            return trades
            
        except Exception as e:
            logger.error(f"Erro ao obter trades: {e}")
            return []
    
    def get_performance_stats(self):
        """Obtém estatísticas simples de performance"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Total de trades
            cursor.execute("SELECT COUNT(*) FROM trades")
            total_trades = cursor.fetchone()[0]
            
            # Trades com lucro
            cursor.execute("SELECT COUNT(*) FROM trades WHERE profit > 0")
            winning_trades = cursor.fetchone()[0]
            
            # Lucro total
            cursor.execute("SELECT SUM(profit) FROM trades")
            total_profit = cursor.fetchone()[0] or 0
            
            conn.close()
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'win_rate': win_rate,
                'total_profit': total_profit
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_profit': 0
            }
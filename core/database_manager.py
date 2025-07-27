"""
Database Manager para Trading Bot
Gerencia persistência de dados com SQLite
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com todas as tabelas necessárias"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela de trades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    position_type TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity REAL NOT NULL,
                    pnl REAL DEFAULT 0,
                    pnl_pct REAL DEFAULT 0,
                    entry_time DATETIME NOT NULL,
                    exit_time DATETIME,
                    duration_seconds INTEGER,
                    stop_loss REAL,
                    take_profit REAL,
                    exit_reason TEXT,
                    strategy_used TEXT,
                    confidence REAL,
                    commission REAL DEFAULT 0,
                    slippage REAL DEFAULT 0,
                    is_simulation BOOLEAN DEFAULT 1,
                    notes TEXT
                )
            ''')
            
            # Tabela de preços históricos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume REAL DEFAULT 0,
                    UNIQUE(symbol, timeframe, timestamp)
                )
            ''')
            
            # Tabela de métricas diárias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    starting_capital REAL NOT NULL,
                    ending_capital REAL NOT NULL,
                    daily_return REAL NOT NULL,
                    trades_count INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    gross_profit REAL DEFAULT 0,
                    gross_loss REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    sharpe_ratio REAL DEFAULT 0,
                    profit_factor REAL DEFAULT 0,
                    largest_win REAL DEFAULT 0,
                    largest_loss REAL DEFAULT 0,
                    avg_win REAL DEFAULT 0,
                    avg_loss REAL DEFAULT 0,
                    max_consecutive_wins INTEGER DEFAULT 0,
                    max_consecutive_losses INTEGER DEFAULT 0
                )
            ''')
            
            # Tabela de sinais de estratégia
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    signal_strength REAL NOT NULL,
                    confidence REAL NOT NULL,
                    rsi REAL,
                    macd REAL,
                    ema_20 REAL,
                    ema_50 REAL,
                    support_level REAL,
                    resistance_level REAL,
                    trend TEXT,
                    current_price REAL NOT NULL,
                    strategy_name TEXT NOT NULL
                )
            ''')
            
            # Tabela de configurações
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    config_key TEXT UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    description TEXT
                )
            ''')
            
            # Tabela de logs do sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    message TEXT NOT NULL,
                    extra_data TEXT
                )
            ''')
            
            # Índices para performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_data_symbol_timeframe ON price_data(symbol, timeframe)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_data_timestamp ON price_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol ON strategy_signals(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON strategy_signals(timestamp)')
            
            conn.commit()
            print("✅ Database inicializado com sucesso")
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexões com o banco"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
        try:
            yield conn
        finally:
            conn.close()
    
    # ==================== TRADES ====================
    
    def save_trade(self, trade_data: Dict) -> int:
        """Salva um trade no banco de dados"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (
                    symbol, position_type, entry_price, exit_price, quantity,
                    pnl, pnl_pct, entry_time, exit_time, duration_seconds,
                    stop_loss, take_profit, exit_reason, strategy_used,
                    confidence, commission, slippage, is_simulation, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('symbol'),
                trade_data.get('position_type'),
                trade_data.get('entry_price'),
                trade_data.get('exit_price'),
                trade_data.get('quantity'),
                trade_data.get('pnl', 0),
                trade_data.get('pnl_pct', 0),
                trade_data.get('entry_time'),
                trade_data.get('exit_time'),
                trade_data.get('duration_seconds'),
                trade_data.get('stop_loss'),
                trade_data.get('take_profit'),
                trade_data.get('exit_reason'),
                trade_data.get('strategy_used'),
                trade_data.get('confidence'),
                trade_data.get('commission', 0),
                trade_data.get('slippage', 0),
                trade_data.get('is_simulation', True),
                trade_data.get('notes')
            ))
            
            trade_id = cursor.lastrowid
            conn.commit()
            return trade_id
    
    def get_trades(self, symbol: str = None, days: int = 30, 
                   limit: int = 1000) -> List[Dict]:
        """Recupera trades do banco de dados"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM trades 
                WHERE timestamp >= datetime('now', '-{} days')
            '''.format(days)
            
            params = []
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_trade_statistics(self, days: int = 30) -> Dict:
        """Calcula estatísticas dos trades"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
                    COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades,
                    SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as gross_profit,
                    SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as gross_loss,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss,
                    MAX(pnl) as largest_win,
                    MIN(pnl) as largest_loss,
                    SUM(pnl) as net_profit,
                    AVG(pnl) as avg_trade,
                    AVG(duration_seconds) as avg_duration
                FROM trades 
                WHERE timestamp >= datetime('now', '-{} days')
                AND exit_time IS NOT NULL
            '''.format(days))
            
            row = cursor.fetchone()
            stats = dict(row) if row else {}
            
            # Calcula métricas derivadas
            if stats.get('total_trades', 0) > 0:
                stats['win_rate'] = (stats.get('winning_trades', 0) / stats['total_trades']) * 100
                
                gross_profit = stats.get('gross_profit', 0)
                gross_loss = stats.get('gross_loss', 0)
                stats['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else 0
                
                stats['avg_duration_minutes'] = stats.get('avg_duration', 0) / 60 if stats.get('avg_duration') else 0
            
            return stats
    
    # ==================== PRICE DATA ====================
    
    def save_price_data(self, symbol: str, timeframe: str, 
                       ohlcv_data: List[Dict]) -> int:
        """Salva dados de preço no banco"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            inserted = 0
            for candle in ohlcv_data:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO price_data (
                            timestamp, symbol, timeframe, open_price, 
                            high_price, low_price, close_price, volume
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        candle.get('timestamp'),
                        symbol,
                        timeframe,
                        candle.get('open'),
                        candle.get('high'),
                        candle.get('low'),
                        candle.get('close'),
                        candle.get('volume', 0)
                    ))
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue  # Dados já existem
            
            conn.commit()
            return inserted
    
    def get_price_data(self, symbol: str, timeframe: str, 
                      limit: int = 1000) -> List[Dict]:
        """Recupera dados de preço"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM price_data 
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (symbol, timeframe, limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Obtém últimos preços para uma lista de símbolos"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            placeholders = ','.join(['?' for _ in symbols])
            cursor.execute(f'''
                SELECT DISTINCT symbol, close_price
                FROM price_data p1
                WHERE symbol IN ({placeholders})
                AND timestamp = (
                    SELECT MAX(timestamp) 
                    FROM price_data p2 
                    WHERE p2.symbol = p1.symbol
                )
            ''', symbols)
            
            rows = cursor.fetchall()
            return {row['symbol']: row['close_price'] for row in rows}
    
    # ==================== STRATEGY SIGNALS ====================
    
    def save_strategy_signal(self, signal_data: Dict) -> int:
        """Salva sinal de estratégia"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO strategy_signals (
                    symbol, timeframe, signal_type, signal_strength, confidence,
                    rsi, macd, ema_20, ema_50, support_level, resistance_level,
                    trend, current_price, strategy_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data.get('symbol'),
                signal_data.get('timeframe'),
                signal_data.get('signal_type'),
                signal_data.get('signal_strength'),
                signal_data.get('confidence'),
                signal_data.get('rsi'),
                signal_data.get('macd'),
                signal_data.get('ema_20'),
                signal_data.get('ema_50'),
                signal_data.get('support_level'),
                signal_data.get('resistance_level'),
                signal_data.get('trend'),
                signal_data.get('current_price'),
                signal_data.get('strategy_name')
            ))
            
            signal_id = cursor.lastrowid
            conn.commit()
            return signal_id
    
    def get_recent_signals(self, symbol: str = None, 
                          hours: int = 24, limit: int = 100) -> List[Dict]:
        """Recupera sinais recentes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM strategy_signals 
                WHERE timestamp >= datetime('now', '-{} hours')
            '''.format(hours)
            
            params = []
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    # ==================== DAILY METRICS ====================
    
    def save_daily_metrics(self, date: str, metrics: Dict) -> int:
        """Salva métricas diárias"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_metrics (
                    date, starting_capital, ending_capital, daily_return,
                    trades_count, winning_trades, losing_trades,
                    gross_profit, gross_loss, max_drawdown, sharpe_ratio,
                    profit_factor, largest_win, largest_loss,
                    avg_win, avg_loss, max_consecutive_wins, max_consecutive_losses
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date,
                metrics.get('starting_capital'),
                metrics.get('ending_capital'),
                metrics.get('daily_return'),
                metrics.get('trades_count', 0),
                metrics.get('winning_trades', 0),
                metrics.get('losing_trades', 0),
                metrics.get('gross_profit', 0),
                metrics.get('gross_loss', 0),
                metrics.get('max_drawdown', 0),
                metrics.get('sharpe_ratio', 0),
                metrics.get('profit_factor', 0),
                metrics.get('largest_win', 0),
                metrics.get('largest_loss', 0),
                metrics.get('avg_win', 0),
                metrics.get('avg_loss', 0),
                metrics.get('max_consecutive_wins', 0),
                metrics.get('max_consecutive_losses', 0)
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_daily_metrics(self, days: int = 30) -> List[Dict]:
        """Recupera métricas diárias"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM daily_metrics 
                WHERE date >= date('now', '-{} days')
                ORDER BY date DESC
            '''.format(days))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ==================== SYSTEM LOGS ====================
    
    def log(self, level: str, module: str, message: str, extra_data: Dict = None):
        """Adiciona log do sistema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_logs (level, module, message, extra_data)
                VALUES (?, ?, ?, ?)
            ''', (
                level.upper(),
                module,
                message,
                json.dumps(extra_data) if extra_data else None
            ))
            
            conn.commit()
    
    def get_logs(self, level: str = None, module: str = None, 
                hours: int = 24, limit: int = 1000) -> List[Dict]:
        """Recupera logs do sistema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM system_logs 
                WHERE timestamp >= datetime('now', '-{} hours')
            '''.format(hours)
            
            params = []
            if level:
                query += ' AND level = ?'
                params.append(level.upper())
            
            if module:
                query += ' AND module = ?'
                params.append(module)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    # ==================== CONFIGURATION ====================
    
    def set_config(self, key: str, value: Any, description: str = None):
        """Define configuração"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO bot_config (config_key, config_value, description)
                VALUES (?, ?, ?)
            ''', (key, json.dumps(value), description))
            
            conn.commit()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Obtém configuração"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT config_value FROM bot_config WHERE config_key = ?', (key,))
            row = cursor.fetchone()
            
            if row:
                return json.loads(row['config_value'])
            return default
    
    # ==================== ANALYTICS ====================
    
    def get_performance_summary(self, days: int = 30) -> Dict:
        """Gera resumo de performance"""
        trade_stats = self.get_trade_statistics(days)
        daily_metrics = self.get_daily_metrics(days)
        
        # Calcula equity curve
        equity_curve = []
        if daily_metrics:
            for metric in reversed(daily_metrics):  # Ordem cronológica
                equity_curve.append({
                    'date': metric['date'],
                    'capital': metric['ending_capital'],
                    'return': metric['daily_return']
                })
        
        # Calcula drawdown máximo
        max_drawdown = 0
        peak = 0
        if equity_curve:
            for point in equity_curve:
                capital = point['capital']
                if capital > peak:
                    peak = capital
                else:
                    drawdown = (peak - capital) / peak
                    max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'trade_statistics': trade_stats,
            'daily_metrics': daily_metrics[:7],  # Últimos 7 dias
            'equity_curve': equity_curve,
            'max_drawdown': max_drawdown * 100,
            'total_days': len(daily_metrics),
            'profitable_days': len([d for d in daily_metrics if d['daily_return'] > 0])
        }
    
    def export_to_csv(self, table: str, filename: str, days: int = 30) -> bool:
        """Exporta dados para CSV"""
        try:
            with self.get_connection() as conn:
                if table == 'trades':
                    query = f'''
                        SELECT * FROM trades 
                        WHERE timestamp >= datetime('now', '-{days} days')
                        ORDER BY timestamp DESC
                    '''
                elif table == 'daily_metrics':
                    query = f'''
                        SELECT * FROM daily_metrics 
                        WHERE date >= date('now', '-{days} days')
                        ORDER BY date DESC
                    '''
                else:
                    return False
                
                df = pd.read_sql_query(query, conn)
                df.to_csv(filename, index=False)
                return True
                
        except Exception as e:
            print(f"❌ Erro ao exportar {table}: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Remove dados antigos para otimização"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Remove logs antigos
            cursor.execute('''
                DELETE FROM system_logs 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days_to_keep))
            
            # Remove sinais antigos
            cursor.execute('''
                DELETE FROM strategy_signals 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days_to_keep))
            
            # Remove dados de preço muito antigos (mantém mais tempo)
            cursor.execute('''
                DELETE FROM price_data 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days_to_keep * 2))
            
            # Vacuum para otimizar espaço
            cursor.execute('VACUUM')
            
            conn.commit()
            print(f"✅ Limpeza concluída: dados > {days_to_keep} dias removidos")
    
    def get_database_stats(self) -> Dict:
        """Retorna estatísticas do banco de dados"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Conta registros em cada tabela
            tables = ['trades', 'price_data', 'daily_metrics', 'strategy_signals', 'system_logs']
            
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
                stats[f'{table}_count'] = cursor.fetchone()['count']
            
            # Tamanho do banco
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            stats['database_size_bytes'] = cursor.fetchone()['size']
            stats['database_size_mb'] = stats['database_size_bytes'] / (1024 * 1024)
            
            return stats

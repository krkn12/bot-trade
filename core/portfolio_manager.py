"""
Portfolio Manager para Trading Bot
Gerencia múltiplos pares e diversificação de risco
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

class PositionType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class Position:
    symbol: str
    position_type: PositionType
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float] = None
    unrealized_pnl: float = 0.0
    
    def update_unrealized_pnl(self, current_price: float):
        """Atualiza PnL não realizado"""
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity

@dataclass
class PortfolioMetrics:
    total_value: float = 0.0
    available_cash: float = 0.0
    total_positions_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl_today: float = 0.0
    daily_return: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    active_positions: int = 0
    trades_today: int = 0

class PortfolioManager:
    def __init__(self, initial_capital: float, max_positions: int = 5, 
                 max_risk_per_trade: float = 0.02, max_portfolio_risk: float = 0.10):
        
        self.initial_capital = initial_capital
        self.available_cash = initial_capital
        self.max_positions = max_positions
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        
        # Posições ativas
        self.positions: Dict[str, Position] = {}
        
        # Histórico
        self.trade_history: List[Dict] = []
        self.daily_values: List[float] = [initial_capital]
        self.equity_curve: List[Tuple[datetime, float]] = [(datetime.now(), initial_capital)]
        
        # Configurações de diversificação
        self.symbol_weights = {
            'BTCUSDT': 0.4,   # 40% máximo em BTC
            'ETHUSDT': 0.3,   # 30% máximo em ETH
            'ADAUSDT': 0.15,  # 15% máximo em ADA
            'DOTUSDT': 0.15,  # 15% máximo em DOT
        }
        
        # Correlações (simplificado)
        self.correlations = {
            ('BTCUSDT', 'ETHUSDT'): 0.8,
            ('BTCUSDT', 'ADAUSDT'): 0.7,
            ('ETHUSDT', 'ADAUSDT'): 0.6,
        }
        
        # Métricas
        self.metrics = PortfolioMetrics()
        
    def can_open_position(self, symbol: str, position_size: float) -> Tuple[bool, str]:
        """Verifica se pode abrir uma nova posição"""
        
        # Verifica número máximo de posições
        if len(self.positions) >= self.max_positions:
            return False, f"Máximo de {self.max_positions} posições atingido"
        
        # Verifica se já tem posição no símbolo
        if symbol in self.positions:
            return False, f"Já existe posição em {symbol}"
        
        # Verifica cash disponível
        if position_size > self.available_cash:
            return False, f"Cash insuficiente: ${self.available_cash:.2f} < ${position_size:.2f}"
        
        # Verifica peso máximo do símbolo
        max_weight = self.symbol_weights.get(symbol, 0.2)  # Default 20%
        current_portfolio_value = self.get_total_portfolio_value()
        max_position_size = current_portfolio_value * max_weight
        
        if position_size > max_position_size:
            return False, f"Posição muito grande para {symbol}: ${position_size:.2f} > ${max_position_size:.2f}"
        
        # Verifica risco de correlação
        correlation_risk = self._calculate_correlation_risk(symbol, position_size)
        if correlation_risk > self.max_portfolio_risk:
            return False, f"Risco de correlação muito alto: {correlation_risk:.2%}"
        
        return True, "OK"
    
    def open_position(self, symbol: str, position_type: PositionType, 
                     entry_price: float, quantity: float, 
                     stop_loss: float, take_profit: float) -> bool:
        """Abre uma nova posição"""
        
        position_size = quantity * entry_price
        can_open, reason = self.can_open_position(symbol, position_size)
        
        if not can_open:
            print(f"❌ Não foi possível abrir posição em {symbol}: {reason}")
            return False
        
        # Cria a posição
        position = Position(
            symbol=symbol,
            position_type=position_type,
            entry_price=entry_price,
            quantity=quantity,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        self.positions[symbol] = position
        self.available_cash -= position_size
        
        print(f"✅ Posição {position_type.value} aberta em {symbol}")
        print(f"   💰 Preço: ${entry_price:.4f} | Qtd: {quantity:.6f}")
        print(f"   🛑 Stop Loss: ${stop_loss:.4f} | 🎯 Take Profit: ${take_profit:.4f}")
        print(f"   💵 Valor: ${position_size:.2f} | Cash restante: ${self.available_cash:.2f}")
        
        return True
    
    def close_position(self, symbol: str, exit_price: float, reason: str = "Manual") -> Optional[float]:
        """Fecha uma posição e retorna o PnL"""
        
        if symbol not in self.positions:
            print(f"❌ Posição não encontrada: {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # Calcula PnL
        if position.position_type == PositionType.LONG:
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity
        
        # Atualiza cash
        position_value = position.quantity * exit_price
        self.available_cash += position_value
        
        # Remove posição
        del self.positions[symbol]
        
        # Registra no histórico
        trade_record = {
            'symbol': symbol,
            'position_type': position.position_type.value,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'quantity': position.quantity,
            'pnl': pnl,
            'pnl_pct': (pnl / (position.entry_price * position.quantity)) * 100,
            'entry_time': position.entry_time,
            'exit_time': datetime.now(),
            'duration': datetime.now() - position.entry_time,
            'reason': reason
        }
        
        self.trade_history.append(trade_record)
        
        # Atualiza métricas
        self.metrics.realized_pnl_today += pnl
        self.metrics.trades_today += 1
        
        print(f"🔄 Posição fechada em {symbol} ({reason})")
        print(f"   💰 Preço saída: ${exit_price:.4f}")
        print(f"   📊 PnL: ${pnl:.2f} ({trade_record['pnl_pct']:.2f}%)")
        print(f"   💵 Cash: ${self.available_cash:.2f}")
        
        return pnl
    
    def update_positions(self, price_data: Dict[str, float]):
        """Atualiza todas as posições com preços atuais"""
        
        for symbol, position in self.positions.items():
            if symbol in price_data:
                current_price = price_data[symbol]
                position.update_unrealized_pnl(current_price)
                
                # Verifica stop loss e take profit
                self._check_exit_conditions(symbol, current_price)
    
    def _check_exit_conditions(self, symbol: str, current_price: float):
        """Verifica condições de saída (stop loss, take profit)"""
        
        position = self.positions[symbol]
        
        if position.position_type == PositionType.LONG:
            # Stop Loss
            if current_price <= position.stop_loss:
                self.close_position(symbol, current_price, "Stop Loss")
                return
            
            # Take Profit
            if current_price >= position.take_profit:
                self.close_position(symbol, current_price, "Take Profit")
                return
                
        else:  # SHORT
            # Stop Loss
            if current_price >= position.stop_loss:
                self.close_position(symbol, current_price, "Stop Loss")
                return
            
            # Take Profit
            if current_price <= position.take_profit:
                self.close_position(symbol, current_price, "Take Profit")
                return
    
    def get_total_portfolio_value(self) -> float:
        """Calcula valor total do portfolio"""
        positions_value = sum(pos.quantity * pos.entry_price + pos.unrealized_pnl 
                            for pos in self.positions.values())
        return self.available_cash + positions_value
    
    def get_portfolio_allocation(self) -> Dict[str, float]:
        """Retorna alocação atual do portfolio"""
        total_value = self.get_total_portfolio_value()
        
        if total_value == 0:
            return {}
        
        allocation = {'CASH': self.available_cash / total_value}
        
        for symbol, position in self.positions.items():
            position_value = position.quantity * position.entry_price + position.unrealized_pnl
            allocation[symbol] = position_value / total_value
        
        return allocation
    
    def calculate_portfolio_metrics(self) -> PortfolioMetrics:
        """Calcula métricas do portfolio"""
        
        total_value = self.get_total_portfolio_value()
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        # Atualiza métricas básicas
        self.metrics.total_value = total_value
        self.metrics.available_cash = self.available_cash
        self.metrics.total_positions_value = total_value - self.available_cash
        self.metrics.unrealized_pnl = unrealized_pnl
        self.metrics.daily_return = ((total_value / self.initial_capital) - 1) * 100
        self.metrics.active_positions = len(self.positions)
        
        # Calcula métricas avançadas se há histórico
        if self.trade_history:
            self.metrics.win_rate = self._calculate_win_rate()
            self.metrics.profit_factor = self._calculate_profit_factor()
            self.metrics.sharpe_ratio = self._calculate_sharpe_ratio()
            self.metrics.max_drawdown = self._calculate_max_drawdown()
        
        # Atualiza equity curve
        self.equity_curve.append((datetime.now(), total_value))
        
        # Limita histórico
        if len(self.equity_curve) > 1000:
            self.equity_curve = self.equity_curve[-1000:]
        
        return self.metrics
    
    def _calculate_correlation_risk(self, new_symbol: str, position_size: float) -> float:
        """Calcula risco de correlação ao adicionar nova posição"""
        
        total_value = self.get_total_portfolio_value()
        correlation_risk = 0
        
        for existing_symbol in self.positions.keys():
            # Busca correlação entre símbolos
            correlation = self._get_correlation(new_symbol, existing_symbol)
            
            # Peso da posição existente
            existing_weight = (self.positions[existing_symbol].quantity * 
                             self.positions[existing_symbol].entry_price) / total_value
            
            # Peso da nova posição
            new_weight = position_size / total_value
            
            # Risco de correlação = correlação * peso1 * peso2
            correlation_risk += abs(correlation) * existing_weight * new_weight
        
        return correlation_risk
    
    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Obtém correlação entre dois símbolos"""
        pair = (symbol1, symbol2) if symbol1 < symbol2 else (symbol2, symbol1)
        return self.correlations.get(pair, 0.3)  # Default 30% correlação
    
    def _calculate_win_rate(self) -> float:
        """Calcula taxa de acerto"""
        if not self.trade_history:
            return 0
        wins = sum(1 for trade in self.trade_history if trade['pnl'] > 0)
        return (wins / len(self.trade_history)) * 100
    
    def _calculate_profit_factor(self) -> float:
        """Calcula Profit Factor"""
        if not self.trade_history:
            return 0
        
        gross_profit = sum(trade['pnl'] for trade in self.trade_history if trade['pnl'] > 0)
        gross_loss = sum(abs(trade['pnl']) for trade in self.trade_history if trade['pnl'] < 0)
        
        return gross_profit / gross_loss if gross_loss > 0 else 0
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calcula Sharpe Ratio simplificado"""
        if len(self.daily_values) < 2:
            return 0
        
        returns = [(self.daily_values[i] / self.daily_values[i-1] - 1) 
                  for i in range(1, len(self.daily_values))]
        
        if not returns:
            return 0
        
        mean_return = sum(returns) / len(returns)
        
        if len(returns) < 2:
            return 0
        
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5
        
        return (mean_return / std_dev) if std_dev > 0 else 0
    
    def _calculate_max_drawdown(self) -> float:
        """Calcula Maximum Drawdown"""
        if len(self.equity_curve) < 2:
            return 0
        
        values = [point[1] for point in self.equity_curve]
        peak = values[0]
        max_dd = 0
        
        for value in values:
            if value > peak:
                peak = value
            else:
                dd = (peak - value) / peak
                max_dd = max(max_dd, dd)
        
        return max_dd * 100
    
    def get_position_summary(self) -> Dict:
        """Retorna resumo das posições"""
        if not self.positions:
            return {'message': 'Nenhuma posição ativa'}
        
        summary = {}
        for symbol, position in self.positions.items():
            summary[symbol] = {
                'type': position.position_type.value,
                'entry_price': position.entry_price,
                'quantity': position.quantity,
                'unrealized_pnl': position.unrealized_pnl,
                'pnl_pct': (position.unrealized_pnl / (position.entry_price * position.quantity)) * 100,
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit,
                'duration': str(datetime.now() - position.entry_time).split('.')[0]
            }
        
        return summary
    
    def save_state(self, filename: str = "portfolio_state.json"):
        """Salva estado do portfolio"""
        state = {
            'available_cash': self.available_cash,
            'positions': {
                symbol: {
                    'symbol': pos.symbol,
                    'position_type': pos.position_type.value,
                    'entry_price': pos.entry_price,
                    'quantity': pos.quantity,
                    'entry_time': pos.entry_time.isoformat(),
                    'stop_loss': pos.stop_loss,
                    'take_profit': pos.take_profit,
                    'trailing_stop': pos.trailing_stop
                }
                for symbol, pos in self.positions.items()
            },
            'trade_history': self.trade_history[-100:],  # Últimos 100 trades
            'metrics': {
                'realized_pnl_today': self.metrics.realized_pnl_today,
                'trades_today': self.metrics.trades_today
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def load_state(self, filename: str = "portfolio_state.json"):
        """Carrega estado do portfolio"""
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            
            self.available_cash = state.get('available_cash', self.initial_capital)
            
            # Reconstrói posições
            for symbol, pos_data in state.get('positions', {}).items():
                position = Position(
                    symbol=pos_data['symbol'],
                    position_type=PositionType(pos_data['position_type']),
                    entry_price=pos_data['entry_price'],
                    quantity=pos_data['quantity'],
                    entry_time=datetime.fromisoformat(pos_data['entry_time']),
                    stop_loss=pos_data['stop_loss'],
                    take_profit=pos_data['take_profit'],
                    trailing_stop=pos_data.get('trailing_stop')
                )
                self.positions[symbol] = position
            
            # Restaura histórico
            self.trade_history = state.get('trade_history', [])
            
            # Restaura métricas
            metrics_data = state.get('metrics', {})
            self.metrics.realized_pnl_today = metrics_data.get('realized_pnl_today', 0)
            self.metrics.trades_today = metrics_data.get('trades_today', 0)
            
            print(f"✅ Estado do portfolio carregado de {filename}")
            
        except FileNotFoundError:
            print(f"⚠️ Arquivo {filename} não encontrado. Iniciando com estado limpo.")
        except Exception as e:
            print(f"❌ Erro ao carregar estado: {e}")
    
    def print_portfolio_status(self):
        """Imprime status atual do portfolio"""
        metrics = self.calculate_portfolio_metrics()
        allocation = self.get_portfolio_allocation()
        
        print("\n" + "="*60)
        print("📊 STATUS DO PORTFOLIO")
        print("="*60)
        print(f"💰 Valor Total: ${metrics.total_value:.2f}")
        print(f"💵 Cash Disponível: ${metrics.available_cash:.2f} ({allocation.get('CASH', 0)*100:.1f}%)")
        print(f"📈 Retorno Diário: {metrics.daily_return:.2f}%")
        print(f"💹 PnL Não Realizado: ${metrics.unrealized_pnl:.2f}")
        print(f"💰 PnL Realizado Hoje: ${metrics.realized_pnl_today:.2f}")
        print(f"📊 Posições Ativas: {metrics.active_positions}/{self.max_positions}")
        print(f"🎯 Taxa de Acerto: {metrics.win_rate:.1f}%")
        print(f"⚡ Profit Factor: {metrics.profit_factor:.2f}")
        print(f"📉 Max Drawdown: {metrics.max_drawdown:.2f}%")
        
        if self.positions:
            print("\n📋 POSIÇÕES ATIVAS:")
            for symbol, pos in self.positions.items():
                pnl_pct = (pos.unrealized_pnl / (pos.entry_price * pos.quantity)) * 100
                print(f"   {symbol}: {pos.position_type.value} | "
                      f"${pos.entry_price:.4f} | "
                      f"PnL: ${pos.unrealized_pnl:.2f} ({pnl_pct:+.2f}%)")
        
        print("="*60)

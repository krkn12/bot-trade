"""
Risk Manager Avançado para Trading Bot
Implementa Kelly Criterion, Position Sizing, Trailing Stop Loss
"""
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class RiskManager:
    def __init__(self, 
                 max_daily_loss: float = 0.05,  # 5% perda máxima diária
                 max_position_size: float = 0.15,  # 15% máximo por posição
                 max_portfolio_risk: float = 0.20,  # 20% risco total do portfolio
                 trailing_stop_activation: float = 0.02,  # 2% para ativar trailing
                 trailing_stop_distance: float = 0.01):  # 1% distância do trailing
        
        self.max_daily_loss = max_daily_loss
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.trailing_stop_activation = trailing_stop_activation
        self.trailing_stop_distance = trailing_stop_distance
        
        # Histórico para cálculo de métricas
        self.trade_history: List[Dict] = []
        self.daily_returns: List[float] = []
        self.trailing_stops: Dict[str, Dict] = {}  # symbol -> {price, activated}
        
    def calculate_kelly_position_size(self, 
                                    capital: float,
                                    win_rate: float,
                                    avg_win: float,
                                    avg_loss: float,
                                    risk_free_rate: float = 0.02) -> float:
        """
        Calcula position size usando Kelly Criterion
        Kelly% = (bp - q) / b
        onde: b = odds recebidas, p = probabilidade de ganhar, q = probabilidade de perder
        """
        if win_rate <= 0 or win_rate >= 1 or avg_loss <= 0:
            return capital * 0.02  # Default 2% se não há dados suficientes
            
        # Calcula Kelly Criterion
        b = avg_win / avg_loss  # Ratio win/loss
        p = win_rate
        q = 1 - win_rate
        
        kelly_fraction = (b * p - q) / b
        
        # Aplica limitadores de segurança
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Max 25% Kelly
        
        # Fractional Kelly (mais conservador)
        fractional_kelly = kelly_fraction * 0.5  # 50% do Kelly completo
        
        position_size = capital * fractional_kelly
        
        # Aplica limites máximos
        max_allowed = capital * self.max_position_size
        return min(position_size, max_allowed)
    
    def calculate_position_size_fixed_risk(self,
                                         capital: float,
                                         entry_price: float,
                                         stop_loss_price: float,
                                         risk_per_trade: float = 0.02) -> float:
        """Calcula position size baseado em risco fixo por trade"""
        if stop_loss_price <= 0 or entry_price <= stop_loss_price:
            return 0
            
        risk_per_unit = abs(entry_price - stop_loss_price)
        max_risk_amount = capital * risk_per_trade
        
        position_size = max_risk_amount / risk_per_unit
        max_allowed = capital * self.max_position_size
        
        return min(position_size, max_allowed)
    
    def update_trailing_stop(self, symbol: str, current_price: float, position_type: str = 'LONG') -> Optional[float]:
        """
        Atualiza trailing stop loss
        Retorna novo stop loss price ou None se não mudou
        """
        if symbol not in self.trailing_stops:
            self.trailing_stops[symbol] = {
                'highest_price': current_price if position_type == 'LONG' else float('inf'),
                'lowest_price': current_price if position_type == 'SHORT' else 0,
                'stop_price': None,
                'activated': False,
                'entry_price': current_price,
                'position_type': position_type
            }
            return None
            
        trailing_data = self.trailing_stops[symbol]
        
        if position_type == 'LONG':
            # Para posição LONG
            if current_price > trailing_data['highest_price']:
                trailing_data['highest_price'] = current_price
                
                # Ativa trailing stop se ganho >= threshold
                profit_pct = (current_price - trailing_data['entry_price']) / trailing_data['entry_price']
                if profit_pct >= self.trailing_stop_activation:
                    trailing_data['activated'] = True
                    
                # Atualiza stop price se trailing ativo
                if trailing_data['activated']:
                    new_stop = current_price * (1 - self.trailing_stop_distance)
                    if trailing_data['stop_price'] is None or new_stop > trailing_data['stop_price']:
                        trailing_data['stop_price'] = new_stop
                        return new_stop
                        
        else:  # SHORT position
            if current_price < trailing_data['lowest_price']:
                trailing_data['lowest_price'] = current_price
                
                profit_pct = (trailing_data['entry_price'] - current_price) / trailing_data['entry_price']
                if profit_pct >= self.trailing_stop_activation:
                    trailing_data['activated'] = True
                    
                if trailing_data['activated']:
                    new_stop = current_price * (1 + self.trailing_stop_distance)
                    if trailing_data['stop_price'] is None or new_stop < trailing_data['stop_price']:
                        trailing_data['stop_price'] = new_stop
                        return new_stop
        
        return None
    
    def should_stop_trading(self, current_capital: float, initial_capital: float) -> Tuple[bool, str]:
        """Verifica se deve parar de operar por gestão de risco"""
        daily_loss_pct = (initial_capital - current_capital) / initial_capital
        
        if daily_loss_pct >= self.max_daily_loss:
            return True, f"⛔ STOP: Perda diária máxima atingida ({daily_loss_pct:.2%})"
            
        # Verifica drawdown consecutivo
        if len(self.daily_returns) >= 3:
            consecutive_losses = all(r < 0 for r in self.daily_returns[-3:])
            if consecutive_losses and daily_loss_pct > 0.02:  # 3 perdas + 2% loss
                return True, "⛔ STOP: 3 perdas consecutivas + 2% drawdown"
                
        return False, ""
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calcula Sharpe Ratio"""
        if len(returns) < 2:
            return 0
            
        excess_returns = [r - risk_free_rate/252 for r in returns]  # Daily risk-free rate
        mean_excess = sum(excess_returns) / len(excess_returns)
        
        if len(excess_returns) < 2:
            return 0
            
        variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
        std_dev = math.sqrt(variance)
        
        return mean_excess / std_dev if std_dev > 0 else 0
    
    def calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calcula Sortino Ratio (considera apenas downside deviation)"""
        if len(returns) < 2:
            return 0
            
        excess_returns = [r - risk_free_rate/252 for r in returns]
        mean_excess = sum(excess_returns) / len(excess_returns)
        
        # Apenas retornos negativos para downside deviation
        negative_returns = [r for r in excess_returns if r < 0]
        
        if len(negative_returns) < 2:
            return float('inf') if mean_excess > 0 else 0
            
        downside_variance = sum(r ** 2 for r in negative_returns) / len(negative_returns)
        downside_deviation = math.sqrt(downside_variance)
        
        return mean_excess / downside_deviation if downside_deviation > 0 else 0
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> Tuple[float, int, int]:
        """
        Calcula Maximum Drawdown
        Retorna: (max_dd_pct, start_index, end_index)
        """
        if len(equity_curve) < 2:
            return 0, 0, 0
            
        peak = equity_curve[0]
        max_dd = 0
        max_dd_start = 0
        max_dd_end = 0
        current_dd_start = 0
        
        for i, value in enumerate(equity_curve):
            if value > peak:
                peak = value
                current_dd_start = i
            else:
                dd = (peak - value) / peak
                if dd > max_dd:
                    max_dd = dd
                    max_dd_start = current_dd_start
                    max_dd_end = i
                    
        return max_dd, max_dd_start, max_dd_end
    
    def get_risk_metrics(self) -> Dict:
        """Retorna métricas de risco atuais"""
        if not self.daily_returns:
            return {}
            
        return {
            'sharpe_ratio': self.calculate_sharpe_ratio(self.daily_returns),
            'sortino_ratio': self.calculate_sortino_ratio(self.daily_returns),
            'win_rate': self._calculate_win_rate(),
            'avg_win': self._calculate_avg_win(),
            'avg_loss': self._calculate_avg_loss(),
            'profit_factor': self._calculate_profit_factor(),
            'total_trades': len(self.trade_history)
        }
    
    def _calculate_win_rate(self) -> float:
        """Calcula taxa de acerto"""
        if not self.trade_history:
            return 0
        wins = sum(1 for trade in self.trade_history if trade.get('pnl', 0) > 0)
        return wins / len(self.trade_history)
    
    def _calculate_avg_win(self) -> float:
        """Calcula ganho médio dos trades vencedores"""
        wins = [trade['pnl'] for trade in self.trade_history if trade.get('pnl', 0) > 0]
        return sum(wins) / len(wins) if wins else 0
    
    def _calculate_avg_loss(self) -> float:
        """Calcula perda média dos trades perdedores"""
        losses = [abs(trade['pnl']) for trade in self.trade_history if trade.get('pnl', 0) < 0]
        return sum(losses) / len(losses) if losses else 0
    
    def _calculate_profit_factor(self) -> float:
        """Calcula Profit Factor (Gross Profit / Gross Loss)"""
        gross_profit = sum(trade['pnl'] for trade in self.trade_history if trade.get('pnl', 0) > 0)
        gross_loss = sum(abs(trade['pnl']) for trade in self.trade_history if trade.get('pnl', 0) < 0)
        return gross_profit / gross_loss if gross_loss > 0 else 0
    
    def add_trade(self, pnl: float, entry_price: float, exit_price: float, symbol: str):
        """Adiciona trade ao histórico"""
        trade = {
            'timestamp': datetime.now(),
            'pnl': pnl,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'symbol': symbol,
            'return': pnl / entry_price if entry_price > 0 else 0
        }
        self.trade_history.append(trade)
        self.daily_returns.append(trade['return'])
        
        # Limita histórico a 1000 trades
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]
            self.daily_returns = self.daily_returns[-1000:]
    
    def reset_trailing_stop(self, symbol: str):
        """Remove trailing stop para um símbolo"""
        if symbol in self.trailing_stops:
            del self.trailing_stops[symbol]

"""
Multi-Timeframe Strategy para Trading Bot
Analisa múltiplos timeframes para decisões mais precisas
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class Signal(Enum):
    STRONG_BUY = 2
    BUY = 1
    NEUTRAL = 0
    SELL = -1
    STRONG_SELL = -2

class Timeframe(Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

@dataclass
class TimeframeAnalysis:
    timeframe: Timeframe
    signal: Signal
    confidence: float  # 0-1
    rsi: Optional[float] = None
    macd: Optional[float] = None
    trend: Optional[str] = None
    support: Optional[float] = None
    resistance: Optional[float] = None

class MultiTimeframeStrategy:
    def __init__(self):
        # Pesos para cada timeframe (maior = mais importante)
        self.timeframe_weights = {
            Timeframe.M1: 0.1,   # Ruído, peso baixo
            Timeframe.M5: 0.15,  # Entrada/saída
            Timeframe.M15: 0.2,  # Confirmação
            Timeframe.M30: 0.25, # Tendência de curto prazo
            Timeframe.H1: 0.3,   # Tendência principal
        }
        
        # Cache para evitar recálculos
        self.analysis_cache: Dict[str, Dict[Timeframe, TimeframeAnalysis]] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        
    async def analyze_symbol(self, symbol: str, current_price: float, 
                           price_data: Dict[Timeframe, List[float]]) -> Dict[str, any]:
        """
        Analisa um símbolo em múltiplos timeframes
        """
        # Verifica cache
        if self._is_cache_valid(symbol):
            cached_analysis = self.analysis_cache[symbol]
        else:
            # Análise completa
            cached_analysis = {}
            for timeframe in self.timeframe_weights.keys():
                if timeframe in price_data and len(price_data[timeframe]) >= 50:
                    analysis = await self._analyze_timeframe(
                        symbol, timeframe, current_price, price_data[timeframe]
                    )
                    cached_analysis[timeframe] = analysis
            
            # Atualiza cache
            self.analysis_cache[symbol] = cached_analysis
            self.cache_expiry[symbol] = datetime.now() + timedelta(minutes=1)
        
        # Combina sinais de todos os timeframes
        combined_signal = self._combine_signals(cached_analysis)
        
        return {
            'signal': combined_signal['signal'],
            'confidence': combined_signal['confidence'],
            'timeframe_analysis': cached_analysis,
            'entry_price': current_price,
            'stop_loss': self._calculate_stop_loss(cached_analysis, current_price),
            'take_profit': self._calculate_take_profit(cached_analysis, current_price),
            'risk_reward_ratio': combined_signal.get('risk_reward', 2.0)
        }
    
    async def _analyze_timeframe(self, symbol: str, timeframe: Timeframe, 
                               current_price: float, prices: List[float]) -> TimeframeAnalysis:
        """Analisa um timeframe específico"""
        
        # Calcula indicadores técnicos
        rsi = self._calculate_rsi(prices)
        macd = self._calculate_macd(prices)
        ema_20 = self._calculate_ema(prices, 20)
        ema_50 = self._calculate_ema(prices, 50)
        
        # Identifica suporte e resistência
        support, resistance = self._find_support_resistance(prices)
        
        # Determina tendência
        trend = self._determine_trend(prices, ema_20, ema_50)
        
        # Gera sinal baseado nos indicadores
        signal, confidence = self._generate_signal(
            current_price, rsi, macd, ema_20, ema_50, 
            support, resistance, trend, timeframe
        )
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            signal=signal,
            confidence=confidence,
            rsi=rsi,
            macd=macd,
            trend=trend,
            support=support,
            resistance=resistance
        )
    
    def _combine_signals(self, timeframe_analyses: Dict[Timeframe, TimeframeAnalysis]) -> Dict:
        """Combina sinais de múltiplos timeframes"""
        if not timeframe_analyses:
            return {'signal': Signal.NEUTRAL, 'confidence': 0}
        
        weighted_signal = 0
        total_weight = 0
        total_confidence = 0
        
        for timeframe, analysis in timeframe_analyses.items():
            weight = self.timeframe_weights.get(timeframe, 0.1)
            weighted_signal += analysis.signal.value * weight * analysis.confidence
            total_weight += weight
            total_confidence += analysis.confidence * weight
        
        if total_weight == 0:
            return {'signal': Signal.NEUTRAL, 'confidence': 0}
        
        # Normaliza o sinal
        final_signal_value = weighted_signal / total_weight
        final_confidence = total_confidence / total_weight
        
        # Converte para enum Signal
        if final_signal_value >= 1.5:
            final_signal = Signal.STRONG_BUY
        elif final_signal_value >= 0.5:
            final_signal = Signal.BUY
        elif final_signal_value <= -1.5:
            final_signal = Signal.STRONG_SELL
        elif final_signal_value <= -0.5:
            final_signal = Signal.SELL
        else:
            final_signal = Signal.NEUTRAL
        
        # Calcula risk/reward baseado na análise
        risk_reward = self._calculate_risk_reward_ratio(timeframe_analyses)
        
        return {
            'signal': final_signal,
            'confidence': final_confidence,
            'risk_reward': risk_reward,
            'signal_strength': abs(final_signal_value)
        }
    
    def _generate_signal(self, current_price: float, rsi: float, macd: float,
                        ema_20: float, ema_50: float, support: float, 
                        resistance: float, trend: str, timeframe: Timeframe) -> Tuple[Signal, float]:
        """Gera sinal para um timeframe específico"""
        
        signals = []
        confidences = []
        
        # Sinal RSI
        if rsi is not None:
            if rsi < 30:
                signals.append(Signal.BUY.value)
                confidences.append(0.8)
            elif rsi > 70:
                signals.append(Signal.SELL.value)
                confidences.append(0.8)
            elif rsi < 40:
                signals.append(Signal.BUY.value * 0.5)
                confidences.append(0.4)
            elif rsi > 60:
                signals.append(Signal.SELL.value * 0.5)
                confidences.append(0.4)
        
        # Sinal MACD
        if macd is not None:
            if macd > 0:
                signals.append(Signal.BUY.value * 0.7)
                confidences.append(0.6)
            else:
                signals.append(Signal.SELL.value * 0.7)
                confidences.append(0.6)
        
        # Sinal EMA
        if ema_20 is not None and ema_50 is not None:
            if ema_20 > ema_50 and current_price > ema_20:
                signals.append(Signal.BUY.value)
                confidences.append(0.7)
            elif ema_20 < ema_50 and current_price < ema_20:
                signals.append(Signal.SELL.value)
                confidences.append(0.7)
        
        # Sinal Suporte/Resistência
        if support and resistance:
            distance_to_support = (current_price - support) / support
            distance_to_resistance = (resistance - current_price) / current_price
            
            if distance_to_support < 0.01:  # Próximo ao suporte
                signals.append(Signal.BUY.value)
                confidences.append(0.9)
            elif distance_to_resistance < 0.01:  # Próximo à resistência
                signals.append(Signal.SELL.value)
                confidences.append(0.9)
        
        # Sinal de Tendência
        if trend == "UPTREND":
            signals.append(Signal.BUY.value * 0.5)
            confidences.append(0.5)
        elif trend == "DOWNTREND":
            signals.append(Signal.SELL.value * 0.5)
            confidences.append(0.5)
        
        if not signals:
            return Signal.NEUTRAL, 0
        
        # Média ponderada dos sinais
        avg_signal = sum(s * c for s, c in zip(signals, confidences)) / sum(confidences)
        avg_confidence = sum(confidences) / len(confidences)
        
        # Ajusta confiança baseado no timeframe
        timeframe_multiplier = {
            Timeframe.M1: 0.7,
            Timeframe.M5: 0.8,
            Timeframe.M15: 0.9,
            Timeframe.M30: 1.0,
            Timeframe.H1: 1.1,
        }.get(timeframe, 1.0)
        
        final_confidence = min(avg_confidence * timeframe_multiplier, 1.0)
        
        # Converte para Signal enum
        if avg_signal >= 1.5:
            return Signal.STRONG_BUY, final_confidence
        elif avg_signal >= 0.5:
            return Signal.BUY, final_confidence
        elif avg_signal <= -1.5:
            return Signal.STRONG_SELL, final_confidence
        elif avg_signal <= -0.5:
            return Signal.SELL, final_confidence
        else:
            return Signal.NEUTRAL, final_confidence
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calcula RSI"""
        if len(prices) < period + 1:
            return None
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26) -> Optional[float]:
        """Calcula MACD"""
        if len(prices) < slow:
            return None
        
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        if ema_fast is None or ema_slow is None:
            return None
        
        return ema_fast - ema_slow
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calcula EMA"""
        if len(prices) < period:
            return None
        
        k = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * k) + (ema * (1 - k))
        
        return ema
    
    def _find_support_resistance(self, prices: List[float]) -> Tuple[Optional[float], Optional[float]]:
        """Encontra níveis de suporte e resistência"""
        if len(prices) < 20:
            return None, None
        
        # Usa últimos 50 preços para análise
        recent_prices = prices[-50:]
        
        # Suporte: mínimo dos últimos períodos
        support = min(recent_prices)
        
        # Resistência: máximo dos últimos períodos
        resistance = max(recent_prices)
        
        return support, resistance
    
    def _determine_trend(self, prices: List[float], ema_20: float, ema_50: float) -> str:
        """Determina tendência atual"""
        if len(prices) < 10 or ema_20 is None or ema_50 is None:
            return "SIDEWAYS"
        
        current_price = prices[-1]
        
        # Tendência baseada em EMAs
        if ema_20 > ema_50 and current_price > ema_20:
            return "UPTREND"
        elif ema_20 < ema_50 and current_price < ema_20:
            return "DOWNTREND"
        else:
            return "SIDEWAYS"
    
    def _calculate_stop_loss(self, analyses: Dict[Timeframe, TimeframeAnalysis], 
                           current_price: float) -> float:
        """Calcula stop loss baseado na análise multi-timeframe"""
        
        # Coleta suportes de diferentes timeframes
        supports = []
        for analysis in analyses.values():
            if analysis.support:
                supports.append(analysis.support)
        
        if supports:
            # Usa o suporte mais próximo, mas não muito próximo
            nearest_support = max(s for s in supports if s < current_price * 0.98)
            return max(nearest_support, current_price * 0.97)  # Mínimo 3% stop
        
        # Default: 2% stop loss
        return current_price * 0.98
    
    def _calculate_take_profit(self, analyses: Dict[Timeframe, TimeframeAnalysis], 
                             current_price: float) -> float:
        """Calcula take profit baseado na análise multi-timeframe"""
        
        # Coleta resistências de diferentes timeframes
        resistances = []
        for analysis in analyses.values():
            if analysis.resistance:
                resistances.append(analysis.resistance)
        
        if resistances:
            # Usa a resistência mais próxima
            nearest_resistance = min(r for r in resistances if r > current_price * 1.02)
            return min(nearest_resistance, current_price * 1.06)  # Máximo 6% profit
        
        # Default: 4% take profit
        return current_price * 1.04
    
    def _calculate_risk_reward_ratio(self, analyses: Dict[Timeframe, TimeframeAnalysis]) -> float:
        """Calcula ratio risco/retorno baseado na análise"""
        
        # Média das confianças
        confidences = [a.confidence for a in analyses.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Ratio baseado na confiança (maior confiança = maior ratio)
        base_ratio = 2.0
        confidence_multiplier = 0.5 + avg_confidence  # 0.5 a 1.5
        
        return base_ratio * confidence_multiplier
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Verifica se o cache ainda é válido"""
        if symbol not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[symbol]
    
    def get_trading_session_info(self) -> Dict:
        """Retorna informações sobre a sessão de trading atual"""
        now = datetime.now()
        
        # Detecta sessão de trading (simplificado)
        hour = now.hour
        
        if 9 <= hour < 16:
            session = "US_SESSION"
            volatility = "HIGH"
        elif 2 <= hour < 9:
            session = "ASIA_SESSION"
            volatility = "MEDIUM"
        elif 16 <= hour < 24:
            session = "EUROPE_SESSION"
            volatility = "HIGH"
        else:
            session = "LOW_LIQUIDITY"
            volatility = "LOW"
        
        return {
            'session': session,
            'expected_volatility': volatility,
            'recommended_timeframes': self._get_recommended_timeframes(session)
        }
    
    def _get_recommended_timeframes(self, session: str) -> List[Timeframe]:
        """Retorna timeframes recomendados para cada sessão"""
        if session in ["US_SESSION", "EUROPE_SESSION"]:
            return [Timeframe.M5, Timeframe.M15, Timeframe.M30, Timeframe.H1]
        elif session == "ASIA_SESSION":
            return [Timeframe.M15, Timeframe.M30, Timeframe.H1]
        else:
            return [Timeframe.M30, Timeframe.H1]

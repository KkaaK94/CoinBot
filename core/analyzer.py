"""
기술적 분석 엔진 (1/3)
다양한 기술적 지표 계산 및 점수 산출
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from config.settings import settings
from utils.logger import Logger

@dataclass
class TechnicalIndicators:
    """기술적 지표 클래스"""
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    sma_short: float
    sma_long: float
    ema_short: float
    ema_long: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    volume_sma: float
    stoch_k: float
    stoch_d: float

@dataclass
class AnalysisResult:
    """분석 결과 클래스"""
    ticker: str
    timeframe: str
    timestamp: datetime
    
    # 기술적 지표
    indicators: TechnicalIndicators
    
    # 점수 시스템
    rsi_score: float
    macd_score: float
    volume_score: float
    momentum_score: float
    volatility_score: float
    total_score: float
    
    # 신호
    trend_direction: str  # UP, DOWN, SIDEWAYS
    signal_strength: float  # 0.0 ~ 1.0
    confidence: float  # 0.0 ~ 1.0
    
    # 추천 액션
    recommended_action: str  # BUY, SELL, HOLD
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class TechnicalAnalyzer:
    """기술적 분석기 클래스"""
    
    def __init__(self):
        self.logger = Logger()
        self.settings = settings
        self.analysis_config = settings.get_analysis_config()
        
        self.logger.info("기술적 분석기 초기화 완료")
    
    def analyze(self, df: pd.DataFrame, ticker: str, timeframe: str) -> Optional[AnalysisResult]:
        """종합 기술적 분석"""
        try:
            if df is None or len(df) < 50:
                self.logger.warning(f"분석용 데이터 부족: {ticker} {timeframe}")
                return None
            
            # 1. 기술적 지표 계산
            indicators = self._calculate_indicators(df)
            
            # 2. 점수 계산
            scores = self._calculate_scores(df, indicators)
            
            # 3. 신호 분석
            signals = self._analyze_signals(df, indicators)
            
            # 4. 결과 통합
            result = AnalysisResult(
                ticker=ticker,
                timeframe=timeframe,
                timestamp=datetime.now(),
                indicators=indicators,
                **scores,
                **signals
            )
            
            # 5. 매매 추천
            self._generate_recommendation(result, df)
            
            return result
            
        except Exception as e:
            self.logger.error(f"기술적 분석 실패 {ticker}: {e}")
            return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """기술적 지표 계산"""
        try:
            close = df['close']
            high = df['high']
            low = df['low']
            volume = df['volume']
            
            # RSI 계산
            rsi = self._calculate_rsi(close, self.analysis_config['rsi_period'])
            
            # MACD 계산
            macd_data = self._calculate_macd(
                close,
                self.analysis_config['macd_fast'],
                self.analysis_config['macd_slow'],
                self.analysis_config['macd_signal']
            )
            
            # 이동평균 계산
            sma_short = self._calculate_sma(close, self.analysis_config['ma_short'])
            sma_long = self._calculate_sma(close, self.analysis_config['ma_long'])
            ema_short = self._calculate_ema(close, self.analysis_config['ma_short'])
            ema_long = self._calculate_ema(close, self.analysis_config['ma_long'])
            
            # 볼린저 밴드
            bb_data = self._calculate_bollinger_bands(close, 20, 2)
            
            # 스토캐스틱
            stoch_data = self._calculate_stochastic(high, low, close, 14, 3)
            
            # 거래량 이동평균
            volume_sma = self._calculate_sma(volume, 20)
            
            return TechnicalIndicators(
                rsi=rsi,
                macd=macd_data['macd'],
                macd_signal=macd_data['signal'],
                macd_histogram=macd_data['histogram'],
                sma_short=sma_short,
                sma_long=sma_long,
                ema_short=ema_short,
                ema_long=ema_long,
                bb_upper=bb_data['upper'],
                bb_middle=bb_data['middle'],
                bb_lower=bb_data['lower'],
                volume_sma=volume_sma,
                stoch_k=stoch_data['%K'],
                stoch_d=stoch_data['%D']
            )
            
        except Exception as e:
            self.logger.error(f"기술적 지표 계산 실패: {e}")
            # 기본값 반환
            return TechnicalIndicators(
                rsi=50, macd=0, macd_signal=0, macd_histogram=0,
                sma_short=0, sma_long=0, ema_short=0, ema_long=0,
                bb_upper=0, bb_middle=0, bb_lower=0, volume_sma=0,
                stoch_k=50, stoch_d=50
            )
        def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
             """RSI 계산"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
        except:
            return 50.0
    
    def _calculate_macd(self, prices: pd.Series, fast: int, slow: int, signal: int) -> Dict[str, float]:
        """MACD 계산"""
        try:
            ema_fast = self._calculate_ema(prices, fast)
            ema_slow = self._calculate_ema(prices, slow)
            macd_line = ema_fast - ema_slow
            
            # Signal line
            macd_series = pd.Series([macd_line] * len(prices), index=prices.index)
            signal_line = self._calculate_ema(macd_series, signal)
            histogram = macd_line - signal_line
            
            return {
                'macd': float(macd_line) if not pd.isna(macd_line) else 0.0,
                'signal': float(signal_line) if not pd.isna(signal_line) else 0.0,
                'histogram': float(histogram) if not pd.isna(histogram) else 0.0
            }
        except:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
    
    def _calculate_sma(self, prices: pd.Series, period: int) -> float:
        """단순 이동평균 계산"""
        try:
            sma = prices.rolling(window=period).mean()
            return float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else 0.0
        except:
            return 0.0
    
    def _calculate_ema(self, prices: pd.Series, period: int) -> float:
        """지수 이동평균 계산"""
        try:
            ema = prices.ewm(span=period).mean()
            return float(ema.iloc[-1]) if not pd.isna(ema.iloc[-1]) else 0.0
        except:
            return 0.0
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int, std_dev: float) -> Dict[str, float]:
        """볼린저 밴드 계산"""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            
            return {
                'upper': float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else 0.0,
                'middle': float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else 0.0,
                'lower': float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else 0.0
            }
        except:
            return {'upper': 0.0, 'middle': 0.0, 'lower': 0.0}
    
    def _calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, k_period: int, d_period: int) -> Dict[str, float]:
        """스토캐스틱 계산"""
        try:
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            
            k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            d_percent = k_percent.rolling(window=d_period).mean()
            
            return {
                '%K': float(k_percent.iloc[-1]) if not pd.isna(k_percent.iloc[-1]) else 50.0,
                '%D': float(d_percent.iloc[-1]) if not pd.isna(d_percent.iloc[-1]) else 50.0
            }
        except:
            return {'%K': 50.0, '%D': 50.0}
    
    def _calculate_scores(self, df: pd.DataFrame, indicators: TechnicalIndicators) -> Dict[str, float]:
        """점수 계산 (0-100점)"""
        try:
            # 1. RSI 점수 (25점 만점)
            rsi_score = self._score_rsi(indicators.rsi)
            
            # 2. MACD 점수 (25점 만점)
            macd_score = self._score_macd(indicators, df['close'])
            
            # 3. 거래량 점수 (20점 만점)
            volume_score = self._score_volume(df['volume'], indicators.volume_sma)
            
            # 4. 모멘텀 점수 (15점 만점)
            momentum_score = self._score_momentum(df['close'], indicators)
            
            # 5. 변동성 점수 (15점 만점)
            volatility_score = self._score_volatility(df['close'])
            
            # 총점 계산
            total_score = rsi_score + macd_score + volume_score + momentum_score + volatility_score
            
            return {
                'rsi_score': rsi_score,
                'macd_score': macd_score,
                'volume_score': volume_score,
                'momentum_score': momentum_score,
                'volatility_score': volatility_score,
                'total_score': min(max(total_score, 0), 100)
            }
            
        except Exception as e:
            self.logger.error(f"점수 계산 실패: {e}")
            return {
                'rsi_score': 0, 'macd_score': 0, 'volume_score': 0,
                'momentum_score': 0, 'volatility_score': 0, 'total_score': 0
            }
    
    def _score_rsi(self, rsi: float) -> float:
        """RSI 점수 (0-25점)"""
        if 20 <= rsi <= 35:      # 강한 매수 구간
            return 25
        elif 35 < rsi <= 45:     # 약한 매수 구간
            return 20
        elif 45 < rsi <= 55:     # 중립 구간
            return 10
        elif 55 < rsi <= 70:     # 약한 매도 구간
            return 5
        else:                    # 과매수/과매도
            return 0
    
    def _score_macd(self, indicators: TechnicalIndicators, prices: pd.Series) -> float:
        """MACD 점수 (0-25점)"""
        score = 0
        
        # 골든크로스/데드크로스 확인
        if indicators.macd > indicators.macd_signal:
            score += 15  # 골든크로스
        
       # 히스토그램 증가 확인
        if indicators.macd_histogram > 0:
            score += 10  # 상승 모멘텀
        
        return min(score, 25)
    
    def _score_volume(self, volume: pd.Series, volume_sma: float) -> float:
        """거래량 점수 (0-20점)"""
        try:
            recent_volume = volume.iloc[-5:].mean()
            volume_ratio = recent_volume / volume_sma if volume_sma > 0 else 1
            
            if volume_ratio >= 2.0:
                return 20
            elif volume_ratio >= 1.5:
                return 15
            elif volume_ratio >= 1.2:
                return 10
            elif volume_ratio >= 0.8:
                return 5
            else:
                return 0
        except:
            return 0
    
    def _score_momentum(self, prices: pd.Series, indicators: TechnicalIndicators) -> float:
        """모멘텀 점수 (0-15점)"""
        try:
            score = 0
            current_price = prices.iloc[-1]
            
            # 이동평균 배열 확인
            if current_price > indicators.sma_short > indicators.sma_long:
                score += 10
            elif current_price > indicators.sma_short:
                score += 5
            
            # 최근 추세 확인
            price_change = (prices.iloc[-1] - prices.iloc[-5]) / prices.iloc[-5]
            if price_change > 0.02:      # 2% 이상 상승
                score += 5
            elif price_change > 0:       # 상승
                score += 2
            
            return min(score, 15)
        except:
            return 0
    
    def _score_volatility(self, prices: pd.Series) -> float:
        """변동성 점수 (0-15점)"""
        try:
            returns = prices.pct_change().dropna()
            volatility = returns.iloc[-10:].std() * 100
            
            if 1.0 <= volatility <= 3.0:     # 적정 변동성
                return 15
            elif 3.0 < volatility <= 5.0:    # 높은 변동성
                return 10
            elif 0.5 <= volatility < 1.0:    # 낮은 변동성
                return 5
            else:                            # 극단적 변동성
                return 0
        except:
            return 0
    
    def _analyze_signals(self, df: pd.DataFrame, indicators: TechnicalIndicators) -> Dict[str, any]:
        """신호 분석"""
        try:
            current_price = df['close'].iloc[-1]
            
            # 1. 트렌드 방향 결정
            trend_direction = self._determine_trend(current_price, indicators)
            
            # 2. 신호 강도 계산
            signal_strength = self._calculate_signal_strength(df, indicators)
            
            # 3. 신뢰도 계산
            confidence = self._calculate_confidence(df, indicators)
            
            return {
                'trend_direction': trend_direction,
                'signal_strength': signal_strength,
                'confidence': confidence
            }
            
        except Exception as e:
            self.logger.error(f"신호 분석 실패: {e}")
            return {
                'trend_direction': 'SIDEWAYS',
                'signal_strength': 0.0,
                'confidence': 0.0
            }
    
    def _determine_trend(self, current_price: float, indicators: TechnicalIndicators) -> str:
        """트렌드 방향 결정"""
        try:
            conditions = []
            
            # 이동평균 기준
            if current_price > indicators.sma_short > indicators.sma_long:
                conditions.append('UP')
            elif current_price < indicators.sma_short < indicators.sma_long:
                conditions.append('DOWN')
            else:
                conditions.append('SIDEWAYS')
            
            # MACD 기준
            if indicators.macd > indicators.macd_signal and indicators.macd_histogram > 0:
                conditions.append('UP')
            elif indicators.macd < indicators.macd_signal and indicators.macd_histogram < 0:
                conditions.append('DOWN')
            else:
                conditions.append('SIDEWAYS')
            
            # 볼린저 밴드 기준
            if current_price > indicators.bb_middle:
                conditions.append('UP')
            elif current_price < indicators.bb_middle:
                conditions.append('DOWN')
            else:
                conditions.append('SIDEWAYS')
            
            # 다수결 원칙
            up_count = conditions.count('UP')
            down_count = conditions.count('DOWN')
            
            if up_count > down_count:
                return 'UP'
            elif down_count > up_count:
                return 'DOWN'
            else:
                return 'SIDEWAYS'
                
        except:
            return 'SIDEWAYS'
    
    def _calculate_signal_strength(self, df: pd.DataFrame, indicators: TechnicalIndicators) -> float:
        """신호 강도 계산 (0.0 - 1.0)"""
        try:
            strength_factors = []
            
            # RSI 강도
            rsi_strength = abs(indicators.rsi - 50) / 50
            strength_factors.append(rsi_strength)
            
            # MACD 강도
            macd_strength = abs(indicators.macd_histogram) / (abs(indicators.macd) + 0.001)
            strength_factors.append(min(macd_strength, 1.0))
            
            # 거래량 강도
            volume_ratio = df['volume'].iloc[-5:].mean() / df['volume'].mean()
            volume_strength = min(volume_ratio / 2, 1.0)
            strength_factors.append(volume_strength)
            
            # 평균 계산
            return np.mean(strength_factors)
            
        except:
            return 0.0
    
    def _calculate_confidence(self, df: pd.DataFrame, indicators: TechnicalIndicators) -> float:
        """신뢰도 계산 (0.0 - 1.0)"""
        try:
            confidence_factors = []
            
            # 데이터 충분성
            data_confidence = min(len(df) / 100, 1.0)
            confidence_factors.append(data_confidence)
            
            # 지표 일관성
            trend_consistency = self._check_trend_consistency(indicators)
            confidence_factors.append(trend_consistency)
            
            # 시장 안정성
            volatility = df['close'].pct_change().std()
            stability = max(0, 1 - (volatility * 10))
            confidence_factors.append(stability)
            
            return np.mean(confidence_factors)
            
        except:
            return 0.0
    
    def _check_trend_consistency(self, indicators: TechnicalIndicators) -> float:
        """트렌드 일관성 체크"""
        try:
            trends = []
            
            # RSI 트렌드
            if indicators.rsi < 40:
                trends.append('UP')
            elif indicators.rsi > 60:
                trends.append('DOWN')
            else:
                trends.append('NEUTRAL')
            
            # MACD 트렌드
            if indicators.macd > indicators.macd_signal:
                trends.append('UP')
            else:
                trends.append('DOWN')
            
            # 일관성 계산
            up_count = trends.count('UP')
            down_count = trends.count('DOWN')
            
            if up_count > down_count or down_count > up_count:
                return 0.8  # 일관성 있음
            else:
                return 0.4  # 혼재
                
        except:
            return 0.0
    
    def _generate_recommendation(self, result: AnalysisResult, df: pd.DataFrame):
        """매매 추천 생성"""
        try:
            current_price = df['close'].iloc[-1]
            
            # 기본 조건 확인
            if result.total_score >= self.settings.analysis.min_score_threshold and result.confidence >= 0.6:
                if result.trend_direction == 'UP' and result.signal_strength >= 0.5:
                    result.recommended_action = 'BUY'
                    result.entry_price = current_price
                    result.stop_loss = current_price * (1 - self.settings.trading.stop_loss_ratio)
                    result.take_profit = current_price * (1 + self.settings.trading.take_profit_ratio)
                
                elif result.trend_direction == 'DOWN' and result.signal_strength >= 0.5:
                    result.recommended_action = 'SELL'
                    result.entry_price = current_price
                    result.stop_loss = current_price * (1 + self.settings.trading.stop_loss_ratio)
                    result.take_profit = current_price * (1 - self.settings.trading.take_profit_ratio)
                
                else:
                    result.recommended_action = 'HOLD'
            else:
                result.recommended_action = 'HOLD'
                
        except Exception as e:
            self.logger.error(f"매매 추천 생성 실패: {e}")
            result.recommended_action = 'HOLD'
    
    def batch_analyze(self, data_dict: Dict[str, pd.DataFrame], ticker: str) -> Dict[str, AnalysisResult]:
        """다중 시간봉 일괄 분석"""
        results = {}
        
        for timeframe, df in data_dict.items():
            result = self.analyze(df, ticker, timeframe)
            if result:
                results[timeframe] = result
        
        return results
    
    def get_analysis_summary(self, results: Dict[str, AnalysisResult]) -> Dict[str, any]:
        """분석 결과 요약"""
        try:
            if not results:
                return {}
            
            # 평균 점수 계산
            total_scores = [r.total_score for r in results.values()]
            avg_score = np.mean(total_scores)
            
            # 트렌드 일관성
            trends = [r.trend_direction for r in results.values()]
            trend_consistency = len(set(trends)) == 1
            
            # 신뢰도 평균
            confidences = [r.confidence for r in results.values()]
            avg_confidence = np.mean(confidences)
            
            # 추천 액션 결정
            actions = [r.recommended_action for r in results.values()]
            recommended_action = max(set(actions), key=actions.count)
            
            return {
                'avg_score': avg_score,
                'trend_consistency': trend_consistency,
                'avg_confidence': avg_confidence,
                'recommended_action': recommended_action,
                'timeframe_count': len(results),
                'analysis_timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"분석 요약 실패: {e}")
            return {}
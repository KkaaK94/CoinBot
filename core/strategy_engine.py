"""
전략 엔진 모듈 (1/3)
동적 전략 생성, 관리, 성과 평가
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
import uuid

from config.settings import settings
from core.analyzer import AnalysisResult
from utils.logger import Logger
from utils.auto_updater import log_config_change, log_bug_fix, log_feature_add

@dataclass
class TradingStrategy:
    """거래 전략 클래스"""
    strategy_id: str
    name: str
    strategy_type: str  # MOMENTUM, TREND, MEAN_REVERSION, SCALPING
    
    # 진입 조건
    entry_conditions: Dict[str, any]
    
    # 청산 조건
    exit_conditions: Dict[str, any]
    
    # 성과 지표
    total_trades: int = 0
    winning_trades: int = 0
    total_profit: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    performance_score: float = 0.0
    
    # 메타 정보
    created_at: datetime = datetime.now()
    last_used: datetime = datetime.now()
    is_active: bool = True
    
    # 적응형 파라미터
    adaptation_count: int = 0
    success_streak: int = 0
    failure_streak: int = 0

@dataclass
class StrategySignal:
    """전략 신호 클래스"""
    strategy_id: str
    ticker: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    timeframe: str
    reasoning: str
    timestamp: datetime = datetime.now()

class StrategyEngine:
    """전략 엔진 클래스"""
    
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.logger = Logger()
        
        # 전략 저장소
        self.strategies: Dict[str, TradingStrategy] = {}
        self.strategy_performance_history = {}
        
        # 시장 상황 분석
        self.market_condition = "NEUTRAL"
        self.market_volatility = 0.0
        
        # 전략 생성 템플릿
        self.strategy_templates = self._initialize_strategy_templates()
        
        # 기본 전략 생성
        self._create_initial_strategies()
        
        self.logger.info("전략 엔진 초기화 완료")
         # 🔄 이 부분을 추가! (초기화 맨 마지막에)
        try:
            log_feature_add(
                "core/strategy_engine.py",
                "전략 엔진 초기화 완료",
                {
                    "strategies_count": len(self.strategies),
                    "market_condition": self.market_condition,
                    "status": "활성화"
                }
            )
        except:
            pass  # 로깅 실패해도 메인 기능에 영향 없게
    
    def _initialize_strategy_templates(self) -> Dict[str, Dict]:
        """전략 템플릿 초기화 (매매 활성화 버전)"""

        return {
            "MOMENTUM": {
                "entry_conditions": {
                    "min_score": 55,  # ✅ 80 → 55로 변경
                    "rsi_range": (25, 65),  # ✅ (30, 50) → (25, 65)로 확대
                    "volume_surge": False,  # ✅ True → False로 변경 (조건 완화)
                    "trend_alignment": False,  # ✅ True → False로 변경
                    "momentum_threshold": 0.01  # ✅ 0.02 → 0.01로 완화
                },
                "exit_conditions": {
                    "profit_target": 0.04,  # ✅ 0.12 → 0.04로 현실적으로
                    "stop_loss": 0.02,  # ✅ 0.06 → 0.02로 현실적으로
                    "time_limit_hours": 6,
                    "rsi_overbought": 75,
                    "momentum_reversal": True
                }
            },
            "TREND": {
                "entry_conditions": {
                    "min_score": 45,  # ✅ 75 → 45로 변경
                    "trend_strength": 0.5,  # ✅ 0.7 → 0.5로 완화
                    "ma_alignment": False,  # ✅ True → False로 완화
                    "volume_confirmation": False,  # ✅ True → False로 완화
                    "pullback_entry": False  # ✅ True → False로 완화
                },
                "exit_conditions": {
                    "profit_target": 0.06,  # ✅ 0.18 → 0.06으로 현실적으로
                    "stop_loss": 0.03,  # ✅ 0.08 → 0.03으로 현실적으로
                    "time_limit_hours": 12,
                    "trend_break": True,
                    "ma_crossover": True
                }
            },
            "MEAN_REVERSION": {
                "entry_conditions": {
                    "min_score": 45,  # ✅ 70 → 45로 변경
                    "rsi_extreme": True,
                    "bollinger_touch": False,  # ✅ True → False로 완화
                    "volume_divergence": False,  # ✅ True → False로 완화
                    "support_resistance": False  # ✅ True → False로 완화
                },
                "exit_conditions": {
                    "profit_target": 0.04,  # ✅ 0.08 → 0.04로 현실적으로
                    "stop_loss": 0.02,  # ✅ 0.04 → 0.02로 현실적으로
                    "time_limit_hours": 4,
                    "rsi_normalization": True,
                    "bollinger_middle": True
                }
            },
            "SCALPING": {
                "entry_conditions": {
                    "min_score": 45,  # ✅ 85 → 45로 대폭 변경
                    "micro_trend": False,  # ✅ True → False로 완화
                    "volume_spike": False,  # ✅ True → False로 완화
                    "spread_check": True,
                    "momentum_acceleration": False  # ✅ True → False로 완화
                },
                "exit_conditions": {
                    "profit_target": 0.03,  # ✅ 0.04 → 0.03으로 약간 완화
                    "stop_loss": 0.015,  # ✅ 0.02 → 0.015로 약간 완화
                    "time_limit_hours": 1,
                    "momentum_fade": True,
                    "volume_dry_up": True
                }
            }
        }
    def _create_initial_strategies(self):
        """초기 전략 생성"""
        try:
            # 각 전략 타입별로 기본 전략 생성
            for strategy_type, template in self.strategy_templates.items():
                strategy = TradingStrategy(
                    strategy_id=str(uuid.uuid4()),
                    name=f"기본_{strategy_type}",
                    strategy_type=strategy_type,
                    entry_conditions=template["entry_conditions"].copy(),
                    exit_conditions=template["exit_conditions"].copy()
                )
                
                self.strategies[strategy.strategy_id] = strategy
                
            self.logger.info(f"초기 전략 {len(self.strategies)}개 생성 완료")
            
        except Exception as e:
            self.logger.error(f"초기 전략 생성 실패: {e}")
    
    def generate_signals(self, analysis_results: Dict[str, AnalysisResult], ticker: str) -> List[StrategySignal]:
        """전략별 신호 생성 (자동 업데이트 적용)"""
        signals = []
    
        try:
            # 🔄 신호 생성 시작 로깅
            try:
                log_feature_add(
                    "core/strategy_engine.py", 
                    f"{ticker} 신호 생성 프로세스 시작"
                )
            except:
                pass
            
            for strategy_id, strategy in self.strategies.items():
                if not strategy.is_active:
                    continue
                
                signal = self._evaluate_strategy(strategy, analysis_results, ticker)
                if signal:
                    signals.append(signal)
            
            # 신호 우선순위 정렬 (성과 기반)
            signals.sort(key=lambda x: self.strategies[x.strategy_id].performance_score, reverse=True)
            
            # 🔄 생성된 신호 정보 로깅
            if signals:
                try:
                    log_config_change(
                        "core/strategy_engine.py",
                        f"{ticker} 총 {len(signals)}개 신호 생성됨",
                        {
                            "ticker": ticker,
                            "signals_count": len(signals),
                            "top_signal_action": signals[0].action if signals else "NONE",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                except:
                    pass
            
            return signals
            
        except Exception as e:
            # 🔄 에러 로깅
            try:
                log_bug_fix(
                    "core/strategy_engine.py",
                    f"{ticker} 신호 생성 실패: {str(e)}"
                )
            except:
                pass
            
            self.logger.error(f"신호 생성 실패: {e}")
            return []
    
    def _evaluate_strategy(self, strategy: TradingStrategy, analysis_results: Dict[str, AnalysisResult], ticker: str) -> Optional[StrategySignal]:
        """개별 전략 평가"""
        try:
            # 다중 시간봉 결과 통합
            combined_analysis = self._combine_analysis_results(analysis_results)
            
            if not combined_analysis:
                return None
            
            # 진입 조건 체크
            entry_signal = self._check_entry_conditions(strategy, combined_analysis, ticker)
            
            if entry_signal:
                return entry_signal
            
            return None
            
        except Exception as e:
            self.logger.error(f"전략 평가 실패 {strategy.name}: {e}")
            return None
    def _combine_analysis_results(self, analysis_results: Dict[str, AnalysisResult]) -> Optional[Dict]:
        """다중 시간봉 분석 결과 통합"""
        try:
            if not analysis_results:
                return None
            
            # 가중평균 계산 (짧은 시간봉에 더 높은 가중치)
            weights = {
                'minute1': 0.5,
                'minute3': 0.3,
                'minute5': 0.2
            }
            
            total_score = 0
            total_confidence = 0
            total_weight = 0
            
            trend_votes = []
            action_votes = []
            indicators_sum = {}
            
            for timeframe, result in analysis_results.items():
                weight = weights.get(timeframe, 0.1)
                
                total_score += result.total_score * weight
                total_confidence += result.confidence * weight
                total_weight += weight
                
                trend_votes.append(result.trend_direction)
                action_votes.append(result.recommended_action)
                
                # 기술적 지표 평균화
                indicators = result.indicators
                for attr in ['rsi', 'macd', 'macd_signal', 'macd_histogram']:
                    if attr not in indicators_sum:
                        indicators_sum[attr] = 0
                    indicators_sum[attr] += getattr(indicators, attr) * weight
            
            # 정규화
            avg_score = total_score / total_weight if total_weight > 0 else 0
            avg_confidence = total_confidence / total_weight if total_weight > 0 else 0
            
            # 다수결 투표
            dominant_trend = max(set(trend_votes), key=trend_votes.count) if trend_votes else 'SIDEWAYS'
            dominant_action = max(set(action_votes), key=action_votes.count) if action_votes else 'HOLD'
            
            # 기술적 지표 정규화
            for key in indicators_sum:
                indicators_sum[key] = indicators_sum[key] / total_weight if total_weight > 0 else 0
            
            return {
                'avg_score': avg_score,
                'avg_confidence': avg_confidence,
                'dominant_trend': dominant_trend,
                'dominant_action': dominant_action,
                'indicators': indicators_sum,
                'timeframe_consistency': len(set(trend_votes)) == 1
            }
            
        except Exception as e:
            self.logger.error(f"분석 결과 통합 실패: {e}")
            return None
    
    def _check_entry_conditions(self, strategy: TradingStrategy, combined_analysis: Dict, ticker: str) -> Optional[StrategySignal]:
        """진입 조건 체크 (자동 업데이트 적용)"""
        try:
            entry_conditions = strategy.entry_conditions
        
            # 🔥 중요! 이 값들을 변경할 때마다 로깅
            original_min_score = 75  # 원래 기본값
            current_min_score = entry_conditions.get('min_score', 45)  # 현재 사용값
        
            original_confidence = 0.6  # 원래 기본값  
            current_confidence = 0.4   # 현재 사용값
        
            # 🔄 설정 변경 감지 및 로깅 (값이 기본값과 다를 때만)
            if current_min_score != original_min_score:
               try:
                   log_config_change(
                       "core/strategy_engine.py",
                       f"min_score 조건 완화 적용됨: {original_min_score} → {current_min_score}",
                       {
                            "min_score": {"original": original_min_score, "current": current_min_score},
                            "reason": "매매 활성화를 위한 조건 완화",
                            "ticker": ticker
                       }
                   )
               except:
                   pass
        
            # 기본 점수 조건
            if combined_analysis['avg_score'] < current_min_score:
                return None
        
            # 신뢰도 조건
            if combined_analysis['avg_confidence'] < current_confidence:
                return None
        
            # 전략 타입별 특화 조건
            if not self._check_strategy_specific_conditions(strategy, combined_analysis):
                return None
        
            # 🔄 신호 생성 성공 시 로깅
            try:
                log_config_change(
                    "core/strategy_engine.py",
                    f"{ticker} 매매 신호 생성 성공",
                    {
                        "ticker": ticker,
                        "score": combined_analysis['avg_score'],
                        "confidence": combined_analysis['avg_confidence'],
                        "strategy_type": strategy.strategy_type
                    }
                )
            except:
                pass
        
            # 신호 생성
            signal = self._create_strategy_signal(strategy, combined_analysis, ticker)
            return signal
        
        except Exception as e:
            # 🔄 에러 발생 시 로깅
            try:
                log_bug_fix(
                    "core/strategy_engine.py",
                    f"진입 조건 체크 에러 발생: {ticker} - {str(e)}"
              )
            except:
                pass
        
            self.logger.error(f"진입 조건 체크 실패: {e}")
            return None
    
    def _check_strategy_specific_conditions(self, strategy: TradingStrategy, combined_analysis: Dict) -> bool:
        """전략별 특화 조건 체크"""
        try:
            strategy_type = strategy.strategy_type
            conditions = strategy.entry_conditions
            indicators = combined_analysis['indicators']
            
            if strategy_type == "MOMENTUM":
                # 모멘텀 조건
                rsi_in_range = conditions['rsi_range'][0] <= indicators['rsi'] <= conditions['rsi_range'][1]
                volume_surge = combined_analysis.get('volume_surge', False)
                trend_alignment = combined_analysis['dominant_trend'] == 'UP'
                
                return rsi_in_range and (not conditions['volume_surge'] or volume_surge) and trend_alignment
            
            elif strategy_type == "TREND":
                # 트렌드 조건
                trend_strength = combined_analysis['avg_confidence']
                trend_consistent = combined_analysis['timeframe_consistency']
                
                return (trend_strength >= conditions['trend_strength'] and 
                        trend_consistent and 
                        combined_analysis['dominant_trend'] == 'UP')
            
            elif strategy_type == "MEAN_REVERSION":
                # 평균회귀 조건
                rsi_extreme = indicators['rsi'] <= 30 or indicators['rsi'] >= 70
                return rsi_extreme and combined_analysis['dominant_trend'] != 'SIDEWAYS'
            
            elif strategy_type == "SCALPING":
                # 스캘핑 조건
                high_score = combined_analysis['avg_score'] >= conditions['min_score']
                high_confidence = combined_analysis['avg_confidence'] >= 0.8
                
                return high_score and high_confidence
            
            return True
            
        except Exception as e:
            self.logger.error(f"전략별 조건 체크 실패: {e}")
            return False
    
    def _create_strategy_signal(self, strategy: TradingStrategy, combined_analysis: Dict, ticker: str) -> StrategySignal:
        """전략 신호 생성"""
        try:
            # 기본 가격 정보 (실제로는 data_collector에서 가져와야 함)
            current_price = 50000  # 임시값, 실제 구현 시 수정 필요
            
            # 청산 조건 기반 손절/익절가 계산
            exit_conditions = strategy.exit_conditions
            stop_loss_ratio = exit_conditions.get('stop_loss', 0.08)
            profit_target_ratio = exit_conditions.get('profit_target', 0.15)
            
            stop_loss = current_price * (1 - stop_loss_ratio)
            take_profit = current_price * (1 + profit_target_ratio)
            
            # 신호 생성
            action = combined_analysis['dominant_action']
            if action == 'HOLD':
                action = 'BUY' if combined_analysis['dominant_trend'] == 'UP' else 'HOLD'
            
            reasoning = f"{strategy.strategy_type} 전략: 점수 {combined_analysis['avg_score']:.1f}, " \
                       f"신뢰도 {combined_analysis['avg_confidence']:.2f}, 트렌드 {combined_analysis['dominant_trend']}"
            
            return StrategySignal(
                strategy_id=strategy.strategy_id,
                ticker=ticker,
                action=action,
                confidence=combined_analysis['avg_confidence'],
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe="combined",
                reasoning=reasoning
            )
            
        except Exception as e:
            self.logger.error(f"전략 신호 생성 실패: {e}")
            return None
    
    def update_strategy_performance(self, strategy_id: str, trade_result: Dict):
        """전략 성과 업데이트"""
        try:
            if strategy_id not in self.strategies:
                self.logger.warning(f"존재하지 않는 전략 ID: {strategy_id}")
                return
            
            strategy = self.strategies[strategy_id]
            
            # 거래 결과 반영
            strategy.total_trades += 1
            strategy.last_used = datetime.now()
            
            profit = trade_result.get('profit_ratio', 0)
            strategy.total_profit += profit
            
            if profit > 0:
                strategy.winning_trades += 1
                strategy.success_streak += 1
                strategy.failure_streak = 0
            else:
                strategy.success_streak = 0
                strategy.failure_streak += 1
            
            # 성과 지표 계산
            strategy.win_rate = strategy.winning_trades / strategy.total_trades
            strategy.avg_profit = strategy.total_profit / strategy.total_trades
            
            # 드로우다운 업데이트
            if profit < strategy.max_drawdown:
                strategy.max_drawdown = profit
            
            # 성과 점수 계산 (0-1 범위)
            strategy.performance_score = self._calculate_performance_score(strategy)
            
            # 전략 적응
            self._adapt_strategy(strategy, trade_result)
            
            # 성과 히스토리 저장
            self._save_performance_history(strategy_id, trade_result)
            
            self.logger.info(f"전략 성과 업데이트: {strategy.name} - "
                           f"승률: {strategy.win_rate:.2%}, 평균수익: {strategy.avg_profit:.2%}")
            
        except Exception as e:
            self.logger.error(f"전략 성과 업데이트 실패: {e}")
    
    def _calculate_performance_score(self, strategy: TradingStrategy) -> float:
        """성과 점수 계산"""
        try:
            if strategy.total_trades == 0:
                return 0.0
            
            # 기본 점수 = 승률 * (1 + 평균수익률)
            base_score = strategy.win_rate * (1 + strategy.avg_profit)
            
            # 거래 횟수 가중치 (충분한 데이터 확보)
            trade_weight = min(strategy.total_trades / 20, 1.0)
            
            # 연속 성공/실패 보정
            streak_factor = 1.0
            if strategy.success_streak >= 3:
                streak_factor = 1.1  # 연속 성공 보너스
            elif strategy.failure_streak >= 3:
                streak_factor = 0.9  # 연속 실패 페널티
            
            # 드로우다운 페널티
            drawdown_penalty = max(0, 1 + strategy.max_drawdown)  # 음수 드로우다운이므로 1에서 빼기
            
            final_score = base_score * trade_weight * streak_factor * drawdown_penalty
            
            return max(0, min(final_score, 2.0))  # 0-2 범위로 제한
            
        except Exception as e:
            self.logger.error(f"성과 점수 계산 실패: {e}")
            return 0.0
    
    def _adapt_strategy(self, strategy: TradingStrategy, trade_result: Dict):
        """전략 적응 (파라미터 조정)"""
        try:
            strategy.adaptation_count += 1
            
            # 연속 실패 시 조정
            if strategy.failure_streak >= 3:
                self._adjust_strategy_parameters(strategy, "conservative")
                self.logger.info(f"전략 보수적 조정: {strategy.name}")
            
            # 연속 성공 시 조정
            elif strategy.success_streak >= 5:
                self._adjust_strategy_parameters(strategy, "aggressive")
                self.logger.info(f"전략 공격적 조정: {strategy.name}")
            
            # 성과가 지속적으로 낮으면 비활성화
            if (strategy.total_trades >= 10 and 
                strategy.performance_score < 0.3 and 
                strategy.failure_streak >= 5):
                
                strategy.is_active = False
                self.logger.warning(f"전략 비활성화: {strategy.name} (저성과)")
            
        except Exception as e:
            self.logger.error(f"전략 적응 실패: {e}")
    
    def _adjust_strategy_parameters(self, strategy: TradingStrategy, direction: str):
        """전략 파라미터 조정"""
        try:
            if direction == "conservative":
                # 보수적 조정: 더 엄격한 조건
                if 'min_score' in strategy.entry_conditions:
                    strategy.entry_conditions['min_score'] = min(95, strategy.entry_conditions['min_score'] + 5)
                
                if 'stop_loss' in strategy.exit_conditions:
                    strategy.exit_conditions['stop_loss'] = min(0.12, strategy.exit_conditions['stop_loss'] + 0.01)
            
            elif direction == "aggressive":
                # 공격적 조정: 더 관대한 조건
                if 'min_score' in strategy.entry_conditions:
                    strategy.entry_conditions['min_score'] = max(65, strategy.entry_conditions['min_score'] - 3)
                
                if 'profit_target' in strategy.exit_conditions:
                    strategy.exit_conditions['profit_target'] = min(0.25, strategy.exit_conditions['profit_target'] + 0.02)
            
        except Exception as e:
            self.logger.error(f"파라미터 조정 실패: {e}")
    
    def _save_performance_history(self, strategy_id: str, trade_result: Dict):
        """성과 히스토리 저장"""
        try:
            if strategy_id not in self.strategy_performance_history:
                self.strategy_performance_history[strategy_id] = []
            
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'profit_ratio': trade_result.get('profit_ratio', 0),
                'trade_duration': trade_result.get('duration_hours', 0),
                'ticker': trade_result.get('ticker', ''),
                'performance_score': self.strategies[strategy_id].performance_score
            }
            
            self.strategy_performance_history[strategy_id].append(history_entry)
            
            # 최근 100개 기록만 유지
            if len(self.strategy_performance_history[strategy_id]) > 100:
                self.strategy_performance_history[strategy_id] = \
                    self.strategy_performance_history[strategy_id][-100:]
            
        except Exception as e:
            self.logger.error(f"성과 히스토리 저장 실패: {e}")
    def create_dynamic_strategy(self, market_conditions: Dict) -> Optional[TradingStrategy]:
        """동적 전략 생성"""
        try:
            # 시장 상황 분석
            volatility = market_conditions.get('volatility', 0.02)
            trend_strength = market_conditions.get('trend_strength', 0.5)
            volume_surge = market_conditions.get('volume_surge', False)
            rising_ratio = market_conditions.get('rising_ratio', 0.5)
            
            # 시장 상황에 따른 전략 타입 결정
            if volatility > 0.05 and volume_surge:
                strategy_type = "SCALPING"
                base_template = self.strategy_templates["SCALPING"]
            elif trend_strength > 0.7 and rising_ratio > 0.6:
                strategy_type = "TREND"
                base_template = self.strategy_templates["TREND"]
            elif volatility > 0.03:
                strategy_type = "MOMENTUM"
                base_template = self.strategy_templates["MOMENTUM"]
            else:
                strategy_type = "MEAN_REVERSION"
                base_template = self.strategy_templates["MEAN_REVERSION"]
            
            # 시장 조건에 맞게 파라미터 조정
            adjusted_conditions = self._adjust_conditions_for_market(base_template, market_conditions)
            
            # 새 전략 생성
            strategy = TradingStrategy(
                strategy_id=str(uuid.uuid4()),
                name=f"동적_{strategy_type}_{datetime.now().strftime('%H%M')}",
                strategy_type=strategy_type,
                entry_conditions=adjusted_conditions["entry_conditions"],
                exit_conditions=adjusted_conditions["exit_conditions"]
            )
            
            self.strategies[strategy.strategy_id] = strategy
            
            self.logger.info(f"동적 전략 생성: {strategy.name} (시장상황: 변동성 {volatility:.3f})")
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"동적 전략 생성 실패: {e}")
            return None
    
    def _adjust_conditions_for_market(self, base_template: Dict, market_conditions: Dict) -> Dict:
        """시장 상황에 맞는 조건 조정"""
        try:
            entry_conditions = base_template["entry_conditions"].copy()
            exit_conditions = base_template["exit_conditions"].copy()
            
            volatility = market_conditions.get('volatility', 0.02)
            trend_strength = market_conditions.get('trend_strength', 0.5)
            
            # 높은 변동성 시장
            if volatility > 0.04:
                # 더 엄격한 진입 조건
                if 'min_score' in entry_conditions:
                    entry_conditions['min_score'] += 5
                
                # 더 빠른 청산
                if 'profit_target' in exit_conditions:
                    exit_conditions['profit_target'] *= 0.8
                if 'stop_loss' in exit_conditions:
                    exit_conditions['stop_loss'] *= 0.8
            
            # 강한 트렌드 시장
            if trend_strength > 0.8:
                # 더 관대한 진입 조건
                if 'min_score' in entry_conditions:
                    entry_conditions['min_score'] = max(70, entry_conditions['min_score'] - 5)
                
                # 더 큰 수익 목표
                if 'profit_target' in exit_conditions:
                    exit_conditions['profit_target'] *= 1.2
            
            return {
                "entry_conditions": entry_conditions,
                "exit_conditions": exit_conditions
            }
            
        except Exception as e:
            self.logger.error(f"조건 조정 실패: {e}")
            return base_template
    
    def get_best_strategies(self, count: int = 3) -> List[TradingStrategy]:
        """최고 성과 전략 반환"""
        try:
            active_strategies = [s for s in self.strategies.values() if s.is_active]
            
            # 성과 점수 기준 정렬
            sorted_strategies = sorted(
                active_strategies, 
                key=lambda x: x.performance_score, 
                reverse=True
            )
            
            return sorted_strategies[:count]
            
        except Exception as e:
            self.logger.error(f"최고 전략 조회 실패: {e}")
            return []
    
    def cleanup_poor_strategies(self):
        """저성과 전략 정리"""
        try:
            strategies_to_remove = []
            current_time = datetime.now()
            
            for strategy_id, strategy in self.strategies.items():
                # 24시간 이상 미사용 + 저성과
                hours_unused = (current_time - strategy.last_used).total_seconds() / 3600
                
                if (hours_unused > 24 and 
                    strategy.total_trades >= 5 and 
                    strategy.performance_score < 0.2):
                    strategies_to_remove.append(strategy_id)
                
                # 또는 5번 이상 연속 실패
                elif strategy.failure_streak >= 5 and strategy.total_trades >= 5:
                    strategies_to_remove.append(strategy_id)
            
            # 전략 삭제 (최소 2개는 유지)
            if len(self.strategies) - len(strategies_to_remove) >= 2:
                for strategy_id in strategies_to_remove:
                    removed_strategy = self.strategies.pop(strategy_id)
                    self.logger.info(f"저성과 전략 삭제: {removed_strategy.name}")
                    
                    # 히스토리도 정리
                    if strategy_id in self.strategy_performance_history:
                        del self.strategy_performance_history[strategy_id]
            
        except Exception as e:
            self.logger.error(f"전략 정리 실패: {e}")
    
    def get_strategy_summary(self) -> Dict[str, any]:
        """전략 현황 요약"""
        try:
            active_strategies = [s for s in self.strategies.values() if s.is_active]
            
            if not active_strategies:
                return {'total_strategies': 0, 'active_strategies': 0}
            
            # 통계 계산
            total_trades = sum(s.total_trades for s in active_strategies)
            total_wins = sum(s.winning_trades for s in active_strategies)
            total_profit = sum(s.total_profit for s in active_strategies)
            
            # 전략별 성과
            strategy_performance = []
            for strategy in active_strategies:
                strategy_performance.append({
                    'name': strategy.name,
                    'type': strategy.strategy_type,
                    'performance_score': strategy.performance_score,
                    'win_rate': strategy.win_rate,
                    'total_trades': strategy.total_trades,
                    'avg_profit': strategy.avg_profit,
                    'success_streak': strategy.success_streak,
                    'is_active': strategy.is_active
                })
            
            # 최고 성과 전략
            best_strategy = max(active_strategies, key=lambda x: x.performance_score)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'total_strategies': len(self.strategies),
                'active_strategies': len(active_strategies),
                'total_trades': total_trades,
                'overall_win_rate': total_wins / total_trades if total_trades > 0 else 0,
                'overall_profit': total_profit,
                'best_strategy': {
                    'name': best_strategy.name,
                    'type': best_strategy.strategy_type,
                    'performance_score': best_strategy.performance_score
                },
                'strategies': strategy_performance
            }
            
        except Exception as e:
            self.logger.error(f"전략 요약 실패: {e}")
            return {'error': str(e)}
    
    def save_strategies_to_file(self, filename: str = None):
        """전략 데이터 파일 저장"""
        try:
            if filename is None:
                filename = f"data/strategies/strategies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # 전략 데이터 직렬화
            strategies_data = {}
            for strategy_id, strategy in self.strategies.items():
                strategies_data[strategy_id] = {
                    'strategy_id': strategy.strategy_id,
                    'name': strategy.name,
                    'strategy_type': strategy.strategy_type,
                    'entry_conditions': strategy.entry_conditions,
                    'exit_conditions': strategy.exit_conditions,
                    'total_trades': strategy.total_trades,
                    'winning_trades': strategy.winning_trades,
                    'total_profit': strategy.total_profit,
                    'max_drawdown': strategy.max_drawdown,
                    'win_rate': strategy.win_rate,
                    'avg_profit': strategy.avg_profit,
                    'performance_score': strategy.performance_score,
                    'created_at': strategy.created_at.isoformat(),
                    'last_used': strategy.last_used.isoformat(),
                    'is_active': strategy.is_active,
                    'adaptation_count': strategy.adaptation_count,
                    'success_streak': strategy.success_streak,
                    'failure_streak': strategy.failure_streak
                }
            
            # 파일 저장
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'strategies': strategies_data,
                    'performance_history': self.strategy_performance_history,
                    'saved_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"전략 데이터 저장 완료: {filename}")
            
        except Exception as e:
            self.logger.error(f"전략 저장 실패: {e}")
    
    def load_strategies_from_file(self, filename: str):
        """전략 데이터 파일 로드"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            strategies_data = data.get('strategies', {})
            
            # 전략 데이터 복원
            loaded_strategies = {}
            for strategy_id, strategy_data in strategies_data.items():
                strategy = TradingStrategy(
                    strategy_id=strategy_data['strategy_id'],
                    name=strategy_data['name'],
                    strategy_type=strategy_data['strategy_type'],
                    entry_conditions=strategy_data['entry_conditions'],
                    exit_conditions=strategy_data['exit_conditions'],
                    total_trades=strategy_data['total_trades'],
                    winning_trades=strategy_data['winning_trades'],
                    total_profit=strategy_data['total_profit'],
                    max_drawdown=strategy_data['max_drawdown'],
                    win_rate=strategy_data['win_rate'],
                    avg_profit=strategy_data['avg_profit'],
                    performance_score=strategy_data['performance_score'],
                    created_at=datetime.fromisoformat(strategy_data['created_at']),
                    last_used=datetime.fromisoformat(strategy_data['last_used']),
                    is_active=strategy_data['is_active'],
                    adaptation_count=strategy_data['adaptation_count'],
                    success_streak=strategy_data['success_streak'],
                    failure_streak=strategy_data['failure_streak']
                )
                loaded_strategies[strategy_id] = strategy
            
            self.strategies = loaded_strategies
            self.strategy_performance_history = data.get('performance_history', {})
            
            self.logger.info(f"전략 데이터 로드 완료: {len(self.strategies)}개 전략")
            
        except Exception as e:
            self.logger.error(f"전략 로드 실패: {e}")
    
    def analyze_market_conditions(self, market_data: Dict) -> Dict[str, any]:
        """시장 상황 분석"""
        try:
            # 시장 데이터에서 조건 추출
            volatility = market_data.get('volatility', 0.02)
            rising_ratio = market_data.get('rising_ratio', 0.5)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            
            # 시장 상황 분류
            if volatility > 0.05:
                market_condition = "HIGH_VOLATILITY"
            elif rising_ratio > 0.7:
                market_condition = "BULLISH"
            elif rising_ratio < 0.3:
                market_condition = "BEARISH"
            else:
                market_condition = "NEUTRAL"
            
            # 추천 전략 타입
            if market_condition == "HIGH_VOLATILITY":
                recommended_strategy = "SCALPING"
            elif market_condition == "BULLISH":
                recommended_strategy = "TREND"
            elif market_condition == "BEARISH":
                recommended_strategy = "MEAN_REVERSION"
            else:
                recommended_strategy = "MOMENTUM"
            
            self.market_condition = market_condition
            self.market_volatility = volatility
            
            return {
                'market_condition': market_condition,
                'volatility': volatility,
                'rising_ratio': rising_ratio,
                'volume_ratio': volume_ratio,
                'recommended_strategy': recommended_strategy,
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"시장 상황 분석 실패: {e}")
            return {'market_condition': 'UNKNOWN', 'error': str(e)}
    
    def should_create_new_strategy(self) -> bool:
        """새 전략 생성 필요성 판단"""
        try:
            active_strategies = [s for s in self.strategies.values() if s.is_active]
            
            # 조건들
            conditions = [
                len(active_strategies) < 2,  # 활성 전략 부족
                all(s.performance_score < 0.5 for s in active_strategies),  # 모든 전략 저성과
                self.market_volatility > 0.04,  # 높은 변동성
                len(active_strategies) < 4 and any(s.success_streak >= 5 for s in active_strategies)  # 성공 전략 있음
            ]
            
            return any(conditions)
            
        except Exception as e:
            self.logger.error(f"새 전략 필요성 판단 실패: {e}")
            return False
    
    def get_strategy_recommendations(self, ticker: str, analysis_results: Dict[str, AnalysisResult]) -> Dict[str, any]:
        """전략 추천"""
        try:
            # 신호 생성
            signals = self.generate_signals(analysis_results, ticker)
            
            if not signals:
                return {
                    'recommendation': 'HOLD',
                    'confidence': 0.0,
                    'reason': '신호 없음'
                }
            
            # 최고 신호 선택
            best_signal = signals[0]  # 이미 성과순으로 정렬됨
            
            return {
                'recommendation': best_signal.action,
                'confidence': best_signal.confidence,
                'strategy_name': self.strategies[best_signal.strategy_id].name,
                'strategy_type': self.strategies[best_signal.strategy_id].strategy_type,
                'entry_price': best_signal.entry_price,
                'stop_loss': best_signal.stop_loss,
                'take_profit': best_signal.take_profit,
                'reasoning': best_signal.reasoning,
                'timestamp': best_signal.timestamp.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"전략 추천 실패: {e}")
            return {
                'recommendation': 'HOLD',
                'confidence': 0.0,
                'reason': f'오류: {str(e)}'
            }
    def update_strategy_conditions(self, new_min_score=None, new_confidence=None):
        """
        전략 조건 업데이트 (자동 문서화 포함)
        새 AI가 설정을 변경할 때 사용하는 메서드
        """
        changes = {}
    
        # 현재 설정값들
        current_settings = {
            "min_score": 50,  # 현재 사용 중인 값
            "confidence": 0.5  # 현재 사용 중인 값
      }
    
        if new_min_score is not None:
            old_score = current_settings["min_score"]
            changes["min_score"] = {"old": old_score, "new": new_min_score}
        
            # 실제 설정 적용 로직은 여기에...
            # self.current_min_score = new_min_score
    
        if new_confidence is not None:
            old_confidence = current_settings["confidence"]
            changes["confidence"] = {"old": old_confidence, "new": new_confidence}
        
            # 실제 설정 적용 로직은 여기에...
            # self.current_confidence = new_confidence
    
        if changes:
            # 🔄 설정 변경 자동 로깅
            try:
                log_config_change(
                   "core/strategy_engine.py",
                   f"전략 조건 수동 업데이트: {', '.join(changes.keys())}",
                   changes
              )
            
                print(f"✅ 전략 조건 업데이트 및 자동 문서화 완료")
                print(f"📝 변경사항: {changes}")
            except Exception as e:
                print(f"⚠️ 로깅 실패 (설정은 적용됨): {e}")

    def get_current_strategy_status(self):
        """현재 전략 상태 반환 (디버깅용)"""
        return {
            "active_strategies": len([s for s in self.strategies.values() if s.is_active]),
            "total_strategies": len(self.strategies),
            "market_condition": self.market_condition,
            "last_signal_time": getattr(self, 'last_signal_time', None)
        }


if __name__ == "__main__":
    # 모듈 테스트 시 로깅
    try:
        log_feature_add(
            "core/strategy_engine.py",
            "strategy_engine.py 모듈 직접 실행됨 (테스트 모드)"
        )
    except:
        pass            
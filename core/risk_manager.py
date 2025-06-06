"""
리스크 관리자 (1/2)
손실 한도 관리, 포지션 크기 제어, 긴급 정지
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import os

from config.settings import settings
from core.data_collector import DataCollector
from core.strategy_engine import StrategySignal
from utils.logger import Logger

@dataclass
class RiskMetrics:
    """리스크 지표 클래스"""
    daily_pnl: float
    daily_pnl_ratio: float
    max_drawdown: float
    current_exposure: float
    position_count: int
    largest_position_ratio: float
    volatility_risk: float
    concentration_risk: float
    overall_risk_score: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL

@dataclass
class RiskAlert:
    """리스크 알림 클래스"""
    alert_id: str
    alert_type: str  # POSITION_LOSS, DAILY_LIMIT, CONCENTRATION, VOLATILITY
    severity: str    # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    ticker: str
    current_value: float
    threshold: float
    recommendation: str
    timestamp: datetime

class RiskManager:
    """리스크 관리자 클래스"""
    
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.logger = Logger()
        self.data_collector = DataCollector()
        
        # 리스크 한도 설정
        self.max_daily_loss = settings_obj.trading.max_daily_loss
        self.max_position_loss = settings_obj.trading.max_position_loss
        self.max_total_exposure = 0.95  # 총 자본의 95%까지만 투자
        self.max_single_position = 0.4   # 단일 포지션 최대 40%
        self.max_volatility_threshold = 0.15  # 15% 이상 변동성 제한
        
        # 상태 추적
        self.daily_start_capital = 0
        self.risk_alerts: List[RiskAlert] = []
        self.emergency_mode = False
        self.risk_override = False
        
        # 리스크 기록
        self.risk_history = []
        
        # 초기화
        self._initialize_daily_capital()
        
        self.logger.info("리스크 관리자 초기화 완료")
    
    def _initialize_daily_capital(self):
        """일일 시작 자본 초기화"""
        try:
            # 현재 총 자산 계산 (KRW + 코인 평가액)
            krw_balance = self.data_collector.get_balance("KRW")
            
            # 모든 코인 잔고와 현재가 계산
            all_balances = self.data_collector.get_all_balances()
            total_coin_value = 0
            
            for currency, balance in all_balances.items():
                if currency != 'KRW' and balance > 0:
                    ticker = f'KRW-{currency}'
                    current_price = self.data_collector.get_current_price(ticker)
                    if current_price:
                        total_coin_value += balance * current_price
            
            self.daily_start_capital = krw_balance + total_coin_value
            
            self.logger.info(f"일일 시작 자본: {self.daily_start_capital:,.0f}원 "
                           f"(KRW: {krw_balance:,.0f}, 코인: {total_coin_value:,.0f})")
            
        except Exception as e:
            self.logger.error(f"일일 자본 초기화 실패: {e}")
            self.daily_start_capital = 160000  # 기본값
    
    def validate_signal(self, signal: StrategySignal, current_positions: Dict) -> Tuple[bool, str]:
        """신호 리스크 검증"""
        try:
            if signal.action != "BUY":
                return True, "매수 신호가 아님"
            
            # 1. 긴급 모드 체크
            if self.emergency_mode:
                return False, "긴급 모드 - 신규 거래 중단"
            
            # 2. 일일 손실 한도 체크
            daily_pnl_ratio = self._calculate_daily_pnl_ratio()
            if daily_pnl_ratio <= -self.max_daily_loss:
                return False, f"일일 손실 한도 초과: {daily_pnl_ratio:.2%}"
            
            # 3. 포지션 수 제한
            if len(current_positions) >= self.settings.trading.max_positions:
                return False, f"최대 포지션 수 초과: {len(current_positions)}"
            
            # 4. 자본 노출 한도
            current_exposure = self._calculate_current_exposure(current_positions)
            position_size = self.settings.trading.capital_per_position
            
            if (current_exposure + position_size) / self.daily_start_capital > self.max_total_exposure:
                return False, f"총 노출 한도 초과: {current_exposure + position_size:,.0f}원"
            
            # 5. 변동성 체크
            volatility_risk = self._check_volatility_risk(signal.ticker)
            if volatility_risk > self.max_volatility_threshold:
                return False, f"높은 변동성 위험: {volatility_risk:.2%}"
            
            # 6. 농축 리스크 (같은 섹터/유사 코인)
            concentration_risk = self._check_concentration_risk(signal.ticker, current_positions)
            if concentration_risk:
                return False, f"농축 위험: {concentration_risk}"
            
            # 7. 신호 품질 체크
            if signal.confidence < 0.7:
                return False, f"신뢰도 부족: {signal.confidence:.2f}"
            
            # 8. 스프레드 체크 (유동성)
            spread_risk = self._check_spread_risk(signal.ticker)
            if spread_risk > 0.02:  # 2% 이상 스프레드
                return False, f"높은 스프레드 위험: {spread_risk:.2%}"
            
            return True, "리스크 검증 통과"
            
        except Exception as e:
            self.logger.error(f"신호 리스크 검증 실패: {e}")
            return False, f"검증 오류: {str(e)}"
    
    def _calculate_daily_pnl_ratio(self) -> float:
        """일일 손익률 계산"""
        try:
            if self.daily_start_capital <= 0:
                return 0.0
            
            # 현재 총 자산
            current_capital = self._get_total_capital()
            
            # 일일 손익률
            daily_pnl = current_capital - self.daily_start_capital
            daily_pnl_ratio = daily_pnl / self.daily_start_capital
            
            return daily_pnl_ratio
            
        except Exception as e:
            self.logger.error(f"일일 손익률 계산 실패: {e}")
            return 0.0
    
    def _get_total_capital(self) -> float:
        """현재 총 자본 계산"""
        try:
            krw_balance = self.data_collector.get_balance("KRW")
            all_balances = self.data_collector.get_all_balances()
            
            total_coin_value = 0
            for currency, balance in all_balances.items():
                if currency != 'KRW' and balance > 0:
                    ticker = f'KRW-{currency}'
                    current_price = self.data_collector.get_current_price(ticker)
                    if current_price:
                        total_coin_value += balance * current_price
            
            return krw_balance + total_coin_value
            
        except Exception as e:
            self.logger.error(f"총 자본 계산 실패: {e}")
            return self.daily_start_capital
    
    def _calculate_current_exposure(self, positions: Dict) -> float:
        """현재 투자 노출액 계산"""
        try:
            total_exposure = 0
            
            for position in positions.values():
                total_exposure += position.current_value
            
            return total_exposure
            
        except Exception as e:
            self.logger.error(f"노출액 계산 실패: {e}")
            return 0.0
    
    def _check_volatility_risk(self, ticker: str) -> float:
        """변동성 리스크 체크"""
        try:
            # 최근 24시간 데이터로 변동성 계산
            df = self.data_collector.get_ohlcv(ticker, "minute60", 24)
            
            if df is None or len(df) < 10:
                return 0.05  # 기본값
            
            # 시간별 수익률 변동성
            returns = df['close'].pct_change().dropna()
            volatility = returns.std()
            
            # 일일 변동성으로 환산 (24시간)
            daily_volatility = volatility * (24 ** 0.5)
            
            return daily_volatility
            
        except Exception as e:
            self.logger.error(f"변동성 리스크 계산 실패: {e}")
            return 0.1  # 보수적 기본값
    
    def _check_concentration_risk(self, ticker: str, positions: Dict) -> Optional[str]:
        """농축 리스크 체크"""
        try:
            # 같은 코인 중복 체크
            for position in positions.values():
                if position.ticker == ticker:
                    return f"이미 보유 중인 코인: {ticker}"
            
            # 비트코인 계열 농축 체크 (예시)
            btc_related = ['KRW-BTC', 'KRW-BCH', 'KRW-BSV']
            eth_related = ['KRW-ETH', 'KRW-ETC', 'KRW-EOS']
            
            if ticker in btc_related:
                btc_positions = [p for p in positions.values() if p.ticker in btc_related]
                if len(btc_positions) >= 2:
                    return "비트코인 계열 농축 위험"
            
            if ticker in eth_related:
                eth_positions = [p for p in positions.values() if p.ticker in eth_related]
                if len(eth_positions) >= 2:
                    return "이더리움 계열 농축 위험"
            
            return None
            
        except Exception as e:
            self.logger.error(f"농축 리스크 체크 실패: {e}")
            return None
    
    def _check_spread_risk(self, ticker: str) -> float:
        """스프레드 리스크 체크"""
        try:
            orderbook = self.data_collector.get_orderbook(ticker)
            
            if not orderbook:
                return 0.01  # 기본값
            
            spread = orderbook.spread
            mid_price = (orderbook.bid_price + orderbook.ask_price) / 2
            
            spread_ratio = spread / mid_price if mid_price > 0 else 0.01
            
            return spread_ratio
            
        except Exception as e:
            self.logger.error(f"스프레드 리스크 체크 실패: {e}")
            return 0.01
    
    def check_position_risks(self, positions: Dict) -> List[RiskAlert]:
        """포지션별 리스크 체크"""
        alerts = []
        
        try:
            for position in positions.values():
                # 1. 개별 포지션 손실 체크
                if position.unrealized_pnl_ratio <= -self.max_position_loss:
                    alert = RiskAlert(
                        alert_id=f"pos_loss_{position.position_id[:8]}",
                        alert_type="POSITION_LOSS",
                        severity="HIGH",
                        message=f"포지션 손실 한도 초과",
                        ticker=position.ticker,
                        current_value=position.unrealized_pnl_ratio,
                        threshold=-self.max_position_loss,
                        recommendation="즉시 청산 고려",
                        timestamp=datetime.now()
                    )
                    alerts.append(alert)
                
                # 2. 급격한 손실 체크 (-15% 이상)
                elif position.unrealized_pnl_ratio <= -0.15:
                    alert = RiskAlert(
                        alert_id=f"rapid_loss_{position.position_id[:8]}",
                        alert_type="POSITION_LOSS",
                        severity="MEDIUM",
                        message=f"급격한 손실 발생",
                        ticker=position.ticker,
                        current_value=position.unrealized_pnl_ratio,
                        threshold=-0.15,
                        recommendation="손절 고려",
                        timestamp=datetime.now()
                    )
                    alerts.append(alert)
                
                # 3. 장기 보유 손실 체크 (24시간 이상 + 손실)
                holding_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
                if holding_hours >= 24 and position.unrealized_pnl_ratio < -0.05:
                    alert = RiskAlert(
                        alert_id=f"long_hold_{position.position_id[:8]}",
                        alert_type="TIME_RISK",
                        severity="MEDIUM",
                        message=f"장기 보유 손실",
                        ticker=position.ticker,
                        current_value=holding_hours,
                        threshold=24,
                        recommendation="청산 검토",
                        timestamp=datetime.now()
                    )
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"포지션 리스크 체크 실패: {e}")
            return []
    def calculate_risk_metrics(self, positions: Dict) -> RiskMetrics:
        """종합 리스크 지표 계산"""
        try:
            # 일일 손익
            daily_pnl_ratio = self._calculate_daily_pnl_ratio()
            daily_pnl = self.daily_start_capital * daily_pnl_ratio
            
            # 최대 드로우다운 계산
            max_drawdown = self._calculate_max_drawdown()
            
            # 현재 노출액
            current_exposure = self._calculate_current_exposure(positions)
            exposure_ratio = current_exposure / self.daily_start_capital if self.daily_start_capital > 0 else 0
            
            # 포지션 수
            position_count = len(positions)
            
            # 최대 포지션 비율
            largest_position_ratio = 0
            if positions:
                largest_value = max(p.current_value for p in positions.values())
                largest_position_ratio = largest_value / self.daily_start_capital if self.daily_start_capital > 0 else 0
            
            # 변동성 리스크 (평균)
            volatility_risks = []
            for position in positions.values():
                vol_risk = self._check_volatility_risk(position.ticker)
                volatility_risks.append(vol_risk)
            
            avg_volatility_risk = sum(volatility_risks) / len(volatility_risks) if volatility_risks else 0
            
            # 농축 리스크 계산
            concentration_risk = self._calculate_concentration_risk(positions)
            
            # 종합 리스크 스코어 계산 (0-100)
            overall_risk_score = self._calculate_overall_risk_score(
                daily_pnl_ratio, max_drawdown, exposure_ratio, 
                largest_position_ratio, avg_volatility_risk, concentration_risk
            )
            
            # 리스크 레벨 결정
            risk_level = self._determine_risk_level(overall_risk_score)
            
            return RiskMetrics(
                daily_pnl=daily_pnl,
                daily_pnl_ratio=daily_pnl_ratio,
                max_drawdown=max_drawdown,
                current_exposure=current_exposure,
                position_count=position_count,
                largest_position_ratio=largest_position_ratio,
                volatility_risk=avg_volatility_risk,
                concentration_risk=concentration_risk,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level
            )
            
        except Exception as e:
            self.logger.error(f"리스크 지표 계산 실패: {e}")
            return RiskMetrics(
                daily_pnl=0, daily_pnl_ratio=0, max_drawdown=0, current_exposure=0,
                position_count=0, largest_position_ratio=0, volatility_risk=0,
                concentration_risk=0, overall_risk_score=50, risk_level="MEDIUM"
            )
    
    def _calculate_max_drawdown(self) -> float:
        """최대 드로우다운 계산"""
        try:
            # 거래 결과 로드
            results_file = "data/trades/trade_results.json"
            
            if not os.path.exists(results_file):
                return 0.0
            
            with open(results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            trades = data.get('trades', [])
            
            if not trades:
                return 0.0
            
            # 누적 수익률 계산
            cumulative_returns = []
            cumulative_return = 0
            
            for trade in trades:
                cumulative_return += trade.get('profit_ratio', 0)
                cumulative_returns.append(cumulative_return)
            
            # 최대 드로우다운 계산
            peak = cumulative_returns[0]
            max_drawdown = 0
            
            for return_val in cumulative_returns:
                if return_val > peak:
                    peak = return_val
                
                drawdown = peak - return_val
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            return max_drawdown
            
        except Exception as e:
            self.logger.error(f"최대 드로우다운 계산 실패: {e}")
            return 0.0
    
    def _calculate_concentration_risk(self, positions: Dict) -> float:
        """농축 리스크 계산 (0-1)"""
        try:
            if not positions:
                return 0.0
            
            # 포지션별 비중 계산
            total_value = sum(p.current_value for p in positions.values())
            
            if total_value <= 0:
                return 0.0
            
            position_weights = [p.current_value / total_value for p in positions.values()]
            
            # 허핀달 지수 계산 (농축도 측정)
            herfindahl_index = sum(w ** 2 for w in position_weights)
            
            # 0-1 범위로 정규화 (1에 가까울수록 농축됨)
            n = len(positions)
            min_hhi = 1 / n  # 완전 분산
            max_hhi = 1      # 완전 농축
            
            if max_hhi > min_hhi:
                normalized_concentration = (herfindahl_index - min_hhi) / (max_hhi - min_hhi)
            else:
                normalized_concentration = 0
            
            return min(max(normalized_concentration, 0), 1)
            
        except Exception as e:
            self.logger.error(f"농축 리스크 계산 실패: {e}")
            return 0.0
    
    def _calculate_overall_risk_score(self, daily_pnl_ratio: float, max_drawdown: float, 
                                    exposure_ratio: float, largest_position_ratio: float,
                                    volatility_risk: float, concentration_risk: float) -> float:
        """종합 리스크 스코어 계산 (0-100, 높을수록 위험)"""
        try:
            # 각 리스크 요소별 점수 (0-100)
            scores = []
            
            # 1. 일일 손실 점수
            daily_loss_score = min(abs(daily_pnl_ratio) * 1000, 100) if daily_pnl_ratio < 0 else 0
            scores.append(daily_loss_score)
            
            # 2. 드로우다운 점수
            drawdown_score = min(max_drawdown * 500, 100)
            scores.append(drawdown_score)
            
            # 3. 노출 점수
            exposure_score = min(exposure_ratio * 100, 100)
            scores.append(exposure_score)
            
            # 4. 최대 포지션 점수
            position_score = min(largest_position_ratio * 200, 100)
            scores.append(position_score)
            
            # 5. 변동성 점수
            volatility_score = min(volatility_risk * 500, 100)
            scores.append(volatility_score)
            
            # 6. 농축 점수
            concentration_score = concentration_risk * 100
            scores.append(concentration_score)
            
            # 가중 평균 (일일 손실과 드로우다운에 더 높은 가중치)
            weights = [0.3, 0.25, 0.15, 0.1, 0.1, 0.1]
            overall_score = sum(score * weight for score, weight in zip(scores, weights))
            
            return min(max(overall_score, 0), 100)
            
        except Exception as e:
            self.logger.error(f"종합 리스크 스코어 계산 실패: {e}")
            return 50
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """리스크 레벨 결정"""
        if risk_score >= 80:
            return "CRITICAL"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 40:
            return "MEDIUM"
        else:
            return "LOW"
    
    def should_enter_emergency_mode(self, risk_metrics: RiskMetrics) -> bool:
        """긴급 모드 진입 여부 판단"""
        try:
            emergency_conditions = [
                risk_metrics.daily_pnl_ratio <= -self.max_daily_loss,  # 일일 손실 한도 초과
                risk_metrics.overall_risk_score >= 90,                 # 극도로 높은 리스크
                risk_metrics.max_drawdown >= 0.25,                     # 25% 이상 드로우다운
                len(self.risk_alerts) >= 5                             # 다수의 리스크 알림
            ]
            
            return any(emergency_conditions)
            
        except Exception as e:
            self.logger.error(f"긴급 모드 판단 실패: {e}")
            return False
    
    def enter_emergency_mode(self, reason: str):
        """긴급 모드 진입"""
        try:
            self.emergency_mode = True
            
            message = f"🚨 긴급 모드 진입: {reason}"
            self.logger.critical(message)
            
            # 긴급 모드 알림 생성
            alert = RiskAlert(
                alert_id=f"emergency_{datetime.now().strftime('%H%M%S')}",
                alert_type="EMERGENCY",
                severity="CRITICAL",
                message="긴급 모드 진입",
                ticker="ALL",
                current_value=0,
                threshold=0,
                recommendation="모든 포지션 검토 및 청산 고려",
                timestamp=datetime.now()
            )
            
            self.risk_alerts.append(alert)
            
            # 긴급 모드 기록
            self._record_emergency_event(reason)
            
        except Exception as e:
            self.logger.error(f"긴급 모드 진입 실패: {e}")
    
    def exit_emergency_mode(self, reason: str = "수동 해제"):
        """긴급 모드 해제"""
        try:
            self.emergency_mode = False
            
            message = f"✅ 긴급 모드 해제: {reason}"
            self.logger.info(message)
            
            # 긴급 모드 해제 기록
            self._record_emergency_event(f"해제 - {reason}")
            
        except Exception as e:
            self.logger.error(f"긴급 모드 해제 실패: {e}")
    
    def _record_emergency_event(self, reason: str):
        """긴급 모드 이벤트 기록"""
        try:
            emergency_file = "data/logs/emergency_events.json"
            
            try:
                with open(emergency_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            except FileNotFoundError:
                events = {'events': []}
            
            event = {
                'timestamp': datetime.now().isoformat(),
                'event_type': 'EMERGENCY_MODE_CHANGE',
                'emergency_mode': self.emergency_mode,
                'reason': reason,
                'daily_pnl': self._calculate_daily_pnl_ratio()
            }
            
            events['events'].append(event)
            
            # 최근 100개 이벤트만 유지
            if len(events['events']) > 100:
                events['events'] = events['events'][-100:]
            
            os.makedirs(os.path.dirname(emergency_file), exist_ok=True)
            
            with open(emergency_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"긴급 이벤트 기록 실패: {e}")
    
    def get_risk_summary(self, positions: Dict) -> Dict[str, any]:
        """리스크 요약 정보"""
        try:
            risk_metrics = self.calculate_risk_metrics(positions)
            position_alerts = self.check_position_risks(positions)
            
            # 알림 심각도별 카운트
            alert_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
            for alert in position_alerts:
                alert_counts[alert.severity] += 1
            
            return {
                'timestamp': datetime.now().isoformat(),
                'emergency_mode': self.emergency_mode,
                'risk_override': self.risk_override,
                'daily_start_capital': self.daily_start_capital,
                'current_capital': self._get_total_capital(),
                'risk_metrics': {
                    'daily_pnl': risk_metrics.daily_pnl,
                    'daily_pnl_ratio': risk_metrics.daily_pnl_ratio,
                    'max_drawdown': risk_metrics.max_drawdown,
                    'current_exposure': risk_metrics.current_exposure,
                    'position_count': risk_metrics.position_count,
                    'largest_position_ratio': risk_metrics.largest_position_ratio,
                    'volatility_risk': risk_metrics.volatility_risk,
                    'concentration_risk': risk_metrics.concentration_risk,
                    'overall_risk_score': risk_metrics.overall_risk_score,
                    'risk_level': risk_metrics.risk_level
                },
                'risk_limits': {
                    'max_daily_loss': self.max_daily_loss,
                    'max_position_loss': self.max_position_loss,
                    'max_total_exposure': self.max_total_exposure,
                    'max_single_position': self.max_single_position,
                    'max_volatility_threshold': self.max_volatility_threshold
                },
                'alerts': {
                    'total_alerts': len(position_alerts),
                    'alert_counts': alert_counts,
                    'recent_alerts': [
                        {
                            'type': alert.alert_type,
                            'severity': alert.severity,
                            'ticker': alert.ticker,
                            'message': alert.message,
                            'recommendation': alert.recommendation
                        }
                        for alert in position_alerts[-5:]  # 최근 5개
                    ]
                }
            }
            
        except Exception as e:
            self.logger.error(f"리스크 요약 생성 실패: {e}")
            return {'error': str(e)}
    
    def adjust_position_size(self, signal: StrategySignal, risk_metrics: RiskMetrics) -> float:
        """리스크 기반 포지션 크기 조정"""
        try:
            base_size = self.settings.trading.capital_per_position
            
            # 리스크 레벨에 따른 조정
            risk_multipliers = {
                'LOW': 1.0,
                'MEDIUM': 0.8,
                'HIGH': 0.5,
                'CRITICAL': 0.2
            }
            
            risk_multiplier = risk_multipliers.get(risk_metrics.risk_level, 0.5)
            
            # 신호 신뢰도에 따른 조정
            confidence_multiplier = signal.confidence
            
            # 변동성에 따른 조정
            volatility_multiplier = max(0.3, 1 - risk_metrics.volatility_risk * 2)
            
            # 일일 손실에 따른 조정
            if risk_metrics.daily_pnl_ratio < -0.02:  # -2% 이하 손실
                daily_loss_multiplier = 0.5
            elif risk_metrics.daily_pnl_ratio < 0:    # 손실 상태
                daily_loss_multiplier = 0.8
            else:                                     # 수익 상태
                daily_loss_multiplier = 1.0
            
            # 최종 포지션 크기 계산
            adjusted_size = (base_size * 
                           risk_multiplier * 
                           confidence_multiplier * 
                           volatility_multiplier * 
                           daily_loss_multiplier)
            
            # 최소/최대 한도 적용
            min_size = self.settings.trading.min_order_amount
            max_size = self.daily_start_capital * self.max_single_position
            
            final_size = max(min_size, min(adjusted_size, max_size))
            
            self.logger.info(f"포지션 크기 조정: {base_size:,.0f} → {final_size:,.0f}원 "
                           f"(리스크: {risk_multiplier:.2f}, 신뢰도: {confidence_multiplier:.2f})")
            
            return final_size
            
        except Exception as e:
            self.logger.error(f"포지션 크기 조정 실패: {e}")
            return self.settings.trading.capital_per_position
    
    def should_force_close_position(self, position, risk_metrics: RiskMetrics) -> Optional[str]:
        """강제 청산 여부 판단"""
        try:
            # 1. 긴급 모드에서 모든 포지션 청산
            if self.emergency_mode:
                return "긴급 모드 - 전체 청산"
            
            # 2. 개별 포지션 손실 한도 초과
            if position.unrealized_pnl_ratio <= -self.max_position_loss:
                return f"포지션 손실 한도 초과 ({position.unrealized_pnl_ratio:.2%})"
            
            # 3. 극도의 손실 (-20% 이상)
            if position.unrealized_pnl_ratio <= -0.20:
                return f"극도의 손실 ({position.unrealized_pnl_ratio:.2%})"
            
            # 4. 높은 변동성 + 손실 조합
            volatility = self._check_volatility_risk(position.ticker)
            if volatility > 0.15 and position.unrealized_pnl_ratio <= -0.10:
                return f"고변동성 + 손실 ({volatility:.2%} 변동성, {position.unrealized_pnl_ratio:.2%} 손실)"
            
            # 5. 일일 손실 한도 근접 시 큰 손실 포지션 우선 청산
            if risk_metrics.daily_pnl_ratio <= -self.max_daily_loss * 0.8:  # 80% 도달
                if position.unrealized_pnl_ratio <= -0.08:  # 8% 이상 손실
                    return f"일일 한도 근접 - 손실 포지션 청산 ({position.unrealized_pnl_ratio:.2%})"
            
            return None
            
        except Exception as e:
            self.logger.error(f"강제 청산 판단 실패: {e}")
            return None
    
    def reset_daily_limits(self):
        """일일 제한 초기화"""
        try:
            self._initialize_daily_capital()
            self.risk_alerts.clear()
            
            # 긴급 모드 자동 해제 (수동 설정이 아닌 경우)
            if self.emergency_mode and not self.risk_override:
                self.exit_emergency_mode("일일 리셋")
            
            self.logger.info("일일 리스크 제한 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"일일 제한 초기화 실패: {e}")
    
    def override_risk_controls(self, duration_minutes: int = 60):
        """리스크 통제 일시 해제"""
        try:
            self.risk_override = True
            self.logger.warning(f"⚠️ 리스크 통제 일시 해제 ({duration_minutes}분)")
            
            # 일정 시간 후 자동 복구를 위한 타이머 설정 (실제 구현에서는 스케줄러 사용)
            # 여기서는 기록만 남김
            override_event = {
                'timestamp': datetime.now().isoformat(),
                'duration_minutes': duration_minutes,
                'reason': '수동 해제'
            }
            
            self._record_risk_override(override_event)
            
        except Exception as e:
            self.logger.error(f"리스크 통제 해제 실패: {e}")
    
    def restore_risk_controls(self):
        """리스크 통제 복구"""
        try:
            self.risk_override = False
            self.logger.info("✅ 리스크 통제 복구")
            
        except Exception as e:
            self.logger.error(f"리스크 통제 복구 실패: {e}")
    
    def _record_risk_override(self, event: Dict):
        """리스크 해제 이벤트 기록"""
        try:
            override_file = "data/logs/risk_overrides.json"
            
            try:
                with open(override_file, 'r', encoding='utf-8') as f:
                    overrides = json.load(f)
            except FileNotFoundError:
                overrides = {'overrides': []}
            
            overrides['overrides'].append(event)
            
            # 최근 50개 기록만 유지
            if len(overrides['overrides']) > 50:
                overrides['overrides'] = overrides['overrides'][-50:]
            
            os.makedirs(os.path.dirname(override_file), exist_ok=True)
            
            with open(override_file, 'w', encoding='utf-8') as f:
                json.dump(overrides, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"리스크 해제 기록 실패: {e}")
    
    def get_risk_recommendations(self, positions: Dict) -> List[str]:
        """리스크 기반 추천사항"""
        try:
            recommendations = []
            risk_metrics = self.calculate_risk_metrics(positions)
            
            # 일일 손실 기반 추천
            if risk_metrics.daily_pnl_ratio <= -0.05:
                recommendations.append("일일 손실 5% 초과 - 신규 거래 중단 고려")
            elif risk_metrics.daily_pnl_ratio <= -0.03:
                recommendations.append("일일 손실 3% 초과 - 보수적 거래 권장")
            
            # 포지션 농축도 기반 추천
            if risk_metrics.concentration_risk > 0.7:
                recommendations.append("포지션 농축도 높음 - 분산투자 필요")
            
            # 변동성 기반 추천
            if risk_metrics.volatility_risk > 0.10:
                recommendations.append("높은 변동성 - 포지션 크기 축소 권장")
            
            # 노출 비율 기반 추천
            exposure_ratio = risk_metrics.current_exposure / self.daily_start_capital if self.daily_start_capital > 0 else 0
            if exposure_ratio > 0.8:
                recommendations.append("높은 자본 노출 - 일부 포지션 청산 고려")
            
            # 최대 포지션 기반 추천
            if risk_metrics.largest_position_ratio > 0.3:
                recommendations.append("단일 포지션 비중 과다 - 분할 매도 고려")
            
            # 리스크 레벨 기반 추천
            if risk_metrics.risk_level == "CRITICAL":
                recommendations.append("🚨 위험 수준 Critical - 즉시 포지션 점검 필요")
            elif risk_metrics.risk_level == "HIGH":
                recommendations.append("⚠️ 위험 수준 High - 신중한 거래 필요")
            
            # 긴급 모드 추천
            if self.emergency_mode:
                recommendations.append("🚨 긴급 모드 활성 - 모든 거래 중단됨")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"리스크 추천사항 생성 실패: {e}")
            return ["리스크 분석 오류 - 수동 점검 필요"]
    
    def save_risk_history(self, risk_metrics: RiskMetrics):
        """리스크 기록 저장"""
        try:
            risk_record = {
                'timestamp': datetime.now().isoformat(),
                'daily_pnl_ratio': risk_metrics.daily_pnl_ratio,
                'max_drawdown': risk_metrics.max_drawdown,
                'current_exposure': risk_metrics.current_exposure,
                'position_count': risk_metrics.position_count,
                'volatility_risk': risk_metrics.volatility_risk,
                'concentration_risk': risk_metrics.concentration_risk,
                'overall_risk_score': risk_metrics.overall_risk_score,
                'risk_level': risk_metrics.risk_level,
                'emergency_mode': self.emergency_mode
            }
            
            self.risk_history.append(risk_record)
            
            # 최근 1000개 기록만 유지
            if len(self.risk_history) > 1000:
                self.risk_history = self.risk_history[-1000:]
            
            # 파일 저장 (1시간마다)
            if len(self.risk_history) % 60 == 0:  # 1분마다 호출된다면 60번째마다
                self._save_risk_history_to_file()
            
        except Exception as e:
            self.logger.error(f"리스크 기록 저장 실패: {e}")
    
    def _save_risk_history_to_file(self):
        """리스크 기록 파일 저장"""
        try:
            history_file = "data/logs/risk_history.json"
            
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'risk_history': self.risk_history,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"리스크 기록 파일 저장 실패: {e}")
    
    def health_check(self) -> Dict[str, any]:
        """리스크 관리자 상태 확인"""
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'emergency_mode': self.emergency_mode,
                'risk_override': self.risk_override,
                'daily_start_capital': self.daily_start_capital,
                'current_capital': self._get_total_capital(),
                'daily_pnl_ratio': self._calculate_daily_pnl_ratio(),
                'active_alerts': len(self.risk_alerts),
                'risk_history_count': len(self.risk_history),
                'status': 'HEALTHY' if not self.emergency_mode else 'EMERGENCY'
            }
            
        except Exception as e:
            self.logger.error(f"리스크 관리자 헬스체크 실패: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'ERROR',
                'error': str(e)
            }    
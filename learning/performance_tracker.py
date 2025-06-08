"""
CoinBot 성과 추적 및 분석 시스템
- 상세한 거래 성과 분석
- 백테스팅 및 전략 비교
- 리스크 지표 계산
- 성과 리포트 생성
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 프로젝트 모듈
try:
    from utils.database import DatabaseManager
    from utils.logger import Logger
    from core.data_collector import DataCollector
except ImportError as e:
    print(f"모듈 import 경고: {e}")
    DatabaseManager = None
    Logger = logging.getLogger
    DataCollector = None

@dataclass
class PerformanceMetrics:
    """성과 지표 데이터 클래스"""
    # 기본 수익률 지표
    total_return: float = 0.0
    annualized_return: float = 0.0
    daily_return_mean: float = 0.0
    daily_return_std: float = 0.0
    
    # 리스크 지표
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    # 거래 지표
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # 시간 지표
    avg_holding_period: float = 0.0
    max_holding_period: float = 0.0
    min_holding_period: float = 0.0
    
    # 기타 지표
    recovery_factor: float = 0.0
    ulcer_index: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    cvar_95: float = 0.0  # Conditional VaR 95%

@dataclass
class StrategyComparison:
    """전략 비교 데이터 클래스"""
    strategy_id: str
    strategy_name: str
    metrics: PerformanceMetrics
    period_start: datetime
    period_end: datetime
    total_trades: int
    final_value: float
    ranking: int = 0

@dataclass
class MonthlyPerformance:
    """월별 성과 데이터 클래스"""
    year: int
    month: int
    monthly_return: float
    monthly_trades: int
    monthly_win_rate: float
    monthly_sharpe: float
    monthly_max_dd: float
    start_value: float
    end_value: float

class PerformanceTracker:
    """성과 추적 및 분석 클래스"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """성과 추적기 초기화"""
        self.db = db_manager
        self.logger = Logger() if hasattr(Logger, 'info') else logging.getLogger(__name__)
        
        # 분석 설정
        self.risk_free_rate = 0.02  # 무위험 수익률 (연 2%)
        self.trading_days_per_year = 365  # 암호화폐는 365일 거래
        self.initial_capital = 160000  # 초기 자본 16만원
        self.target_capital = 500000   # 목표 자본 50만원
        
        # 데이터 캐시
        self._trade_data_cache = None
        self._performance_cache = None
        self._cache_timestamp = None
        
        # 결과 저장 경로
        self.output_dir = Path("data/analysis")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("성과 추적기 초기화 완료")
    
    def _load_trade_data(self, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> pd.DataFrame:
        """거래 데이터 로드"""
        try:
            if not self.db:
                return self._generate_mock_trade_data()
            
            # 캐시 확인 (5분간 유효)
            if (self._trade_data_cache is not None and 
                self._cache_timestamp and 
                (datetime.now() - self._cache_timestamp).seconds < 300):
                return self._trade_data_cache
            
            # 데이터베이스에서 거래 기록 조회
            trades = self.db.get_trades(
                start_date=start_date,
                end_date=end_date,
                limit=10000
            )
            
            if not trades:
                self.logger.warning("거래 데이터가 없습니다")
                return pd.DataFrame()
            
            # DataFrame으로 변환
            trade_data = []
            for trade in trades:
                trade_data.append({
                    'trade_id': trade.trade_id,
                    'ticker': trade.ticker,
                    'action': trade.action,
                    'price': trade.price,
                    'quantity': trade.quantity,
                    'total_amount': trade.total_amount,
                    'commission': trade.commission,
                    'strategy_id': trade.strategy_id,
                    'confidence': trade.confidence,
                    'timestamp': trade.timestamp,
                    'profit_loss': trade.profit_loss,
                    'profit_ratio': trade.profit_ratio
                })
            
            df = pd.DataFrame(trade_data)
            
            # 데이터 타입 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # 캐시 업데이트
            self._trade_data_cache = df
            self._cache_timestamp = datetime.now()
            
            return df
            
        except Exception as e:
            self.logger.error(f"거래 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def _generate_mock_trade_data(self) -> pd.DataFrame:
        """모의 거래 데이터 생성 (테스트용)"""
        try:
            import random
            
            # 30일간의 모의 거래 생성
            trades = []
            current_date = datetime.now() - timedelta(days=30)
            trade_id = 1
            
            tickers = ['KRW-BTC', 'KRW-ETH', 'KRW-ADA', 'KRW-DOT', 'KRW-LINK']
            strategies = ['RSI_Strategy', 'MA_Strategy', 'Momentum_Strategy', 'Mean_Reversion']
            
            for day in range(30):
                # 하루에 1-3개 거래 생성
                daily_trades = random.randint(0, 3)
                
                for _ in range(daily_trades):
                    ticker = random.choice(tickers)
                    strategy = random.choice(strategies)
                    
                    # 매수 거래
                    buy_time = current_date + timedelta(hours=random.randint(1, 20))
                    buy_price = random.randint(1000000, 50000000)
                    amount = random.randint(30000, 70000)
                    quantity = amount / buy_price
                    
                    trades.append({
                        'trade_id': f'mock_{trade_id:04d}',
                        'ticker': ticker,
                        'action': 'BUY',
                        'price': buy_price,
                        'quantity': quantity,
                        'total_amount': amount,
                        'commission': amount * 0.0005,
                        'strategy_id': strategy,
                        'confidence': random.uniform(0.6, 0.9),
                        'timestamp': buy_time,
                        'profit_loss': None,
                        'profit_ratio': None
                    })
                    trade_id += 1
                    
                    # 매도 거래 (70% 확률)
                    if random.random() < 0.7:
                        sell_time = buy_time + timedelta(hours=random.randint(2, 48))
                        profit_ratio = random.uniform(-0.08, 0.15)  # -8% ~ +15%
                        sell_price = buy_price * (1 + profit_ratio)
                        sell_amount = quantity * sell_price
                        profit_loss = sell_amount - amount - (amount * 0.0005) - (sell_amount * 0.0005)
                        
                        trades.append({
                            'trade_id': f'mock_{trade_id:04d}',
                            'ticker': ticker,
                            'action': 'SELL',
                            'price': sell_price,
                            'quantity': quantity,
                            'total_amount': sell_amount,
                            'commission': sell_amount * 0.0005,
                            'strategy_id': strategy,
                            'confidence': random.uniform(0.6, 0.9),
                            'timestamp': sell_time,
                            'profit_loss': profit_loss,
                            'profit_ratio': profit_ratio
                        })
                        trade_id += 1
                
                current_date += timedelta(days=1)
            
            df = pd.DataFrame(trades)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            return df
            
        except Exception as e:
            self.logger.error(f"모의 데이터 생성 실패: {e}")
            return pd.DataFrame()
    
    def _calculate_portfolio_values(self, trade_df: pd.DataFrame) -> pd.DataFrame:
        """포트폴리오 가치 시계열 계산"""
        try:
            if trade_df.empty:
                return pd.DataFrame()
            
            # 일별 포트폴리오 가치 계산
            portfolio_values = []
            current_value = self.initial_capital
            current_positions = {}
            
            # 날짜별로 거래 그룹화
            trade_df['date'] = trade_df['timestamp'].dt.date
            daily_trades = trade_df.groupby('date')
            
            start_date = trade_df['date'].min()
            end_date = trade_df['date'].max()
            
            # 모든 날짜에 대해 포트폴리오 가치 계산
            current_date = start_date
            while current_date <= end_date:
                daily_trades_data = daily_trades.get_group(current_date) if current_date in daily_trades.groups else pd.DataFrame()
                
                # 해당 날짜의 거래 처리
                for _, trade in daily_trades_data.iterrows():
                    if trade['action'] == 'BUY':
                        current_value -= trade['total_amount'] + trade['commission']
                        current_positions[trade['ticker']] = current_positions.get(trade['ticker'], 0) + trade['quantity']
                    elif trade['action'] == 'SELL':
                        current_value += trade['total_amount'] - trade['commission']
                        current_positions[trade['ticker']] = current_positions.get(trade['ticker'], 0) - trade['quantity']
                        
                        # 포지션이 0이 되면 제거
                        if abs(current_positions[trade['ticker']]) < 1e-8:
                            del current_positions[trade['ticker']]
                
                # 포트폴리오 가치 기록
                portfolio_values.append({
                    'date': current_date,
                    'portfolio_value': current_value,
                    'cash_value': current_value,
                    'positions': dict(current_positions),
                    'total_return': (current_value - self.initial_capital) / self.initial_capital
                })
                
                current_date += timedelta(days=1)
            
            return pd.DataFrame(portfolio_values)
            
        except Exception as e:
            self.logger.error(f"포트폴리오 가치 계산 실패: {e}")
            return pd.DataFrame()
    
    def calculate_performance_metrics(self, start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> PerformanceMetrics:
        """종합 성과 지표 계산"""
        try:
            # 거래 데이터 로드
            trade_df = self._load_trade_data(start_date, end_date)
            if trade_df.empty:
                return PerformanceMetrics()
            
            # 포트폴리오 가치 계산
            portfolio_df = self._calculate_portfolio_values(trade_df)
            if portfolio_df.empty:
                return PerformanceMetrics()
            
            # 일일 수익률 계산
            portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
            daily_returns = portfolio_df['daily_return'].dropna()
            
            # 기본 수익률 지표
            total_return = portfolio_df['total_return'].iloc[-1]
            days = len(portfolio_df)
            annualized_return = (1 + total_return) ** (365.25 / days) - 1 if days > 0 else 0
            
            # 리스크 지표
            volatility = daily_returns.std() * np.sqrt(365.25)
            sharpe_ratio = (annualized_return - self.risk_free_rate) / volatility if volatility > 0 else 0
            
            # 최대 낙폭 계산
            cumulative_returns = (1 + daily_returns).cumprod()
            peak = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - peak) / peak
            max_drawdown = drawdown.min()
            
            # 거래 지표 계산
            sell_trades = trade_df[trade_df['action'] == 'SELL']
            total_trades = len(sell_trades)
            winning_trades = len(sell_trades[sell_trades['profit_ratio'] > 0])
            losing_trades = total_trades - winning_trades
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            avg_win = sell_trades[sell_trades['profit_ratio'] > 0]['profit_ratio'].mean() if winning_trades > 0 else 0
            avg_loss = sell_trades[sell_trades['profit_ratio'] <= 0]['profit_ratio'].mean() if losing_trades > 0 else 0
            
            # Sortino 비율 (하방 변동성만 고려)
            negative_returns = daily_returns[daily_returns < 0]
            downside_deviation = negative_returns.std() * np.sqrt(365.25)
            sortino_ratio = (annualized_return - self.risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
            
            # VaR 및 CVaR 계산
            var_95 = daily_returns.quantile(0.05)
            cvar_95 = daily_returns[daily_returns <= var_95].mean()
            
            return PerformanceMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                daily_return_mean=daily_returns.mean(),
                daily_return_std=daily_returns.std(),
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                var_95=var_95,
                cvar_95=cvar_95
            )
            
        except Exception as e:
            self.logger.error(f"성과 지표 계산 실패: {e}")
            return PerformanceMetrics()
    def compare_strategies(self, period_days: int = 30) -> List[StrategyComparison]:
        """전략별 성과 비교"""
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            trade_df = self._load_trade_data(start_date=start_date)
            
            if trade_df.empty:
                return []
            
            # 전략별로 데이터 분리
            strategies = trade_df['strategy_id'].unique()
            comparisons = []
            
            for strategy_id in strategies:
                strategy_trades = trade_df[trade_df['strategy_id'] == strategy_id]
                
                if len(strategy_trades) < 2:  # 최소 2개 거래 필요
                    continue
                
                # 해당 전략의 성과 계산
                sell_trades = strategy_trades[strategy_trades['action'] == 'SELL']
                
                if len(sell_trades) == 0:
                    continue
                
                # 전략별 포트폴리오 가치 계산
                strategy_portfolio = self._calculate_strategy_portfolio(strategy_trades)
                
                if strategy_portfolio.empty:
                    continue
                
                # 성과 지표 계산
                metrics = self._calculate_strategy_metrics(strategy_trades, strategy_portfolio)
                
                comparison = StrategyComparison(
                    strategy_id=strategy_id,
                    strategy_name=strategy_id.replace('_', ' ').title(),
                    metrics=metrics,
                    period_start=strategy_trades['timestamp'].min(),
                    period_end=strategy_trades['timestamp'].max(),
                    total_trades=len(sell_trades),
                    final_value=strategy_portfolio['portfolio_value'].iloc[-1] if not strategy_portfolio.empty else 0
                )
                
                comparisons.append(comparison)
            
            # 샤프 비율 기준으로 순위 매기기
            comparisons.sort(key=lambda x: x.metrics.sharpe_ratio, reverse=True)
            for i, comp in enumerate(comparisons):
                comp.ranking = i + 1
            
            return comparisons
            
        except Exception as e:
            self.logger.error(f"전략 비교 실패: {e}")
            return []
    
    def _calculate_strategy_portfolio(self, strategy_trades: pd.DataFrame) -> pd.DataFrame:
        """특정 전략의 포트폴리오 가치 계산"""
        try:
            portfolio_values = []
            current_value = 50000  # 전략당 할당 자본
            
            for _, trade in strategy_trades.iterrows():
                if trade['action'] == 'BUY':
                    current_value -= trade['total_amount'] + trade['commission']
                elif trade['action'] == 'SELL':
                    current_value += trade['total_amount'] - trade['commission']
                
                portfolio_values.append({
                    'timestamp': trade['timestamp'],
                    'portfolio_value': current_value,
                    'total_return': (current_value - 50000) / 50000
                })
            
            return pd.DataFrame(portfolio_values)
            
        except Exception as e:
            self.logger.error(f"전략 포트폴리오 계산 실패: {e}")
            return pd.DataFrame()
    
    def _calculate_strategy_metrics(self, strategy_trades: pd.DataFrame, 
                                  strategy_portfolio: pd.DataFrame) -> PerformanceMetrics:
        """전략별 성과 지표 계산"""
        try:
            if strategy_portfolio.empty:
                return PerformanceMetrics()
            
            # 수익률 계산
            total_return = strategy_portfolio['total_return'].iloc[-1]
            days = len(strategy_portfolio)
            annualized_return = (1 + total_return) ** (365.25 / days) - 1 if days > 0 else 0
            
            # 거래 통계
            sell_trades = strategy_trades[strategy_trades['action'] == 'SELL']
            total_trades = len(sell_trades)
            winning_trades = len(sell_trades[sell_trades['profit_ratio'] > 0])
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            avg_win = sell_trades[sell_trades['profit_ratio'] > 0]['profit_ratio'].mean() if winning_trades > 0 else 0
            avg_loss = sell_trades[sell_trades['profit_ratio'] <= 0]['profit_ratio'].mean() if (total_trades - winning_trades) > 0 else 0
            
            # 변동성 및 샤프 비율
            if len(strategy_portfolio) > 1:
                daily_returns = strategy_portfolio['portfolio_value'].pct_change().dropna()
                volatility = daily_returns.std() * np.sqrt(365.25)
                sharpe_ratio = (annualized_return - self.risk_free_rate) / volatility if volatility > 0 else 0
            else:
                volatility = 0
                sharpe_ratio = 0
            
            return PerformanceMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                total_trades=total_trades,
                winning_trades=winning_trades,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss
            )
            
        except Exception as e:
            self.logger.error(f"전략 지표 계산 실패: {e}")
            return PerformanceMetrics()
    
    def analyze_monthly_performance(self, months: int = 6) -> List[MonthlyPerformance]:
        """월별 성과 분석"""
        try:
            start_date = datetime.now() - timedelta(days=months * 30)
            trade_df = self._load_trade_data(start_date=start_date)
            
            if trade_df.empty:
                return []
            
            # 월별 그룹화
            trade_df['year_month'] = trade_df['timestamp'].dt.to_period('M')
            monthly_groups = trade_df.groupby('year_month')
            
            monthly_performance = []
            
            for period, month_trades in monthly_groups:
                year = period.year
                month = period.month
                
                # 월별 포트폴리오 계산
                month_portfolio = self._calculate_portfolio_values(month_trades)
                
                if month_portfolio.empty:
                    continue
                
                start_value = month_portfolio['portfolio_value'].iloc[0]
                end_value = month_portfolio['portfolio_value'].iloc[-1]
                monthly_return = (end_value - start_value) / start_value if start_value > 0 else 0
                
                # 월별 거래 통계
                sell_trades = month_trades[month_trades['action'] == 'SELL']
                monthly_trades_count = len(sell_trades)
                winning_trades = len(sell_trades[sell_trades['profit_ratio'] > 0])
                monthly_win_rate = winning_trades / monthly_trades_count if monthly_trades_count > 0 else 0
                
                # 월별 샤프 비율
                if len(month_portfolio) > 1:
                    daily_returns = month_portfolio['portfolio_value'].pct_change().dropna()
                    monthly_volatility = daily_returns.std() * np.sqrt(30)
                    monthly_sharpe = (monthly_return * 12 - self.risk_free_rate) / (monthly_volatility * np.sqrt(12)) if monthly_volatility > 0 else 0
                else:
                    monthly_sharpe = 0
                
                # 월별 최대 낙폭
                cumulative_returns = (1 + month_portfolio['portfolio_value'].pct_change()).cumprod()
                peak = cumulative_returns.expanding().max()
                drawdown = (cumulative_returns - peak) / peak
                monthly_max_dd = drawdown.min()
                
                monthly_performance.append(MonthlyPerformance(
                    year=year,
                    month=month,
                    monthly_return=monthly_return,
                    monthly_trades=monthly_trades_count,
                    monthly_win_rate=monthly_win_rate,
                    monthly_sharpe=monthly_sharpe,
                    monthly_max_dd=monthly_max_dd,
                    start_value=start_value,
                    end_value=end_value
                ))
            
            return monthly_performance
            
        except Exception as e:
            self.logger.error(f"월별 성과 분석 실패: {e}")
            return []
    
    def calculate_risk_metrics(self) -> Dict[str, Any]:
        """상세 리스크 지표 계산"""
        try:
            trade_df = self._load_trade_data()
            if trade_df.empty:
                return {}
            
            portfolio_df = self._calculate_portfolio_values(trade_df)
            if portfolio_df.empty:
                return {}
            
            # 일일 수익률
            portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
            daily_returns = portfolio_df['daily_return'].dropna()
            
            if len(daily_returns) < 2:
                return {}
            
            # 기본 통계
            mean_return = daily_returns.mean()
            std_return = daily_returns.std()
            skewness = stats.skew(daily_returns)
            kurtosis = stats.kurtosis(daily_returns)
            
            # VaR 및 CVaR (다양한 신뢰구간)
            var_99 = daily_returns.quantile(0.01)
            var_95 = daily_returns.quantile(0.05)
            var_90 = daily_returns.quantile(0.10)
            
            cvar_99 = daily_returns[daily_returns <= var_99].mean()
            cvar_95 = daily_returns[daily_returns <= var_95].mean()
            cvar_90 = daily_returns[daily_returns <= var_90].mean()
            
            # 최대 낙폭 상세 분석
            cumulative_returns = (1 + daily_returns).cumprod()
            peak = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - peak) / peak
            
            max_drawdown = drawdown.min()
            max_dd_index = drawdown.idxmin()
            
            # 회복 기간 계산
            recovery_periods = []
            in_drawdown = False
            drawdown_start = None
            
            for i, dd in enumerate(drawdown):
                if dd < -0.01 and not in_drawdown:  # 1% 이상 하락시 드로우다운 시작
                    in_drawdown = True
                    drawdown_start = i
                elif dd >= -0.001 and in_drawdown:  # 거의 회복시 드로우다운 끝
                    if drawdown_start is not None:
                        recovery_periods.append(i - drawdown_start)
                    in_drawdown = False
                    drawdown_start = None
            
            avg_recovery_period = np.mean(recovery_periods) if recovery_periods else 0
            max_recovery_period = max(recovery_periods) if recovery_periods else 0
            
            # Calmar 비율 (연환산 수익률 / 최대 낙폭)
            annualized_return = (1 + mean_return) ** 365.25 - 1
            calmar_ratio = abs(annualized_return / max_drawdown) if max_drawdown != 0 else 0
            
            # Ulcer Index (낙폭의 제곱평균제곱근)
            ulcer_index = np.sqrt(np.mean(drawdown ** 2))
            
            # 연속 손실 분석
            sell_trades = trade_df[trade_df['action'] == 'SELL']
            consecutive_losses = []
            current_streak = 0
            
            for _, trade in sell_trades.iterrows():
                if trade['profit_ratio'] < 0:
                    current_streak += 1
                else:
                    if current_streak > 0:
                        consecutive_losses.append(current_streak)
                    current_streak = 0
            
            if current_streak > 0:
                consecutive_losses.append(current_streak)
            
            max_consecutive_losses = max(consecutive_losses) if consecutive_losses else 0
            avg_consecutive_losses = np.mean(consecutive_losses) if consecutive_losses else 0
            
            return {
                'basic_stats': {
                    'mean_daily_return': mean_return,
                    'std_daily_return': std_return,
                    'skewness': skewness,
                    'kurtosis': kurtosis,
                    'annualized_return': annualized_return,
                    'annualized_volatility': std_return * np.sqrt(365.25)
                },
                'var_cvar': {
                    'var_99': var_99,
                    'var_95': var_95,
                    'var_90': var_90,
                    'cvar_99': cvar_99,
                    'cvar_95': cvar_95,
                    'cvar_90': cvar_90
                },
                'drawdown_analysis': {
                    'max_drawdown': max_drawdown,
                    'max_drawdown_date': max_dd_index,
                    'avg_recovery_period_days': avg_recovery_period,
                    'max_recovery_period_days': max_recovery_period,
                    'num_drawdown_periods': len(recovery_periods),
                    'ulcer_index': ulcer_index,
                    'calmar_ratio': calmar_ratio
                },
                'trading_risk': {
                    'max_consecutive_losses': max_consecutive_losses,
                    'avg_consecutive_losses': avg_consecutive_losses,
                    'total_drawdown_periods': len(recovery_periods)
                }
            }
            
        except Exception as e:
            self.logger.error(f"리스크 지표 계산 실패: {e}")
            return {}
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """종합 성과 리포트 생성"""
        try:
            report = {
                'report_generated': datetime.now().isoformat(),
                'period_summary': {},
                'overall_metrics': {},
                'strategy_comparison': [],
                'monthly_performance': [],
                'risk_analysis': {},
                'goal_tracking': {}
            }
            
            # 전체 성과 지표
            overall_metrics = self.calculate_performance_metrics()
            report['overall_metrics'] = {
                'total_return': f"{overall_metrics.total_return:.2%}",
                'annualized_return': f"{overall_metrics.annualized_return:.2%}",
                'volatility': f"{overall_metrics.volatility:.2%}",
                'sharpe_ratio': f"{overall_metrics.sharpe_ratio:.2f}",
                'sortino_ratio': f"{overall_metrics.sortino_ratio:.2f}",
                'max_drawdown': f"{overall_metrics.max_drawdown:.2%}",
                'win_rate': f"{overall_metrics.win_rate:.2%}",
                'total_trades': overall_metrics.total_trades,
                'avg_win': f"{overall_metrics.avg_win:.2%}",
                'avg_loss': f"{overall_metrics.avg_loss:.2%}"
            }
            
            # 기간 요약
            trade_df = self._load_trade_data()
            if not trade_df.empty:
                start_date = trade_df['timestamp'].min()
                end_date = trade_df['timestamp'].max()
                trading_days = (end_date - start_date).days
                
                report['period_summary'] = {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'trading_days': trading_days,
                    'total_trades': len(trade_df[trade_df['action'] == 'SELL'])
                }
            
            # 전략 비교
            strategy_comparisons = self.compare_strategies()
            report['strategy_comparison'] = [
                {
                    'rank': comp.ranking,
                    'strategy_name': comp.strategy_name,
                    'total_return': f"{comp.metrics.total_return:.2%}",
                    'sharpe_ratio': f"{comp.metrics.sharpe_ratio:.2f}",
                    'win_rate': f"{comp.metrics.win_rate:.2%}",
                    'total_trades': comp.total_trades
                }
                for comp in strategy_comparisons[:5]  # 상위 5개 전략만
            ]
            
            # 월별 성과
            monthly_data = self.analyze_monthly_performance()
            report['monthly_performance'] = [
                {
                    'year_month': f"{perf.year}-{perf.month:02d}",
                    'monthly_return': f"{perf.monthly_return:.2%}",
                    'trades': perf.monthly_trades,
                    'win_rate': f"{perf.monthly_win_rate:.2%}",
                    'sharpe_ratio': f"{perf.monthly_sharpe:.2f}"
                }
                for perf in monthly_data
            ]
            
            # 리스크 분석
            risk_metrics = self.calculate_risk_metrics()
            if risk_metrics:
                report['risk_analysis'] = {
                    'value_at_risk_95': f"{risk_metrics.get('var_cvar', {}).get('var_95', 0):.2%}",
                    'max_consecutive_losses': risk_metrics.get('trading_risk', {}).get('max_consecutive_losses', 0),
                    'calmar_ratio': f"{risk_metrics.get('drawdown_analysis', {}).get('calmar_ratio', 0):.2f}",
                    'ulcer_index': f"{risk_metrics.get('drawdown_analysis', {}).get('ulcer_index', 0):.4f}"
                }
            
            # 목표 추적
            current_value = self.initial_capital * (1 + overall_metrics.total_return)
            goal_progress = (current_value - self.initial_capital) / (self.target_capital - self.initial_capital)
            
            report['goal_tracking'] = {
                'initial_capital': f"₩{self.initial_capital:,.0f}",
                'target_capital': f"₩{self.target_capital:,.0f}",
                'current_value': f"₩{current_value:,.0f}",
                'goal_progress': f"{goal_progress:.2%}",
                'remaining_amount': f"₩{self.target_capital - current_value:,.0f}",
                'days_to_goal': self._estimate_days_to_goal(overall_metrics.daily_return_mean, current_value)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"성과 리포트 생성 실패: {e}")
            return {}
    
    def _estimate_days_to_goal(self, daily_return_mean: float, current_value: float) -> str:
        """목표 달성까지 예상 일수 계산"""
        try:
            if daily_return_mean <= 0 or current_value >= self.target_capital:
                return "계산 불가"
            
            # 복리 계산: target = current * (1 + daily_return)^days
            # days = log(target/current) / log(1 + daily_return)
            days_needed = np.log(self.target_capital / current_value) / np.log(1 + daily_return_mean)
            
            if days_needed < 0 or days_needed > 3650:  # 10년 이상이면 계산 불가
                return "10년 이상"
            
            return f"{int(days_needed)}일"
            
        except:
            return "계산 불가"
    def create_performance_charts(self) -> Dict[str, str]:
        """성과 분석 차트 생성"""
        try:
            trade_df = self._load_trade_data()
            if trade_df.empty:
                return {}
            
            portfolio_df = self._calculate_portfolio_values(trade_df)
            if portfolio_df.empty:
                return {}
            
            # 차트 저장 경로
            charts_dir = self.output_dir / "charts"
            charts_dir.mkdir(exist_ok=True)
            
            chart_files = {}
            
            # 1. 포트폴리오 가치 추이 차트
            plt.figure(figsize=(12, 6))
            plt.plot(portfolio_df['date'], portfolio_df['portfolio_value'], linewidth=2, color='#2E86AB')
            plt.axhline(y=self.target_capital, color='red', linestyle='--', alpha=0.7, label=f'목표: ₩{self.target_capital:,.0f}')
            plt.axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.7, label=f'시작: ₩{self.initial_capital:,.0f}')
            plt.title('포트폴리오 가치 추이', fontsize=16, fontweight='bold')
            plt.xlabel('날짜')
            plt.ylabel('포트폴리오 가치 (원)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            portfolio_chart = charts_dir / "portfolio_value.png"
            plt.savefig(portfolio_chart, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files['portfolio_value'] = str(portfolio_chart)
            
            # 2. 일일 수익률 분포 히스토그램
            portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
            daily_returns = portfolio_df['daily_return'].dropna()
            
            plt.figure(figsize=(10, 6))
            plt.hist(daily_returns * 100, bins=30, alpha=0.7, color='#A23B72', edgecolor='black')
            plt.axvline(daily_returns.mean() * 100, color='red', linestyle='--', linewidth=2, label=f'평균: {daily_returns.mean()*100:.2f}%')
            plt.title('일일 수익률 분포', fontsize=16, fontweight='bold')
            plt.xlabel('일일 수익률 (%)')
            plt.ylabel('빈도')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            returns_hist = charts_dir / "daily_returns_distribution.png"
            plt.savefig(returns_hist, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files['returns_distribution'] = str(returns_hist)
            
            # 3. 드로우다운 차트
            cumulative_returns = (1 + daily_returns).cumprod()
            peak = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - peak) / peak
            
            plt.figure(figsize=(12, 6))
            plt.fill_between(portfolio_df['date'][1:], drawdown * 100, 0, alpha=0.7, color='#F18F01')
            plt.title('드로우다운 분석', fontsize=16, fontweight='bold')
            plt.xlabel('날짜')
            plt.ylabel('드로우다운 (%)')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            drawdown_chart = charts_dir / "drawdown_analysis.png"
            plt.savefig(drawdown_chart, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files['drawdown'] = str(drawdown_chart)
            
            # 4. 전략별 성과 비교 차트
            strategy_comparisons = self.compare_strategies()
            if strategy_comparisons:
                strategies = [comp.strategy_name for comp in strategy_comparisons[:5]]
                sharpe_ratios = [comp.metrics.sharpe_ratio for comp in strategy_comparisons[:5]]
                returns = [comp.metrics.total_return * 100 for comp in strategy_comparisons[:5]]
                
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
                
                # 샤프 비율 비교
                bars1 = ax1.bar(strategies, sharpe_ratios, color='#2E86AB', alpha=0.8)
                ax1.set_title('전략별 샤프 비율', fontweight='bold')
                ax1.set_ylabel('샤프 비율')
                ax1.grid(True, alpha=0.3)
                plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
                
                # 수익률 비교
                colors = ['green' if r >= 0 else 'red' for r in returns]
                bars2 = ax2.bar(strategies, returns, color=colors, alpha=0.8)
                ax2.set_title('전략별 수익률', fontweight='bold')
                ax2.set_ylabel('수익률 (%)')
                ax2.grid(True, alpha=0.3)
                plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
                
                plt.tight_layout()
                
                strategy_chart = charts_dir / "strategy_comparison.png"
                plt.savefig(strategy_chart, dpi=300, bbox_inches='tight')
                plt.close()
                chart_files['strategy_comparison'] = str(strategy_chart)
            
            # 5. 월별 성과 히트맵
            monthly_data = self.analyze_monthly_performance(months=12)
            if monthly_data:
                # 데이터 준비
                heat_data = []
                for perf in monthly_data:
                    heat_data.append([perf.year, perf.month, perf.monthly_return * 100])
                
                if heat_data:
                    heat_df = pd.DataFrame(heat_data, columns=['Year', 'Month', 'Return'])
                    pivot_table = heat_df.pivot(index='Year', columns='Month', values='Return')
                    
                    plt.figure(figsize=(12, 6))
                    sns.heatmap(pivot_table, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                               cbar_kws={'label': '월별 수익률 (%)'})
                    plt.title('월별 수익률 히트맵', fontsize=16, fontweight='bold')
                    plt.tight_layout()
                    
                    heatmap_chart = charts_dir / "monthly_heatmap.png"
                    plt.savefig(heatmap_chart, dpi=300, bbox_inches='tight')
                    plt.close()
                    chart_files['monthly_heatmap'] = str(heatmap_chart)
            
            return chart_files
            
        except Exception as e:
            self.logger.error(f"차트 생성 실패: {e}")
            return {}
    
    def backtest_strategy(self, strategy_id: str, start_date: datetime, 
                         end_date: datetime) -> Dict[str, Any]:
        """특정 전략 백테스팅"""
        try:
            # 해당 전략의 거래 데이터만 추출
            trade_df = self._load_trade_data(start_date, end_date)
            strategy_trades = trade_df[trade_df['strategy_id'] == strategy_id]
            
            if strategy_trades.empty:
                return {'error': f'전략 {strategy_id}의 거래 데이터가 없습니다.'}
            
            # 백테스트 결과 계산
            initial_value = 50000  # 전략당 할당 자본
            portfolio_values = []
            current_value = initial_value
            positions = {}
            trades_executed = []
            
            for _, trade in strategy_trades.iterrows():
                trade_info = {
                    'timestamp': trade['timestamp'],
                    'action': trade['action'],
                    'ticker': trade['ticker'],
                    'price': trade['price'],
                    'quantity': trade['quantity'],
                    'total_amount': trade['total_amount']
                }
                
                if trade['action'] == 'BUY':
                    current_value -= trade['total_amount'] + trade['commission']
                    positions[trade['ticker']] = positions.get(trade['ticker'], 0) + trade['quantity']
                    
                elif trade['action'] == 'SELL':
                    current_value += trade['total_amount'] - trade['commission']
                    positions[trade['ticker']] = positions.get(trade['ticker'], 0) - trade['quantity']
                    
                    # 수익률 계산
                    if trade['profit_ratio']:
                        trade_info['profit_ratio'] = trade['profit_ratio']
                
                trades_executed.append(trade_info)
                
                portfolio_values.append({
                    'timestamp': trade['timestamp'],
                    'portfolio_value': current_value,
                    'total_return': (current_value - initial_value) / initial_value
                })
            
            # 백테스트 통계 계산
            final_value = portfolio_values[-1]['portfolio_value'] if portfolio_values else initial_value
            total_return = (final_value - initial_value) / initial_value
            
            sell_trades = strategy_trades[strategy_trades['action'] == 'SELL']
            total_trades = len(sell_trades)
            winning_trades = len(sell_trades[sell_trades['profit_ratio'] > 0])
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            avg_win = sell_trades[sell_trades['profit_ratio'] > 0]['profit_ratio'].mean() if winning_trades > 0 else 0
            avg_loss = sell_trades[sell_trades['profit_ratio'] <= 0]['profit_ratio'].mean() if (total_trades - winning_trades) > 0 else 0
            
            # 최대 드로우다운 계산
            portfolio_df = pd.DataFrame(portfolio_values)
            if not portfolio_df.empty and len(portfolio_df) > 1:
                daily_returns = portfolio_df['portfolio_value'].pct_change().dropna()
                cumulative_returns = (1 + daily_returns).cumprod()
                peak = cumulative_returns.expanding().max()
                drawdown = (cumulative_returns - peak) / peak
                max_drawdown = drawdown.min()
                
                # 샤프 비율
                volatility = daily_returns.std() * np.sqrt(365.25)
                days = len(portfolio_df)
                annualized_return = (1 + total_return) ** (365.25 / days) - 1 if days > 0 else 0
                sharpe_ratio = (annualized_return - self.risk_free_rate) / volatility if volatility > 0 else 0
            else:
                max_drawdown = 0
                sharpe_ratio = 0
                annualized_return = 0
            
            return {
                'strategy_id': strategy_id,
                'backtest_period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'duration_days': (end_date - start_date).days
                },
                'performance': {
                    'initial_value': initial_value,
                    'final_value': final_value,
                    'total_return': f"{total_return:.2%}",
                    'annualized_return': f"{annualized_return:.2%}",
                    'max_drawdown': f"{max_drawdown:.2%}",
                    'sharpe_ratio': f"{sharpe_ratio:.2f}"
                },
                'trading_stats': {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': total_trades - winning_trades,
                    'win_rate': f"{win_rate:.2%}",
                    'avg_win': f"{avg_win:.2%}",
                    'avg_loss': f"{avg_loss:.2%}",
                    'profit_factor': f"{abs(avg_win * winning_trades / (avg_loss * (total_trades - winning_trades))):.2f}" if avg_loss != 0 and (total_trades - winning_trades) > 0 else "N/A"
                },
                'portfolio_values': portfolio_values,
                'trades_executed': trades_executed[-10:]  # 최근 10개 거래만
            }
            
        except Exception as e:
            self.logger.error(f"백테스팅 실패: {e}")
            return {'error': str(e)}
    
    def export_detailed_report(self, format: str = 'json') -> str:
        """상세 리포트 내보내기"""
        try:
            # 종합 리포트 생성
            report = self.generate_performance_report()
            
            # 추가 상세 정보
            detailed_report = {
                **report,
                'detailed_metrics': self.calculate_performance_metrics().__dict__,
                'risk_metrics': self.calculate_risk_metrics(),
                'strategy_details': [comp.__dict__ for comp in self.compare_strategies()],
                'monthly_details': [perf.__dict__ for perf in self.analyze_monthly_performance(months=12)]
            }
            
            # 파일 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format.lower() == 'json':
                filename = self.output_dir / f"detailed_report_{timestamp}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(detailed_report, f, ensure_ascii=False, indent=2, default=str)
            
            elif format.lower() == 'csv':
                # CSV로 주요 지표만 저장
                filename = self.output_dir / f"performance_summary_{timestamp}.csv"
                
                # 기본 지표를 DataFrame으로 변환
                metrics_dict = {
                    '지표': ['총 수익률', '연환산 수익률', '변동성', '샤프 비율', '최대 낙폭', '승률', '총 거래수'],
                    '값': [
                        f"{detailed_report['detailed_metrics']['total_return']:.2%}",
                        f"{detailed_report['detailed_metrics']['annualized_return']:.2%}",
                        f"{detailed_report['detailed_metrics']['volatility']:.2%}",
                        f"{detailed_report['detailed_metrics']['sharpe_ratio']:.2f}",
                        f"{detailed_report['detailed_metrics']['max_drawdown']:.2%}",
                        f"{detailed_report['detailed_metrics']['win_rate']:.2%}",
                        str(detailed_report['detailed_metrics']['total_trades'])
                    ]
                }
                
                df = pd.DataFrame(metrics_dict)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"상세 리포트 저장: {filename}")
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"리포트 내보내기 실패: {e}")
            return ""
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """실시간 성과 지표 (대시보드용)"""
        try:
            # 최근 7일 데이터
            start_date = datetime.now() - timedelta(days=7)
            recent_metrics = self.calculate_performance_metrics(start_date=start_date)
            
            # 전체 기간 데이터
            overall_metrics = self.calculate_performance_metrics()
            
            # 현재 포트폴리오 가치
            current_value = self.initial_capital * (1 + overall_metrics.total_return)
            goal_progress = (current_value - self.initial_capital) / (self.target_capital - self.initial_capital)
            
            return {
                'current_performance': {
                    'current_value': current_value,
                    'total_return': overall_metrics.total_return,
                    'goal_progress': goal_progress,
                    'days_to_goal': self._estimate_days_to_goal(overall_metrics.daily_return_mean, current_value)
                },
                'recent_performance': {
                    'weekly_return': recent_metrics.total_return,
                    'weekly_sharpe': recent_metrics.sharpe_ratio,
                    'weekly_trades': recent_metrics.total_trades,
                    'weekly_win_rate': recent_metrics.win_rate
                },
                'overall_metrics': {
                    'sharpe_ratio': overall_metrics.sharpe_ratio,
                    'max_drawdown': overall_metrics.max_drawdown,
                    'total_trades': overall_metrics.total_trades,
                    'win_rate': overall_metrics.win_rate,
                    'volatility': overall_metrics.volatility
                }
            }
            
        except Exception as e:
            self.logger.error(f"실시간 지표 계산 실패: {e}")
            return {}


# 유틸리티 함수들
def get_performance_tracker(db_manager=None) -> PerformanceTracker:
    """성과 추적기 인스턴스 생성"""
    return PerformanceTracker(db_manager)

def quick_performance_summary() -> Dict[str, Any]:
    """빠른 성과 요약"""
    try:
        tracker = PerformanceTracker()
        return tracker.get_real_time_metrics()
    except Exception as e:
        logging.error(f"빠른 성과 요약 실패: {e}")
        return {}

# 실행 예제
if __name__ == "__main__":
    # 성과 추적기 테스트
    tracker = PerformanceTracker()
    
    print("🔍 성과 분석 시작...")
    
    # 전체 성과 지표
    metrics = tracker.calculate_performance_metrics()
    print(f"총 수익률: {metrics.total_return:.2%}")
    print(f"샤프 비율: {metrics.sharpe_ratio:.2f}")
    print(f"최대 낙폭: {metrics.max_drawdown:.2%}")
    print(f"승률: {metrics.win_rate:.2%}")
    
    # 전략 비교
    comparisons = tracker.compare_strategies()
    print(f"\n📊 전략 비교 ({len(comparisons)}개):")
    for comp in comparisons[:3]:
        print(f"{comp.ranking}. {comp.strategy_name}: {comp.metrics.total_return:.2%} (샤프: {comp.metrics.sharpe_ratio:.2f})")
    
    # 상세 리포트 생성
    report_file = tracker.export_detailed_report('json')
    print(f"\n📄 상세 리포트 저장: {report_file}")
    
    # 차트 생성
    charts = tracker.create_performance_charts()
    print(f"\n📈 생성된 차트: {len(charts)}개")
    for chart_name, path in charts.items():
        print(f"  - {chart_name}: {path}")
    
    print("\n✅ 성과 분석 완료!")                
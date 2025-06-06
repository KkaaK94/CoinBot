"""
설정 관리 모듈
모든 설정값을 중앙에서 관리
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

@dataclass
class TradingConfig:
    """매매 관련 설정"""
    initial_capital: int = 160000       # 초기 자본
    target_capital: int = 500000        # 목표 자본
    max_positions: int = 3              # 최대 포지션 수
    capital_per_position: int = 50000   # 포지션당 자본
    
    # 리스크 관리
    max_daily_loss: float = 0.08        # 최대 일일 손실률
    max_position_loss: float = 0.10     # 최대 포지션 손실률
    stop_loss_ratio: float = 0.08       # 손절 비율
    take_profit_ratio: float = 0.15     # 익절 비율
    
    # 매매 주기
    analysis_interval: int = 180        # 분석 주기 (초)
    min_order_amount: int = 5000        # 최소 주문 금액

@dataclass
class AnalysisConfig:
    """분석 관련 설정"""
    target_coins: List[str] = None      # 분석 대상 코인
    timeframes: List[str] = None        # 시간봉 종류
    
    # 기술적 지표 설정
    rsi_period: int = 14
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    ma_short: int = 5
    ma_long: int = 20
    
    # 점수 시스템
    min_score_threshold: int = 75       # 최소 진입 점수
    max_score: int = 100               # 최대 점수
    
    def __post_init__(self):
        if self.target_coins is None:
            self.target_coins = [
                'KRW-BTC', 'KRW-ETH', 'KRW-SOL', 'KRW-ADA',
                'KRW-MATIC', 'KRW-ATOM', 'KRW-DOT', 'KRW-AVAX'
            ]
        
        if self.timeframes is None:
            self.timeframes = ['minute1', 'minute3', 'minute5']

@dataclass
class DatabaseConfig:
    """데이터베이스 설정"""
    db_path: str = "data/coinbot.db"
    backup_interval: int = 3600         # 백업 주기 (초)
    log_retention_days: int = 30        # 로그 보존 기간

@dataclass
class NotificationConfig:
    """알림 설정"""
    telegram_enabled: bool = True
    email_enabled: bool = False
    
    # 알림 주기
    trade_notifications: bool = True    # 거래 알림
    portfolio_update_interval: int = 3600  # 포트폴리오 업데이트 주기
    error_notifications: bool = True    # 오류 알림

@dataclass
class DashboardConfig:
    """대시보드 설정"""
    host: str = "0.0.0.0"
    port: int = 8050
    debug: bool = False
    auto_refresh_interval: int = 30     # 자동 새로고침 (초)

class Settings:
    """통합 설정 클래스"""
    
    def __init__(self):
        # 환경변수 검증
        self._validate_env_vars()
        
        # 각 설정 섹션 초기화
        self.trading = TradingConfig()
        self.analysis = AnalysisConfig()
        self.database = DatabaseConfig()
        self.notification = NotificationConfig()
        self.dashboard = DashboardConfig()
        
        # API 설정
        self.upbit_access_key = os.getenv('UPBIT_ACCESS_KEY')
        self.upbit_secret_key = os.getenv('UPBIT_SECRET_KEY')
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # 환경 설정
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # 프로젝트 경로
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.data_dir / "logs"
        
        # 디렉토리 생성
        self._create_directories()
        
        # 환경별 설정 조정
        self._adjust_for_environment()
    
    def _validate_env_vars(self):
        """필수 환경변수 검증"""
        required_vars = [
            'UPBIT_ACCESS_KEY',
            'UPBIT_SECRET_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"필수 환경변수가 설정되지 않았습니다: {missing_vars}")
    
    def _create_directories(self):
        """필요한 디렉토리 생성"""
        directories = [
            self.data_dir,
            self.logs_dir,
            self.data_dir / "trades",
            self.data_dir / "strategies", 
            self.data_dir / "backups"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _adjust_for_environment(self):
        """환경별 설정 조정"""
        if self.environment == 'production':
            # 운영환경에서는 더 보수적으로
            self.trading.max_daily_loss = 0.05
            self.trading.stop_loss_ratio = 0.06
            self.analysis.min_score_threshold = 80
            self.dashboard.debug = False
            
        elif self.environment == 'development':
            # 개발환경에서는 더 관대하게
            self.trading.analysis_interval = 60  # 1분마다 분석
            self.dashboard.debug = True
            self.dashboard.auto_refresh_interval = 10
    
    def get_target_coins(self) -> List[str]:
        """분석 대상 코인 리스트 반환"""
        return self.analysis.target_coins.copy()
    
    def get_trading_pairs(self) -> Dict[str, Dict]:
        """거래 페어별 설정 반환"""
        pairs = {}
        for coin in self.analysis.target_coins:
            pairs[coin] = {
                'min_order_amount': self.trading.min_order_amount,
                'stop_loss': self.trading.stop_loss_ratio,
                'take_profit': self.trading.take_profit_ratio
            }
        return pairs
    
    def update_trading_config(self, **kwargs):
        """매매 설정 동적 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self.trading, key):
                setattr(self.trading, key, value)
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """분석 설정을 딕셔너리로 반환"""
        return {
            'rsi_period': self.analysis.rsi_period,
            'rsi_oversold': self.analysis.rsi_oversold,
            'rsi_overbought': self.analysis.rsi_overbought,
            'macd_fast': self.analysis.macd_fast,
            'macd_slow': self.analysis.macd_slow,
            'macd_signal': self.analysis.macd_signal,
            'ma_short': self.analysis.ma_short,
            'ma_long': self.analysis.ma_long
        }
    
    def is_production(self) -> bool:
        """운영환경 여부 확인"""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """개발환경 여부 확인"""
        return self.environment == 'development'
    
    def __str__(self):
        """설정 정보 출력"""
        return f"""
CoinBot Settings:
- Environment: {self.environment}
- Initial Capital: {self.trading.initial_capital:,}원
- Target Capital: {self.trading.target_capital:,}원
- Max Positions: {self.trading.max_positions}
- Analysis Interval: {self.trading.analysis_interval}초
- Target Coins: {len(self.analysis.target_coins)}개
- Min Score Threshold: {self.analysis.min_score_threshold}점
"""

# 전역 설정 인스턴스
settings = Settings()
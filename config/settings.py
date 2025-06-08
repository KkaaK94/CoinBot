"""
트레이딩 봇 설정 관리
- 환경별 설정 분리
- 동적 설정 로드
- 설정 검증
- 안전 모드 지원
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent

@dataclass
class TradingConfig:
    """거래 관련 설정"""
    # 기본 거래 설정
    trade_amount: float = 50000  # 거래 금액 (원)
    max_position_size: float = 500000  # 최대 포지션 크기
    min_trade_amount: float = 5000  # 최소 거래 금액
    
    # 리스크 관리
    stop_loss_percent: float = 5.0  # 손절매 %
    take_profit_percent: float = 10.0  # 익절 %
    max_daily_loss: float = 100000  # 일일 최대 손실
    
    # 거래 제한
    max_trades_per_day: int = 20  # 일일 최대 거래 수
    trade_cooldown_minutes: int = 30  # 거래 쿨다운 (분)
    
    # 대상 코인
    target_coins: List[str] = field(default_factory=lambda: [
        "KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-ADA", "KRW-DOT"
    ])

@dataclass
class IndicatorConfig:
    """기술적 지표 설정"""
    # RSI 설정
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    
    # MACD 설정
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # 이동평균 설정
    ma_short: int = 20
    ma_long: int = 50
    
    # 볼린저 밴드
    bb_period: int = 20
    bb_std: float = 2.0

@dataclass
class SystemConfig:
    """시스템 설정"""
    # 데이터 수집
    data_interval: str = "minute1"  # 1분봉
    lookback_days: int = 30  # 과거 데이터 일수
    
    # 로깅
    log_level: str = "INFO"
    log_file: str = "logs/trading_bot.log"
    
    # 모니터링
    health_check_interval: int = 60  # 헬스체크 간격 (초)
    telegram_alert_interval: int = 300  # 텔레그램 알림 간격 (초)
    
    # 백업
    backup_interval_hours: int = 24
    max_backup_files: int = 7

@dataclass
class APIConfig:
    """API 설정"""
    # 업비트 API
    upbit_access_key: str = ""
    upbit_secret_key: str = ""
    
    # 텔레그램 API
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # API 제한
    api_request_delay: float = 0.1  # API 요청 간격 (초)
    max_retries: int = 3  # 최대 재시도 횟수

class Settings:
    """통합 설정 관리 클래스"""
    
    def __init__(self, config_file: Optional[str] = None, safe_mode: bool = False):
        self.safe_mode = safe_mode
        self.config_file = config_file or str(PROJECT_ROOT / "config" / "settings.json")
        
        # 환경 변수 로드
        self.load_environment()
        
        # 설정 로드
        self.load_settings()
        
        # 설정 검증
        self.validate_settings()
    
    def load_environment(self):
        """환경 변수 로드"""
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            load_dotenv(env_file)
    
    def load_settings(self):
        """설정 파일 로드"""
        # 기본 설정
        self.trading = TradingConfig()
        self.indicators = IndicatorConfig()
        self.system = SystemConfig()
        self.api = APIConfig()
        
        # 환경 변수에서 API 설정 로드
        self.api.upbit_access_key = os.getenv("UPBIT_ACCESS_KEY", "")
        self.api.upbit_secret_key = os.getenv("UPBIT_SECRET_KEY", "")
        self.api.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.api.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # 설정 파일에서 추가 설정 로드
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self.update_from_dict(config_data)
            except Exception as e:
                logging.warning(f"설정 파일 로드 실패: {e}")
        
        # 안전 모드 설정 적용
        if self.safe_mode:
            self.apply_safe_mode()
    
    def apply_safe_mode(self):
        """안전 모드 설정 적용"""
        # 거래 금액을 최소 금액보다 크게 설정
        self.trading.trade_amount = 10000  # 최소 금액보다 크게
        self.trading.max_position_size = 50000
        self.trading.max_daily_loss = 20000
        
        # 보수적인 지표 설정
        self.indicators.rsi_oversold = 25.0
        self.indicators.rsi_overbought = 75.0
        
        # 알림 간격 단축
        self.system.telegram_alert_interval = 60
        
        logging.info("안전 모드가 적용되었습니다.")
    
    def update_from_dict(self, config_dict: Dict[str, Any]):
        """딕셔너리에서 설정 업데이트"""
        if "trading" in config_dict:
            for key, value in config_dict["trading"].items():
                if hasattr(self.trading, key):
                    setattr(self.trading, key, value)
        
        if "indicators" in config_dict:
            for key, value in config_dict["indicators"].items():
                if hasattr(self.indicators, key):
                    setattr(self.indicators, key, value)
        
        if "system" in config_dict:
            for key, value in config_dict["system"].items():
                if hasattr(self.system, key):
                    setattr(self.system, key, value)
    
    def validate_settings(self):
        """설정 검증"""
        errors = []
        
        # API 키 검증
        if not self.api.upbit_access_key:
            errors.append("UPBIT_ACCESS_KEY가 설정되지 않았습니다")
        if not self.api.upbit_secret_key:
            errors.append("UPBIT_SECRET_KEY가 설정되지 않았습니다")
        if not self.api.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다")
        if not self.api.telegram_chat_id:
            errors.append("TELEGRAM_CHAT_ID가 설정되지 않았습니다")
        
        # 거래 설정 검증
        if self.trading.trade_amount < self.trading.min_trade_amount:
            errors.append(f"거래 금액이 최소 금액({self.trading.min_trade_amount})보다 작습니다")
        
        if self.trading.stop_loss_percent <= 0 or self.trading.stop_loss_percent > 50:
            errors.append("손절매 비율이 잘못되었습니다 (0-50% 범위)")
        
        # 지표 설정 검증
        if self.indicators.rsi_period < 5 or self.indicators.rsi_period > 50:
            errors.append("RSI 기간이 잘못되었습니다 (5-50 범위)")
        
        if errors:
            error_msg = "설정 검증 실패:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_msg)
    
    def save_settings(self, file_path: Optional[str] = None):
        """설정을 파일로 저장"""
        save_path = file_path or self.config_file
        
        config_data = {
            "trading": {
                "trade_amount": self.trading.trade_amount,
                "max_position_size": self.trading.max_position_size,
                "stop_loss_percent": self.trading.stop_loss_percent,
                "take_profit_percent": self.trading.take_profit_percent,
                "target_coins": self.trading.target_coins
            },
            "indicators": {
                "rsi_period": self.indicators.rsi_period,
                "rsi_oversold": self.indicators.rsi_oversold,
                "rsi_overbought": self.indicators.rsi_overbought,
                "macd_fast": self.indicators.macd_fast,
                "macd_slow": self.indicators.macd_slow,
                "macd_signal": self.indicators.macd_signal
            },
            "system": {
                "log_level": self.system.log_level,
                "data_interval": self.system.data_interval,
                "lookback_days": self.system.lookback_days
            }
        }
        
        # 설정 파일 디렉토리 생성
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def get_coin_config(self, symbol: str) -> Dict[str, Any]:
        """특정 코인에 대한 설정 반환"""
        return {
            "trade_amount": self.trading.trade_amount,
            "stop_loss": self.trading.stop_loss_percent,
            "take_profit": self.trading.take_profit_percent,
            "rsi_oversold": self.indicators.rsi_oversold,
            "rsi_overbought": self.indicators.rsi_overbought
        }
    
    def is_trading_allowed(self) -> bool:
        """거래 허용 여부 확인"""
        if self.safe_mode:
            return False  # 안전 모드에서는 실제 거래 금지
        
        # API 키가 있는지 확인
        return bool(self.api.upbit_access_key and self.api.upbit_secret_key)
    
    def get_log_config(self) -> Dict[str, Any]:
        """로깅 설정 반환"""
        return {
            "level": self.system.log_level,
            "file": self.system.log_file,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    
    def __str__(self) -> str:
        """설정 정보 문자열 표현"""
        return f"""
트레이딩 봇 설정:
- 모드: {'안전 모드' if self.safe_mode else '실제 거래'}
- 거래 금액: {self.trading.trade_amount:,}원
- 최대 포지션: {self.trading.max_position_size:,}원
- 손절매: {self.trading.stop_loss_percent}%
- 대상 코인: {len(self.trading.target_coins)}개
- RSI 기간: {self.indicators.rsi_period}
        """

# 전역 설정 인스턴스
_settings_instance = None

def get_settings(safe_mode: bool = False) -> Settings:
    """설정 인스턴스 반환 (싱글톤)"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings(safe_mode=safe_mode)
    return _settings_instance

def reload_settings(safe_mode: bool = False):
    """설정 다시 로드"""
    global _settings_instance
    _settings_instance = Settings(safe_mode=safe_mode)
    return _settings_instance

# 개발용 테스트 함수
def test_settings():
    """설정 테스트"""
    try:
        settings = Settings(safe_mode=True)
        print("설정 로드 성공!")
        print(settings)
        return True
    except Exception as e:
        print(f"설정 로드 실패: {e}")
        return False

# 하위 호환성을 위한 전역 settings 인스턴스
settings = None

def init_settings(safe_mode: bool = False):
    """설정 초기화"""
    global settings
    settings = Settings(safe_mode=safe_mode)
    return settings

# 기본 설정 인스턴스 생성 (즉시 생성하지 않음)
def get_default_settings():
    """기본 설정 반환"""
    global settings
    if settings is None:
        # 안전 모드 기본값으로 초기화
        settings = Settings(safe_mode=True)
    return settings

if __name__ == "__main__":
    # 설정 테스트 실행
    print("설정 파일 테스트 중...")
    try:
        test_settings = Settings(safe_mode=True)
        print("설정 로드 성공!")
        print(test_settings)
        print("모든 설정이 정상적으로 로드되었습니다.")
    except Exception as e:
        print(f"설정 로드 실패: {e}")
        print("설정에 문제가 있습니다. 위 오류를 확인하세요.")
#!/usr/bin/env python3
"""
🛡️ CoinBot 고도화된 에러 핸들링 및 복구 시스템
- API 연결 끊김 자동 재연결
- 네트워크 오류 백오프 전략
- 데이터 수집 실패 시 대체 소스 활용
- 치명적 오류 발생 시 안전 모드 전환
- 실시간 오류 모니터링 및 알림
- 자동 복구 및 재시작 메커니즘
"""

import asyncio
import time
import json
import logging
import traceback
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import requests
import threading
from functools import wraps

# ⚠️ 자동 업데이트 시스템 유지 필수!
try:
    from utils.auto_updater import log_config_change, log_bug_fix, log_feature_add
    AUTO_UPDATER_AVAILABLE = True
except ImportError:
    print("⚠️ auto_updater 모듈 없음 - 기본 로깅 사용")
    AUTO_UPDATER_AVAILABLE = False
    def log_config_change(*args, **kwargs): pass
    def log_bug_fix(*args, **kwargs): pass
    def log_feature_add(*args, **kwargs): pass

# 텔레그램 알림 연동
try:
    from utils.telegram_bot import TelegramBot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    TelegramBot = None

class ErrorSeverity(Enum):
    """에러 심각도 레벨"""
    LOW = "low"           # 경고 수준
    MEDIUM = "medium"     # 주의 필요
    HIGH = "high"         # 즉시 대응 필요
    CRITICAL = "critical" # 시스템 중단 위험

class ErrorCategory(Enum):
    """에러 카테고리"""
    NETWORK = "network"               # 네트워크 관련
    API = "api"                      # API 호출 관련  
    DATA_COLLECTION = "data_collection" # 데이터 수집 관련
    TRADING = "trading"              # 거래 실행 관련
    DATABASE = "database"            # 데이터베이스 관련
    SYSTEM = "system"                # 시스템 리소스 관련
    UNKNOWN = "unknown"              # 분류되지 않은 오류

@dataclass
class ErrorEvent:
    """에러 이벤트 데이터 클래스"""
    timestamp: str
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    traceback_info: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    retry_count: int = 0
    max_retries: int = 3
    context: Optional[Dict[str, Any]] = None

@dataclass
class RecoveryStrategy:
    """복구 전략 정의"""
    name: str
    description: str
    max_attempts: int
    delay_seconds: float
    backoff_multiplier: float
    recovery_function: Callable
    success_rate: float = 0.0
    last_used: Optional[datetime] = None

@dataclass
class SystemHealth:
    """시스템 건강도 지표"""
    overall_score: float = 100.0
    api_connection_score: float = 100.0
    data_collection_score: float = 100.0
    trading_system_score: float = 100.0
    network_stability_score: float = 100.0
    error_rate_score: float = 100.0
    last_critical_error: Optional[datetime] = None
    consecutive_errors: int = 0
    recovery_success_rate: float = 0.0

class EnhancedErrorHandler:
    """고도화된 에러 핸들링 시스템"""
    
    def __init__(self, config_file: Optional[str] = None):
        """에러 핸들러 초기화"""
        self.config = self._load_config(config_file)
        self.error_history: List[ErrorEvent] = []
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}
        self.system_health = SystemHealth()
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.emergency_mode = False
        self.safe_mode = False
        
        # 로깅 설정
        self._setup_logging()
        
        # 자동 업데이트 시스템 로깅
        try:
            log_feature_add("utils/enhanced_error_handler.py", "고도화된 에러 핸들링 시스템 초기화")
        except:
            pass
        
        # 텔레그램 봇 초기화
        self.telegram_bot = self._init_telegram_bot()
        
        # 기본 복구 전략 등록
        self._register_default_recovery_strategies()
        
        # 에러 통계 추적
        self.error_stats = {
            'total_errors': 0,
            'recovered_errors': 0,
            'critical_errors': 0,
            'last_24h_errors': [],
            'most_common_errors': {},
            'recovery_success_rate': 0.0
        }
        
        # 백그라운드 모니터링 시작
        self.monitoring_thread = None
        self.monitoring_active = False
        self._start_background_monitoring()
        
        self.logger.info("🛡️ 고도화된 에러 핸들링 시스템 초기화 완료")
        
        try:
            log_feature_add("utils/enhanced_error_handler.py", "에러 핸들링 시스템 시작")
        except:
            pass

    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """설정 파일 로드"""
        default_config = {
            "max_error_history": 1000,
            "alert_cooldown_minutes": 15,
            "emergency_mode_threshold": 10,  # 10개 이상 연속 치명적 오류
            "auto_recovery_enabled": True,
            "safe_mode_timeout_minutes": 30,
            "health_check_interval": 60,
            "retry_delays": {
                "network": [1, 3, 5, 10, 30],
                "api": [2, 5, 10, 20],
                "data_collection": [1, 2, 5, 10],
                "database": [3, 6, 12]
            },
            "max_retries": {
                "network": 5,
                "api": 4,
                "data_collection": 4,
                "database": 3
            },
            "alert_thresholds": {
                "error_rate_per_hour": 20,
                "consecutive_failures": 5,
                "health_score_minimum": 70
            }
        }
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    
                try:
                    log_config_change("utils/enhanced_error_handler.py", "설정 파일 로드 완료", 
                                    {"config_file": config_file})
                except:
                    pass
                    
            except Exception as e:
                print(f"⚠️ 설정 파일 로드 실패: {e}")
                
        return default_config
    
    def _setup_logging(self):
        """에러 핸들링 전용 로깅 설정"""
        self.logger = logging.getLogger('EnhancedErrorHandler')
        self.logger.setLevel(logging.INFO)
        
        # 로그 디렉토리 생성
        log_dir = Path("data/logs/error_handling")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 핸들러가 이미 있으면 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 에러 전용 파일 핸들러
        from logging.handlers import RotatingFileHandler
        error_handler = RotatingFileHandler(
            log_dir / "error_handling.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        # 크리티컬 에러 전용 핸들러
        critical_handler = RotatingFileHandler(
            log_dir / "critical_errors.log",
            maxBytes=5*1024*1024,   # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        critical_handler.setLevel(logging.CRITICAL)
        critical_handler.setFormatter(formatter)
        self.logger.addHandler(critical_handler)
    
    def _init_telegram_bot(self):
        """텔레그램 봇 초기화"""
        if not TELEGRAM_AVAILABLE:
            return None
        
        try:
            bot = TelegramBot()
            self.logger.info("📱 에러 알림용 텔레그램 봇 초기화 완료")
            return bot
        except Exception as e:
            self.logger.warning(f"텔레그램 봇 초기화 실패: {e}")
            return None
    
    def _register_default_recovery_strategies(self):
        """기본 복구 전략들 등록"""
        
        # 네트워크 연결 복구
        self.recovery_strategies["network_reconnect"] = RecoveryStrategy(
            name="network_reconnect",
            description="네트워크 연결 재시도",
            max_attempts=5,
            delay_seconds=2.0,
            backoff_multiplier=1.5,
            recovery_function=self._recover_network_connection
        )
        
        # API 재연결
        self.recovery_strategies["api_reconnect"] = RecoveryStrategy(
            name="api_reconnect",
            description="API 연결 재시도",
            max_attempts=4,
            delay_seconds=3.0,
            backoff_multiplier=2.0,
            recovery_function=self._recover_api_connection
        )
        
        # 데이터 수집 복구
        self.recovery_strategies["data_collection_recovery"] = RecoveryStrategy(
            name="data_collection_recovery",
            description="데이터 수집 대체 소스 사용",
            max_attempts=3,
            delay_seconds=1.0,
            backoff_multiplier=1.0,
            recovery_function=self._recover_data_collection
        )
        
        # 데이터베이스 복구
        self.recovery_strategies["database_recovery"] = RecoveryStrategy(
            name="database_recovery",
            description="데이터베이스 연결 복구",
            max_attempts=3,
            delay_seconds=5.0,
            backoff_multiplier=1.5,
            recovery_function=self._recover_database_connection
        )
        
        # 시스템 리소스 정리
        self.recovery_strategies["system_cleanup"] = RecoveryStrategy(
            name="system_cleanup",
            description="시스템 리소스 정리 및 최적화",
            max_attempts=2,
            delay_seconds=10.0,
            backoff_multiplier=1.0,
            recovery_function=self._perform_system_cleanup
        )
        
        self.logger.info(f"✅ {len(self.recovery_strategies)}개 기본 복구 전략 등록 완료")

    def _start_background_monitoring(self):
        """백그라운드 시스템 모니터링 시작"""
        def monitoring_loop():
            while self.monitoring_active:
                try:
                    # 시스템 건강도 체크
                    self._update_system_health()
                    
                    # 에러 통계 업데이트
                    self._update_error_statistics()
                    
                    # 긴급 모드 체크
                    self._check_emergency_conditions()
                    
                    # 자동 복구 시도
                    if self.config["auto_recovery_enabled"]:
                        self._attempt_auto_recovery()
                    
                    time.sleep(self.config["health_check_interval"])
                    
                except Exception as e:
                    self.logger.error(f"모니터링 루프 오류: {e}")
                    time.sleep(60)  # 오류 시 1분 대기
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("🔍 백그라운드 시스템 모니터링 시작")

    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None, 
                    category: Optional[ErrorCategory] = None) -> ErrorEvent:
        """통합 에러 처리 메인 함수"""
        try:
            # 에러 분류 및 심각도 판단
            if category is None:
                category = self._classify_error(error)
            
            severity = self._assess_severity(error, category)
            
            # 에러 이벤트 생성
            error_event = ErrorEvent(
                timestamp=datetime.now().isoformat(),
                error_id=self._generate_error_id(),
                category=category,
                severity=severity,
                message=str(error),
                details={
                    "error_type": type(error).__name__,
                    "error_args": error.args,
                    "context": context or {}
                },
                traceback_info=traceback.format_exc(),
                context=context
            )
            
            # 에러 히스토리에 추가
            self.error_history.append(error_event)
            self._cleanup_old_errors()
            
            # 통계 업데이트
            self._update_error_stats(error_event)
            
            # 로깅
            self._log_error_event(error_event)
            
            # 자동 업데이트 시스템 로깅
            try:
                log_bug_fix("utils/enhanced_error_handler.py", 
                           f"에러 처리됨: {category.value} - {severity.value}")
            except:
                pass
            
            # 복구 시도
            if self.config["auto_recovery_enabled"] and severity in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]:
                recovery_success = self._attempt_recovery(error_event)
                error_event.recovery_attempted = True
                error_event.recovery_successful = recovery_success
            
            # 알림 발송
            self._send_alert_if_needed(error_event)
            
            # 시스템 건강도 업데이트
            self._update_health_after_error(error_event)
            
            # 긴급 모드 체크
            if severity == ErrorSeverity.CRITICAL:
                self._check_emergency_mode_trigger()
            
            return error_event
            
        except Exception as e:
            # 에러 핸들러 자체에서 오류 발생 시
            self.logger.critical(f"에러 핸들러 내부 오류: {e}")
            try:
                log_bug_fix("utils/enhanced_error_handler.py", 
                           f"에러 핸들러 내부 오류 수정: {str(e)}")
            except:
                pass
            
            # 기본 에러 이벤트 반환
            return ErrorEvent(
                timestamp=datetime.now().isoformat(),
                error_id="handler_error",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                message=f"에러 핸들러 오류: {str(e)}",
                details={"original_error": str(error)}
            )
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """에러 자동 분류"""
        error_message = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # 네트워크 관련 에러
        if any(keyword in error_message for keyword in [
            'connection', 'network', 'timeout', 'unreachable', 'dns', 'socket'
        ]) or any(keyword in error_type for keyword in [
            'connectionerror', 'timeout', 'networkerror'
        ]):
            return ErrorCategory.NETWORK
        
        # API 관련 에러
        if any(keyword in error_message for keyword in [
            'api', 'http', 'status', '401', '403', '429', '500', '502', '503'
        ]) or any(keyword in error_type for keyword in [
            'httperror', 'apierror', 'requestexception'
        ]):
            return ErrorCategory.API
        
        # 데이터 수집 관련 에러
        if any(keyword in error_message for keyword in [
            'data', 'collect', 'fetch', 'parse', 'json', 'response'
        ]):
            return ErrorCategory.DATA_COLLECTION
        
        # 거래 관련 에러
        if any(keyword in error_message for keyword in [
            'trade', 'order', 'balance', 'insufficient', 'market'
        ]):
            return ErrorCategory.TRADING
        
        # 데이터베이스 관련 에러
        if any(keyword in error_message for keyword in [
            'database', 'sql', 'sqlite', 'table', 'column'
        ]) or any(keyword in error_type for keyword in [
            'databaseerror', 'sqliteerror'
        ]):
            return ErrorCategory.DATABASE
        
        # 시스템 관련 에러
        if any(keyword in error_message for keyword in [
            'memory', 'disk', 'cpu', 'resource', 'permission'
        ]) or any(keyword in error_type for keyword in [
            'memoryerror', 'oserror', 'permissionerror'
        ]):
            return ErrorCategory.SYSTEM
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """에러 심각도 평가"""
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # 치명적 에러 조건들
        critical_conditions = [
            'outofmemoryerror' in error_type.lower(),
            'systemerror' in error_type.lower(),
            'insufficient funds' in error_message,
            'api key' in error_message and 'invalid' in error_message,
            'database locked' in error_message,
            self.system_health.consecutive_errors > 5
        ]
        
        if any(critical_conditions):
            return ErrorSeverity.CRITICAL
        
        # 높은 심각도 조건들
        high_conditions = [
            category == ErrorCategory.TRADING,
            '429' in error_message,  # Rate limit
            'authentication' in error_message,
            self.system_health.consecutive_errors > 3
        ]
        
        if any(high_conditions):
            return ErrorSeverity.HIGH
        
        # 중간 심각도 조건들
        medium_conditions = [
            category in [ErrorCategory.API, ErrorCategory.DATABASE],
            'timeout' in error_message,
            self.system_health.consecutive_errors > 1
        ]
        
        if any(medium_conditions):
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.LOW
    
    def _generate_error_id(self) -> str:
        """고유 에러 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = f"{random.randint(1000, 9999)}"
        return f"ERR_{timestamp}_{random_suffix}"
    
    def _attempt_recovery(self, error_event: ErrorEvent) -> bool:
        """자동 복구 시도"""
        try:
            # 카테고리별 복구 전략 선택
            strategy_name = self._select_recovery_strategy(error_event.category)
            
            if strategy_name not in self.recovery_strategies:
                self.logger.warning(f"복구 전략 없음: {strategy_name}")
                return False
            
            strategy = self.recovery_strategies[strategy_name]
            
            self.logger.info(f"🔄 복구 시도: {strategy.description}")
            
            # 백오프 전략으로 복구 시도
            success = self._execute_recovery_with_backoff(strategy, error_event)
            
            # 복구 전략 통계 업데이트
            self._update_recovery_stats(strategy, success)
            
            if success:
                self.logger.info(f"✅ 복구 성공: {strategy.description}")
                
                # 성공 알림
                if self.telegram_bot:
                    try:
                        message = f"🔄 자동 복구 성공\n전략: {strategy.description}\n시간: {datetime.now().strftime('%H:%M:%S')}"
                        self.telegram_bot.send_message(message)
                    except:
                        pass
                
                # 연속 에러 카운터 리셋
                self.system_health.consecutive_errors = 0
                
                try:
                    log_feature_add("utils/enhanced_error_handler.py", f"자동 복구 성공: {strategy_name}")
                except:
                    pass
            else:
                self.logger.warning(f"❌ 복구 실패: {strategy.description}")
                
                try:
                    log_bug_fix("utils/enhanced_error_handler.py", f"복구 실패: {strategy_name}")
                except:
                    pass
            
            return success
            
        except Exception as e:
            self.logger.error(f"복구 시도 중 오류: {e}")
            return False
    
    def _select_recovery_strategy(self, category: ErrorCategory) -> str:
        """카테고리별 복구 전략 선택"""
        strategy_map = {
            ErrorCategory.NETWORK: "network_reconnect",
            ErrorCategory.API: "api_reconnect", 
            ErrorCategory.DATA_COLLECTION: "data_collection_recovery",
            ErrorCategory.DATABASE: "database_recovery",
            ErrorCategory.SYSTEM: "system_cleanup",
            ErrorCategory.TRADING: "api_reconnect",  # 거래 에러는 API 재연결로 시도
            ErrorCategory.UNKNOWN: "network_reconnect"  # 기본값
        }
        
        return strategy_map.get(category, "network_reconnect")
    
    def _execute_recovery_with_backoff(self, strategy: RecoveryStrategy, 
                                     error_event: ErrorEvent) -> bool:
        """백오프 전략으로 복구 실행"""
        for attempt in range(strategy.max_attempts):
            try:
                # 지연 시간 계산 (지수 백오프)
                delay = strategy.delay_seconds * (strategy.backoff_multiplier ** attempt)
                
                if attempt > 0:
                    self.logger.info(f"복구 재시도 {attempt + 1}/{strategy.max_attempts} (대기: {delay:.1f}초)")
                    time.sleep(delay)
                
                # 복구 함수 실행
                success = strategy.recovery_function(error_event, attempt + 1)
                
                if success:
                    error_event.retry_count = attempt + 1
                    strategy.last_used = datetime.now()
                    return True
                
            except Exception as e:
                self.logger.error(f"복구 시도 {attempt + 1} 실패: {e}")
                continue
        
        error_event.retry_count = strategy.max_attempts
        return False
    
    # 복구 함수들
    def _recover_network_connection(self, error_event: ErrorEvent, attempt: int) -> bool:
        """네트워크 연결 복구"""
        try:
            # 간단한 연결 테스트
            test_urls = [
                "https://api.upbit.com/v1/market/all",
                "https://api.bithumb.com/public/ticker/all",
                "https://www.google.com"
            ]
            
            for url in test_urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        self.logger.info(f"네트워크 연결 확인됨: {url}")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"네트워크 복구 시도 실패: {e}")
            return False
    
    def _recover_api_connection(self, error_event: ErrorEvent, attempt: int) -> bool:
        """API 연결 복구"""
        try:
            # 업비트 API 연결 테스트
            test_response = requests.get(
                "https://api.upbit.com/v1/market/all",
                timeout=10
            )
            
            if test_response.status_code == 200:
                self.logger.info("업비트 API 연결 복구됨")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"API 복구 시도 실패: {e}")
            return False
    
    def _recover_data_collection(self, error_event: ErrorEvent, attempt: int) -> bool:
        """데이터 수집 복구 (대체 소스 사용)"""
        try:
            # 여러 데이터 소스 시도
            alternative_sources = [
                "https://api.upbit.com/v1/candles/minutes/1?market=KRW-BTC&count=1",
                "https://api.bithumb.com/public/ticker/BTC_KRW",
            ]
            
            for source in alternative_sources:
                try:
                    response = requests.get(source, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data:  # 데이터가 있으면 성공
                            self.logger.info(f"대체 데이터 소스 사용: {source}")
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"데이터 수집 복구 실패: {e}")
            return False
    
    def _recover_database_connection(self, error_event: ErrorEvent, attempt: int) -> bool:
        """데이터베이스 연결 복구"""
        try:
            # 데이터베이스 파일 존재 확인
            db_path = Path("data/coinbot.db")
            
            if not db_path.exists():
                # 데이터베이스 파일이 없으면 생성
                db_path.parent.mkdir(parents=True, exist_ok=True)
                self.logger.info("데이터베이스 파일 생성 시도")
            
            # 간단한 연결 테스트
            import sqlite3
            try:
                conn = sqlite3.connect(str(db_path), timeout=10)
                conn.execute("SELECT 1")
                conn.close()
                self.logger.info("데이터베이스 연결 복구됨")
                return True
            except sqlite3.Error as e:
                self.logger.error(f"데이터베이스 연결 실패: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"데이터베이스 복구 실패: {e}")
            return False
    
    def _perform_system_cleanup(self, error_event: ErrorEvent, attempt: int) -> bool:
        """시스템 리소스 정리"""
        try:
            import gc
            import psutil
            
            # 가비지 컬렉션 실행
            gc.collect()
            
            # 메모리 사용량 체크
            memory_percent = psutil.virtual_memory().percent
            
            if memory_percent > 85:
                self.logger.warning(f"높은 메모리 사용률: {memory_percent}%")
                # 추가 정리 작업 (필요시)
                
            # 임시 파일 정리
            temp_dir = Path("data/temp")
            if temp_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    temp_dir.mkdir(exist_ok=True)
                    self.logger.info("임시 파일 정리 완료")
                except:
                    pass
            
            self.logger.info("시스템 정리 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"시스템 정리 실패: {e}")
            return False
    
    def _update_recovery_stats(self, strategy: RecoveryStrategy, success: bool):
        """복구 전략 통계 업데이트"""
        try:
            # 성공률 계산 (간단한 이동 평균)
            if hasattr(strategy, 'total_attempts'):
                strategy.total_attempts += 1
            else:
                strategy.total_attempts = 1
            
            if hasattr(strategy, 'successful_attempts'):
                if success:
                    strategy.successful_attempts += 1
            else:
                strategy.successful_attempts = 1 if success else 0
            
            # 성공률 업데이트
            strategy.success_rate = (strategy.successful_attempts / strategy.total_attempts) * 100
            
            # 전체 복구 성공률 업데이트
            total_attempts = sum(getattr(s, 'total_attempts', 0) for s in self.recovery_strategies.values())
            total_successes = sum(getattr(s, 'successful_attempts', 0) for s in self.recovery_strategies.values())
            
            if total_attempts > 0:
                self.system_health.recovery_success_rate = (total_successes / total_attempts) * 100
            
        except Exception as e:
            self.logger.error(f"복구 통계 업데이트 실패: {e}")

    def _cleanup_old_errors(self):
        """오래된 에러 이벤트 정리"""
        max_errors = self.config["max_error_history"]
        if len(self.error_history) > max_errors:
            # 가장 오래된 에러들 제거
            self.error_history = self.error_history[-max_errors:]
            self.logger.debug(f"에러 히스토리 정리: {max_errors}개 유지")

    def _update_error_stats(self, error_event: ErrorEvent):
        """에러 통계 업데이트"""
        try:
            self.error_stats['total_errors'] += 1
            
            if error_event.recovery_successful:
                self.error_stats['recovered_errors'] += 1
            
            if error_event.severity == ErrorSeverity.CRITICAL:
                self.error_stats['critical_errors'] += 1
            
            # 24시간 내 에러 추적
            now = datetime.now()
            cutoff_time = now - timedelta(hours=24)
            
            # 오래된 에러 제거
            self.error_stats['last_24h_errors'] = [
                err_time for err_time in self.error_stats['last_24h_errors']
                if datetime.fromisoformat(err_time) > cutoff_time
            ]
            
            # 새 에러 추가
            self.error_stats['last_24h_errors'].append(error_event.timestamp)
            
            # 가장 흔한 에러 추적
            error_key = f"{error_event.category.value}_{type(error_event.message).__name__}"
            self.error_stats['most_common_errors'][error_key] = \
                self.error_stats['most_common_errors'].get(error_key, 0) + 1
            
            # 복구 성공률 계산
            if self.error_stats['total_errors'] > 0:
                self.error_stats['recovery_success_rate'] = \
                    (self.error_stats['recovered_errors'] / self.error_stats['total_errors']) * 100
                    
        except Exception as e:
            self.logger.error(f"에러 통계 업데이트 실패: {e}")
    def _log_error_event(self, error_event: ErrorEvent):
        """에러 이벤트 로깅"""
        log_level_map = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        
        log_level = log_level_map[error_event.severity]
        
        log_message = (
            f"[{error_event.error_id}] {error_event.category.value.upper()} "
            f"- {error_event.message}"
        )
        
        if error_event.context:
            log_message += f" | Context: {error_event.context}"
        
        self.logger.log(log_level, log_message)
        
        # 트레이스백은 디버그 레벨에서만
        if error_event.traceback_info and error_event.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.debug(f"[{error_event.error_id}] Traceback:\n{error_event.traceback_info}")

    def _send_alert_if_needed(self, error_event: ErrorEvent):
        """필요시 알림 발송"""
        try:
            # 알림 발송 조건 체크
            should_alert = self._should_send_alert(error_event)
            
            if not should_alert:
                return
            
            # 알림 메시지 생성
            alert_message = self._generate_alert_message(error_event)
            
            # 텔레그램 알림
            if self.telegram_bot:
                try:
                    self.telegram_bot.send_message(alert_message)
                    self.logger.info(f"텔레그램 알림 발송: {error_event.error_id}")
                except Exception as e:
                    self.logger.error(f"텔레그램 알림 발송 실패: {e}")
            
            # 알림 쿨다운 설정
            alert_key = f"{error_event.category.value}_{error_event.severity.value}"
            self.alert_cooldowns[alert_key] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"알림 발송 중 오류: {e}")

    def _should_send_alert(self, error_event: ErrorEvent) -> bool:
        """알림 발송 여부 판단"""
        # 심각도별 알림 조건
        if error_event.severity == ErrorSeverity.CRITICAL:
            return True  # 치명적 에러는 항상 알림
        
        if error_event.severity == ErrorSeverity.HIGH:
            # 높은 심각도는 5분 쿨다운
            return self._check_alert_cooldown(error_event, minutes=5)
        
        if error_event.severity == ErrorSeverity.MEDIUM:
            # 중간 심각도는 15분 쿨다운
            return self._check_alert_cooldown(error_event, minutes=15)
        
        # 낮은 심각도는 알림 안함
        return False

    def _check_alert_cooldown(self, error_event: ErrorEvent, minutes: int) -> bool:
        """알림 쿨다운 체크"""
        alert_key = f"{error_event.category.value}_{error_event.severity.value}"
        
        if alert_key not in self.alert_cooldowns:
            return True
        
        last_alert_time = self.alert_cooldowns[alert_key]
        cooldown_period = timedelta(minutes=minutes)
        
        return (datetime.now() - last_alert_time) > cooldown_period

    def _generate_alert_message(self, error_event: ErrorEvent) -> str:
        """알림 메시지 생성"""
        severity_emoji = {
            ErrorSeverity.LOW: "ℹ️",
            ErrorSeverity.MEDIUM: "⚠️", 
            ErrorSeverity.HIGH: "🚨",
            ErrorSeverity.CRITICAL: "🆘"
        }
        
        emoji = severity_emoji[error_event.severity]
        
        message = f"{emoji} CoinBot 에러 알림\n\n"
        message += f"🆔 ID: {error_event.error_id}\n"
        message += f"📂 카테고리: {error_event.category.value.upper()}\n"
        message += f"⚡ 심각도: {error_event.severity.value.upper()}\n"
        message += f"📝 메시지: {error_event.message}\n"
        message += f"🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if error_event.recovery_attempted:
            recovery_status = "성공" if error_event.recovery_successful else "실패"
            message += f"🔄 복구 시도: {recovery_status}\n"
        
        if error_event.context:
            message += f"📋 컨텍스트: {error_event.context}\n"
        
        # 시스템 건강도 추가
        message += f"\n💊 시스템 건강도: {self.system_health.overall_score:.1f}%"
        
        if self.emergency_mode:
            message += "\n🚨 긴급 모드 활성화됨!"
        
        return message

    def _update_system_health(self):
        """시스템 건강도 업데이트"""
        try:
            # 기본 점수
            health_score = 100.0
            
            # 최근 에러율 기반 점수 차감
            recent_errors = len([
                err for err in self.error_history 
                if datetime.fromisoformat(err.timestamp) > (datetime.now() - timedelta(hours=1))
            ])
            
            if recent_errors > 0:
                error_penalty = min(recent_errors * 5, 30)  # 최대 30점 차감
                health_score -= error_penalty
                self.system_health.error_rate_score = max(0, 100 - error_penalty)
            
            # 연속 에러에 대한 추가 차감
            if self.system_health.consecutive_errors > 0:
                consecutive_penalty = min(self.system_health.consecutive_errors * 10, 40)
                health_score -= consecutive_penalty
            
            # 복구 성공률 기반 보정
            if self.system_health.recovery_success_rate > 80:
                health_score += 5  # 복구율이 높으면 보너스
            elif self.system_health.recovery_success_rate < 50:
                health_score -= 10  # 복구율이 낮으면 추가 차감
            
            # 개별 시스템 건강도 업데이트
            self._update_individual_health_scores()
            
            # 전체 건강도 계산
            individual_scores = [
                self.system_health.api_connection_score,
                self.system_health.data_collection_score,
                self.system_health.trading_system_score,
                self.system_health.network_stability_score,
                self.system_health.error_rate_score
            ]
            
            self.system_health.overall_score = max(0, min(100, sum(individual_scores) / len(individual_scores)))
            
        except Exception as e:
            self.logger.error(f"시스템 건강도 업데이트 실패: {e}")

    def _update_individual_health_scores(self):
        """개별 시스템 건강도 업데이트"""
        try:
            # API 연결 상태 체크
            try:
                response = requests.get("https://api.upbit.com/v1/market/all", timeout=5)
                self.system_health.api_connection_score = 100.0 if response.status_code == 200 else 50.0
            except:
                self.system_health.api_connection_score = 0.0
            
            # 네트워크 안정성 체크
            try:
                response = requests.get("https://www.google.com", timeout=5)
                self.system_health.network_stability_score = 100.0 if response.status_code == 200 else 30.0
            except:
                self.system_health.network_stability_score = 0.0
            
            # 데이터 수집 시스템 점수 (최근 데이터 수집 에러 기반)
            data_errors = len([
                err for err in self.error_history[-20:]  # 최근 20개 에러 중
                if err.category == ErrorCategory.DATA_COLLECTION
            ])
            self.system_health.data_collection_score = max(0, 100 - (data_errors * 15))
            
            # 거래 시스템 점수 (최근 거래 에러 기반)
            trading_errors = len([
                err for err in self.error_history[-20:]
                if err.category == ErrorCategory.TRADING
            ])
            self.system_health.trading_system_score = max(0, 100 - (trading_errors * 20))
            
        except Exception as e:
            self.logger.error(f"개별 건강도 업데이트 실패: {e}")

    def _update_error_statistics(self):
        """에러 통계 업데이트"""
        try:
            # 24시간 내 에러 개수 업데이트
            now = datetime.now()
            cutoff_time = now - timedelta(hours=24)
            
            recent_errors = [
                err for err in self.error_history
                if datetime.fromisoformat(err.timestamp) > cutoff_time
            ]
            
            # 시간대별 에러 분포 계산
            hourly_distribution = {}
            for err in recent_errors:
                hour = datetime.fromisoformat(err.timestamp).hour
                hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
            
            # 카테고리별 에러 분포
            category_distribution = {}
            for err in recent_errors:
                cat = err.category.value
                category_distribution[cat] = category_distribution.get(cat, 0) + 1
            
            # 통계 저장
            self.error_stats.update({
                'last_24h_count': len(recent_errors),
                'hourly_distribution': hourly_distribution,
                'category_distribution': category_distribution,
                'last_update': now.isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"에러 통계 업데이트 실패: {e}")

    def _check_emergency_conditions(self):
        """긴급 상황 체크"""
        try:
            emergency_triggers = [
                # 연속 치명적 에러
                self.system_health.consecutive_errors >= self.config["emergency_mode_threshold"],
                
                # 전체 건강도 매우 낮음
                self.system_health.overall_score < 20,
                
                # 최근 1시간 내 과도한 에러
                len([
                    err for err in self.error_history
                    if datetime.fromisoformat(err.timestamp) > (datetime.now() - timedelta(hours=1))
                       and err.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
                ]) > self.config["alert_thresholds"]["error_rate_per_hour"],
                
                # API 연결 완전 실패
                self.system_health.api_connection_score == 0,
            ]
            
            should_activate_emergency = any(emergency_triggers)
            
            if should_activate_emergency and not self.emergency_mode:
                self._activate_emergency_mode()
            elif not should_activate_emergency and self.emergency_mode:
                self._deactivate_emergency_mode()
                
        except Exception as e:
            self.logger.error(f"긴급 상황 체크 실패: {e}")

    def _activate_emergency_mode(self):
        """긴급 모드 활성화"""
        try:
            self.emergency_mode = True
            self.safe_mode = True
            
            self.logger.critical("🚨 긴급 모드 활성화!")
            
            # 긴급 알림 발송
            if self.telegram_bot:
                try:
                    emergency_message = (
                        "🆘 CoinBot 긴급 모드 활성화!\n\n"
                        f"🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"💊 시스템 건강도: {self.system_health.overall_score:.1f}%\n"
                        f"🔴 연속 에러: {self.system_health.consecutive_errors}회\n\n"
                        "모든 거래가 중단되었습니다.\n"
                        "시스템을 점검해주세요."
                    )
                    self.telegram_bot.send_message(emergency_message)
                except:
                    pass
            
            try:
                log_feature_add("utils/enhanced_error_handler.py", "긴급 모드 활성화")
            except:
                pass
                
        except Exception as e:
            self.logger.error(f"긴급 모드 활성화 실패: {e}")

    def _deactivate_emergency_mode(self):
        """긴급 모드 비활성화"""
        try:
            self.emergency_mode = False
            self.safe_mode = False
            
            self.logger.info("✅ 긴급 모드 비활성화 - 시스템 정상화")
            
            # 정상화 알림
            if self.telegram_bot:
                try:
                    recovery_message = (
                        "✅ CoinBot 시스템 정상화\n\n"
                        f"🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"💊 시스템 건강도: {self.system_health.overall_score:.1f}%\n\n"
                        "긴급 모드가 해제되었습니다.\n"
                        "정상 운영을 재개합니다."
                    )
                    self.telegram_bot.send_message(recovery_message)
                except:
                    pass
            
            try:
                log_feature_add("utils/enhanced_error_handler.py", "긴급 모드 해제 - 시스템 정상화")
            except:
                pass
                
        except Exception as e:
            self.logger.error(f"긴급 모드 비활성화 실패: {e}")

    def _check_emergency_mode_trigger(self):
        """치명적 에러 발생 시 긴급 모드 트리거 체크"""
        self.system_health.consecutive_errors += 1
        self.system_health.last_critical_error = datetime.now()
        
        if self.system_health.consecutive_errors >= self.config["emergency_mode_threshold"]:
            self._activate_emergency_mode()

    def _attempt_auto_recovery(self):
        """자동 복구 시도 (백그라운드)"""
        try:
            if self.emergency_mode:
                return  # 긴급 모드에서는 자동 복구 안함
            
            # 최근 실패한 에러들 중 복구 가능한 것들 찾기
            recent_failures = [
                err for err in self.error_history[-10:]  # 최근 10개
                if not err.recovery_successful 
                and err.severity in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]
                and err.retry_count < err.max_retries
            ]
            
            for error_event in recent_failures:
                if datetime.fromisoformat(error_event.timestamp) > (datetime.now() - timedelta(minutes=5)):
                    # 5분 이내 에러만 재시도
                    self.logger.info(f"백그라운드 복구 재시도: {error_event.error_id}")
                    success = self._attempt_recovery(error_event)
                    
                    if success:
                        self.logger.info(f"백그라운드 복구 성공: {error_event.error_id}")
                        break  # 하나씩만 처리
                        
        except Exception as e:
            self.logger.error(f"자동 복구 시도 실패: {e}")

    def _update_health_after_error(self, error_event: ErrorEvent):
        """에러 발생 후 건강도 업데이트"""
        try:
            # 심각도별 건강도 차감
            severity_penalties = {
                ErrorSeverity.LOW: 1,
                ErrorSeverity.MEDIUM: 3,
                ErrorSeverity.HIGH: 8,
                ErrorSeverity.CRITICAL: 15
            }
            
            penalty = severity_penalties[error_event.severity]
            self.system_health.overall_score = max(0, self.system_health.overall_score - penalty)
            
            # 복구 성공 시 건강도 일부 회복
            if error_event.recovery_successful:
                recovery_bonus = penalty * 0.5  # 차감된 점수의 50% 회복
                self.system_health.overall_score = min(100, self.system_health.overall_score + recovery_bonus)
                
        except Exception as e:
            self.logger.error(f"건강도 업데이트 실패: {e}")

    # 공개 API 메서드들
    def get_system_health(self) -> SystemHealth:
        """현재 시스템 건강도 반환"""
        return self.system_health

    def get_error_statistics(self) -> Dict[str, Any]:
        """에러 통계 반환"""
        return self.error_stats.copy()

    def get_recent_errors(self, hours: int = 24) -> List[ErrorEvent]:
        """최근 에러 목록 반환"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            err for err in self.error_history
            if datetime.fromisoformat(err.timestamp) > cutoff_time
        ]

    def is_emergency_mode(self) -> bool:
        """긴급 모드 상태 반환"""
        return self.emergency_mode

    def is_safe_mode(self) -> bool:
        """안전 모드 상태 반환"""
        return self.safe_mode

    def force_recovery_attempt(self, error_id: str) -> bool:
        """특정 에러에 대한 강제 복구 시도"""
        try:
            error_event = None
            for err in self.error_history:
                if err.error_id == error_id:
                    error_event = err
                    break
            
            if not error_event:
                self.logger.warning(f"에러 ID를 찾을 수 없음: {error_id}")
                return False
            
            success = self._attempt_recovery(error_event)
            self.logger.info(f"강제 복구 시도 결과: {success}")
            return success
            
        except Exception as e:
            self.logger.error(f"강제 복구 시도 실패: {e}")
            return False
    def reset_emergency_mode(self):
        """긴급 모드 강제 해제"""
        try:
            self.emergency_mode = False
            self.safe_mode = False
            self.system_health.consecutive_errors = 0
            
            self.logger.info("⚡ 긴급 모드 강제 해제됨")
            
            try:
                log_feature_add("utils/enhanced_error_handler.py", "긴급 모드 수동 해제")
            except:
                pass
            
            if self.telegram_bot:
                try:
                    message = "⚡ 긴급 모드 수동 해제\n정상 운영을 재개합니다."
                    self.telegram_bot.send_message(message)
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"긴급 모드 해제 실패: {e}")

    def generate_health_report(self) -> Dict[str, Any]:
        """시스템 건강도 리포트 생성"""
        try:
            recent_errors = self.get_recent_errors(24)
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'system_health': {
                    'overall_score': self.system_health.overall_score,
                    'api_connection': self.system_health.api_connection_score,
                    'data_collection': self.system_health.data_collection_score,
                    'trading_system': self.system_health.trading_system_score,
                    'network_stability': self.system_health.network_stability_score,
                    'error_rate': self.system_health.error_rate_score
                },
                'error_statistics': self.error_stats.copy(),
                'recent_errors': {
                    'total_24h': len(recent_errors),
                    'critical': len([e for e in recent_errors if e.severity == ErrorSeverity.CRITICAL]),
                    'high': len([e for e in recent_errors if e.severity == ErrorSeverity.HIGH]),
                    'medium': len([e for e in recent_errors if e.severity == ErrorSeverity.MEDIUM]),
                    'low': len([e for e in recent_errors if e.severity == ErrorSeverity.LOW])
                },
                'recovery_strategies': {
                    name: {
                        'success_rate': strategy.success_rate,
                        'last_used': strategy.last_used.isoformat() if strategy.last_used else None,
                        'total_attempts': getattr(strategy, 'total_attempts', 0),
                        'successful_attempts': getattr(strategy, 'successful_attempts', 0)
                    }
                    for name, strategy in self.recovery_strategies.items()
                },
                'system_status': {
                    'emergency_mode': self.emergency_mode,
                    'safe_mode': self.safe_mode,
                    'consecutive_errors': self.system_health.consecutive_errors,
                    'last_critical_error': self.system_health.last_critical_error.isoformat() 
                                         if self.system_health.last_critical_error else None
                }
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"건강도 리포트 생성 실패: {e}")
            return {"error": str(e)}

    def export_error_log(self, hours: int = 24, format: str = "json") -> str:
        """에러 로그 내보내기"""
        try:
            recent_errors = self.get_recent_errors(hours)
            
            if format.lower() == "json":
                return json.dumps([
                    {
                        'timestamp': err.timestamp,
                        'error_id': err.error_id,
                        'category': err.category.value,
                        'severity': err.severity.value,
                        'message': err.message,
                        'recovery_attempted': err.recovery_attempted,
                        'recovery_successful': err.recovery_successful,
                        'retry_count': err.retry_count
                    }
                    for err in recent_errors
                ], indent=2, ensure_ascii=False)
            
            elif format.lower() == "csv":
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # 헤더 작성
                writer.writerow([
                    'Timestamp', 'Error ID', 'Category', 'Severity', 'Message',
                    'Recovery Attempted', 'Recovery Successful', 'Retry Count'
                ])
                
                # 데이터 작성
                for err in recent_errors:
                    writer.writerow([
                        err.timestamp, err.error_id, err.category.value, err.severity.value,
                        err.message, err.recovery_attempted, err.recovery_successful, err.retry_count
                    ])
                
                return output.getvalue()
            
            else:
                raise ValueError(f"지원하지 않는 형식: {format}")
                
        except Exception as e:
            self.logger.error(f"에러 로그 내보내기 실패: {e}")
            return f"내보내기 실패: {str(e)}"

    def stop(self):
        """에러 핸들러 중지"""
        try:
            self.monitoring_active = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            self.logger.info("🛡️ 에러 핸들링 시스템 중지됨")
            
            try:
                log_feature_add("utils/enhanced_error_handler.py", "에러 핸들링 시스템 정상 종료")
            except:
                pass
                
        except Exception as e:
            self.logger.error(f"에러 핸들러 중지 실패: {e}")


# 전역 에러 핸들러 인스턴스
_global_error_handler: Optional[EnhancedErrorHandler] = None

def get_error_handler() -> EnhancedErrorHandler:
    """전역 에러 핸들러 인스턴스 반환"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = EnhancedErrorHandler()
    return _global_error_handler

def init_error_handler(config_file: Optional[str] = None) -> EnhancedErrorHandler:
    """에러 핸들러 초기화"""
    global _global_error_handler
    _global_error_handler = EnhancedErrorHandler(config_file)
    return _global_error_handler

# 데코레이터 함수들
def handle_errors(category: Optional[ErrorCategory] = None, 
                 retry: bool = True, 
                 max_retries: int = 3,
                 delay: float = 1.0):
    """에러 처리 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = get_error_handler()
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    context = {
                        'function': func.__name__,
                        'attempt': attempt + 1,
                        'max_retries': max_retries,
                        'args': str(args)[:100],  # 처음 100자만
                        'kwargs': str(kwargs)[:100]
                    }
                    
                    # 에러 처리
                    error_event = error_handler.handle_error(e, context, category)
                    
                    # 마지막 시도가 아니면 재시도
                    if retry and attempt < max_retries:
                        time.sleep(delay * (attempt + 1))  # 지수 백오프
                        continue
                    else:
                        # 마지막 시도 실패 시 에러 재발생
                        raise e
            
        return wrapper
    return decorator

def handle_async_errors(category: Optional[ErrorCategory] = None,
                       retry: bool = True,
                       max_retries: int = 3,
                       delay: float = 1.0):
    """비동기 함수용 에러 처리 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            error_handler = get_error_handler()
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    context = {
                        'function': func.__name__,
                        'attempt': attempt + 1,
                        'max_retries': max_retries,
                        'args': str(args)[:100],
                        'kwargs': str(kwargs)[:100]
                    }
                    
                    # 에러 처리
                    error_event = error_handler.handle_error(e, context, category)
                    
                    # 마지막 시도가 아니면 재시도
                    if retry and attempt < max_retries:
                        await asyncio.sleep(delay * (attempt + 1))
                        continue
                    else:
                        raise e
                        
        return wrapper
    return decorator

def safe_execute(func: Callable, 
                default_return: Any = None,
                category: Optional[ErrorCategory] = None,
                log_errors: bool = True) -> Any:
    """안전한 함수 실행"""
    try:
        return func()
    except Exception as e:
        if log_errors:
            error_handler = get_error_handler()
            error_handler.handle_error(e, {
                'function': func.__name__ if hasattr(func, '__name__') else str(func),
                'safe_execute': True
            }, category)
        
        return default_return

async def safe_execute_async(func: Callable,
                            default_return: Any = None,
                            category: Optional[ErrorCategory] = None,
                            log_errors: bool = True) -> Any:
    """안전한 비동기 함수 실행"""
    try:
        return await func()
    except Exception as e:
        if log_errors:
            error_handler = get_error_handler()
            error_handler.handle_error(e, {
                'function': func.__name__ if hasattr(func, '__name__') else str(func),
                'safe_execute_async': True
            }, category)
        
        return default_return

# 특화된 데코레이터들
def handle_network_errors(retry: bool = True, max_retries: int = 5):
    """네트워크 에러 전용 데코레이터"""
    return handle_errors(
        category=ErrorCategory.NETWORK,
        retry=retry,
        max_retries=max_retries,
        delay=2.0
    )

def handle_api_errors(retry: bool = True, max_retries: int = 4):
    """API 에러 전용 데코레이터"""
    return handle_errors(
        category=ErrorCategory.API,
        retry=retry,
        max_retries=max_retries,
        delay=3.0
    )

def handle_data_collection_errors(retry: bool = True, max_retries: int = 3):
    """데이터 수집 에러 전용 데코레이터"""
    return handle_errors(
        category=ErrorCategory.DATA_COLLECTION,
        retry=retry,
        max_retries=max_retries,
        delay=1.0
    )

def handle_trading_errors(retry: bool = False, max_retries: int = 1):
    """거래 에러 전용 데코레이터 (재시도 안함)"""
    return handle_errors(
        category=ErrorCategory.TRADING,
        retry=retry,
        max_retries=max_retries,
        delay=0.0
    )

# 컨텍스트 매니저
class ErrorHandlerContext:
    """에러 핸들링 컨텍스트 매니저"""
    
    def __init__(self, category: Optional[ErrorCategory] = None, 
                 context_info: Optional[Dict] = None):
        self.category = category
        self.context_info = context_info or {}
        self.error_handler = get_error_handler()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error_handler.handle_error(exc_val, self.context_info, self.category)
        return False  # 에러를 다시 발생시킴

# 유틸리티 함수들
def log_manual_error(message: str, 
                    category: ErrorCategory = ErrorCategory.UNKNOWN,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict] = None):
    """수동 에러 로깅"""
    error_handler = get_error_handler()
    
    # 가짜 예외 생성
    manual_error = Exception(message)
    
    # 컨텍스트에 수동 로그임을 표시
    if context is None:
        context = {}
    context['manual_log'] = True
    
    error_handler.handle_error(manual_error, context, category)

def check_system_health() -> Dict[str, Any]:
    """시스템 건강도 간단 체크"""
    error_handler = get_error_handler()
    health = error_handler.get_system_health()
    
    return {
        'overall_score': health.overall_score,
        'status': 'healthy' if health.overall_score > 80 else 
                 'warning' if health.overall_score > 60 else 'critical',
        'emergency_mode': error_handler.is_emergency_mode(),
        'consecutive_errors': health.consecutive_errors
    }

def create_health_report() -> str:
    """건강도 리포트 생성 (문자열 형태)"""
    error_handler = get_error_handler()
    report_data = error_handler.generate_health_report()
    
    return json.dumps(report_data, indent=2, ensure_ascii=False)

# 메인 함수 (테스트용)
def main():
    """테스트 및 데모용 메인 함수"""
    print("🛡️ CoinBot 고도화 에러 핸들링 시스템 테스트")
    print("=" * 60)
    
    # 에러 핸들러 초기화
    error_handler = init_error_handler()
    
    # 테스트 에러들
    test_errors = [
        (Exception("네트워크 연결 실패"), ErrorCategory.NETWORK),
        (Exception("API 429 Too Many Requests"), ErrorCategory.API),
        (Exception("데이터 파싱 오류"), ErrorCategory.DATA_COLLECTION),
        (Exception("거래 실행 실패"), ErrorCategory.TRADING),
    ]
    
    print("\n📋 테스트 에러 처리 중...")
    for i, (error, category) in enumerate(test_errors, 1):
        print(f"  {i}. {category.value}: {error}")
        error_handler.handle_error(error, {"test": True}, category)
    
    print(f"\n📊 시스템 건강도: {error_handler.get_system_health().overall_score:.1f}%")
    print(f"📈 총 에러 수: {error_handler.get_error_statistics()['total_errors']}")
    print(f"🔄 복구 성공률: {error_handler.get_system_health().recovery_success_rate:.1f}%")
    
    # 데코레이터 테스트
    @handle_network_errors(max_retries=2)
    def test_network_function():
        print("    네트워크 함수 실행 중...")
        if random.random() < 0.7:  # 70% 확률로 실패
            raise Exception("네트워크 타임아웃")
        return "성공"
    
    print("\n🧪 데코레이터 테스트:")
    try:
        result = test_network_function()
        print(f"    결과: {result}")
    except Exception as e:
        print(f"    최종 실패: {e}")
    
    print("\n✅ 테스트 완료!")
    
    # 정리
    error_handler.stop()

if __name__ == "__main__":
    main()                        
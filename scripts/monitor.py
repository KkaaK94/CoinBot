#!/usr/bin/env python3
"""
🔍 CoinBot 실시간 모니터링 시스템 (고도화 버전)
- 봇 프로세스 상태 실시간 모니터링
- 시스템 리소스 모니터링 및 알림
- 성능 지표 추적 및 분석
- 자동 재시작 및 복구 시스템
- 웹 API 및 대시보드 제공
- 텔레그램 알림 통합
"""

import os
import sys
import time
import json
import psutil
import argparse
import threading
import subprocess
import requests
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler

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

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 선택적 모듈 import
try:
    from utils.telegram_bot import TelegramBot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    TelegramBot = None

@dataclass
class SystemMetrics:
    """시스템 메트릭 데이터 클래스"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    disk_total_gb: float
    network_sent_mb: float
    network_recv_mb: float
    load_average: List[float] = field(default_factory=list)
    process_count: int = 0
    temperature: Optional[float] = None

@dataclass
class BotStatus:
    """봇 상태 데이터 클래스"""
    is_running: bool
    pid: Optional[int]
    uptime_seconds: int
    last_restart: Optional[str]
    restart_count: int
    cpu_percent: float
    memory_mb: float
    status_message: str
    last_activity: Optional[str] = None
    error_count: int = 0
    last_error: Optional[str] = None

@dataclass
class AlertConfig:
    """알림 설정 데이터 클래스"""
    enabled: bool = True
    telegram_enabled: bool = True
    email_enabled: bool = False
    cpu_threshold: float = 85.0
    memory_threshold: float = 85.0
    disk_threshold: float = 90.0
    bot_down_alert: bool = True
    error_count_threshold: int = 5
    alert_cooldown_minutes: int = 30

@dataclass
class PerformanceMetrics:
    """성과 지표 데이터 클래스"""
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    win_rate: float = 0.0
    total_profit_loss: float = 0.0
    daily_pnl: float = 0.0
    last_trade_time: Optional[str] = None
    average_trade_duration: float = 0.0
    current_positions: int = 0

class EnhancedBotMonitor:
    """고도화된 CoinBot 모니터링 시스템"""
    
    def __init__(self, config_file: str = None):
        """모니터 초기화"""
        self.config = self._load_config(config_file)
        self.bot_process = None
        self.start_time = datetime.now()
        self.restart_count = 0
        self.last_restart = None
        self.metrics_history = []
        self.alerts_sent = {}  # 알림 쿨다운 관리
        self.running = True
        self.error_count = 0
        self.last_error = None
        
        # 로거 설정
        self._setup_logging()
        
        # 자동 업데이트 시스템 로깅
        try:
            log_feature_add("scripts/monitor.py", "고도화된 모니터링 시스템 초기화 시작")
        except:
            pass
        
        # Flask 앱 초기화
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_routes()
        
        # 알림 시스템 초기화
        self._init_alert_system()
        
        # 초기 네트워크 통계
        try:
            self.initial_net_io = psutil.net_io_counters()
        except:
            self.initial_net_io = None
        
        # 성과 지표 초기화
        self.performance_metrics = PerformanceMetrics()
        
        # 종료 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("🚀 고도화된 CoinBot 모니터링 시스템 초기화 완료")
        
        try:
            log_feature_add("scripts/monitor.py", "모니터링 시스템 초기화 완료")
        except:
            pass
    def _load_config(self, config_file: str = None) -> Dict[str, Any]:
        """설정 파일 로드 및 기본값 설정"""
        default_config = {
            "bot_script": "main.py",
            "python_executable": "python",
            "check_interval": 15,  # 15초마다 확인 (더 빠른 반응)
            "restart_threshold": 5,  # 5회까지 재시작
            "cpu_alert_threshold": 85,
            "memory_alert_threshold": 85,
            "disk_alert_threshold": 90,
            "web_port": 8888,
            "auto_restart": True,
            "log_file": "data/logs/monitor.log",
            "metrics_retention_hours": 48,  # 48시간 보관
            "performance_check_enabled": True,
            "telegram_alerts": True,
            "email_alerts": False,
            "alert_cooldown_minutes": 30,
            "health_check_url": None,
            "backup_enabled": True,
            "backup_interval_hours": 6
        }
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    
                try:
                    log_config_change("scripts/monitor.py", "설정 파일 로드 완료", 
                                    {"config_file": config_file})
                except:
                    pass
                    
            except Exception as e:
                print(f"⚠️ 설정 파일 로드 실패: {e}")
                
        return default_config
    
    def _setup_logging(self):
        """로깅 시스템 설정"""
        self.logger = logging.getLogger('CoinBotMonitor')
        self.logger.setLevel(logging.INFO)
        
        # 로그 디렉토리 생성
        log_file = PROJECT_ROOT / self.config["log_file"]
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
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
        
        # 로테이팅 파일 핸들러
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _init_alert_system(self):
        """알림 시스템 초기화"""
        self.alert_config = AlertConfig()
        
        # 텔레그램 봇 초기화
        if TELEGRAM_AVAILABLE and self.config.get("telegram_alerts", True):
            try:
                self.telegram_bot = TelegramBot()
                self.logger.info("📱 텔레그램 알림 시스템 활성화됨")
            except Exception as e:
                self.logger.warning(f"텔레그램 봇 초기화 실패: {e}")
                self.telegram_bot = None
        else:
            self.telegram_bot = None
    
    def _signal_handler(self, signum, frame):
        """종료 시그널 핸들러"""
        self.logger.info(f"종료 시그널 수신: {signum}")
        self.running = False
    
    def get_bot_status(self) -> BotStatus:
        """봇 프로세스 상태 확인"""
        try:
            # main.py 프로세스 찾기
            bot_process = None
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline and 'python' in cmdline:
                        bot_process = proc
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if bot_process:
                # 프로세스 정보 수집
                cpu_percent = bot_process.cpu_percent()
                memory_mb = bot_process.memory_info().rss / (1024 * 1024)
                create_time = datetime.fromtimestamp(bot_process.create_time())
                uptime_seconds = int((datetime.now() - create_time).total_seconds())
                
                # 활동 상태 확인 (로그 파일 기반)
                last_activity = self._check_bot_activity()
                
                return BotStatus(
                    is_running=True,
                    pid=bot_process.pid,
                    uptime_seconds=uptime_seconds,
                    last_restart=self.last_restart,
                    restart_count=self.restart_count,
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    status_message="정상 실행 중",
                    last_activity=last_activity,
                    error_count=self.error_count,
                    last_error=self.last_error
                )
            else:
                return BotStatus(
                    is_running=False,
                    pid=None,
                    uptime_seconds=0,
                    last_restart=self.last_restart,
                    restart_count=self.restart_count,
                    cpu_percent=0.0,
                    memory_mb=0.0,
                    status_message="봇이 실행되지 않음",
                    error_count=self.error_count,
                    last_error=self.last_error
                )
                
        except Exception as e:
            self.logger.error(f"봇 상태 확인 실패: {e}")
            try:
                log_bug_fix("scripts/monitor.py", f"봇 상태 확인 에러 수정: {str(e)}")
            except:
                pass
                
            return BotStatus(
                is_running=False,
                pid=None,
                uptime_seconds=0,
                last_restart=self.last_restart,
                restart_count=self.restart_count,
                cpu_percent=0.0,
                memory_mb=0.0,
                status_message=f"상태 확인 오류: {str(e)}",
                error_count=self.error_count,
                last_error=str(e)
            )
    
    def _check_bot_activity(self) -> Optional[str]:
        """봇 활동 상태 확인 (로그 파일 기반)"""
        try:
            log_file = PROJECT_ROOT / "data/logs/coinbot.log"
            if not log_file.exists():
                return None
            
            # 최근 10분 내 로그 확인
            cutoff_time = datetime.now() - timedelta(minutes=10)
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in reversed(lines[-100:]):  # 최근 100줄만 확인
                if any(keyword in line for keyword in ['TRADE', 'BUY', 'SELL', 'ANALYSIS']):
                    try:
                        # 로그에서 시간 추출 시도
                        timestamp_str = line.split(' - ')[0]
                        log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        if log_time > cutoff_time:
                            return log_time.isoformat()
                    except:
                        continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"활동 상태 확인 실패: {e}")
            return None
    
    def get_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 정보
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # 디스크 정보
            disk = psutil.disk_usage(PROJECT_ROOT)
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # 네트워크 정보
            network_sent_mb = 0
            network_recv_mb = 0
            if self.initial_net_io:
                try:
                    current_net_io = psutil.net_io_counters()
                    network_sent_mb = (current_net_io.bytes_sent - self.initial_net_io.bytes_sent) / (1024 * 1024)
                    network_recv_mb = (current_net_io.bytes_recv - self.initial_net_io.bytes_recv) / (1024 * 1024)
                except:
                    pass
            
            # 시스템 부하 (Linux/Unix만)
            load_average = []
            try:
                load_average = list(os.getloadavg())
            except (OSError, AttributeError):
                load_average = [0.0, 0.0, 0.0]
            
            # 프로세스 수
            process_count = len(list(psutil.process_iter()))
            
            # 온도 정보 (가능한 경우)
            temperature = None
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            temperature = entries[0].current
                            break
            except:
                pass
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_percent,
                disk_free_gb=disk_free_gb,
                disk_total_gb=disk_total_gb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                load_average=load_average,
                process_count=process_count,
                temperature=temperature
            )
            
        except Exception as e:
            self.logger.error(f"시스템 메트릭 수집 실패: {e}")
            try:
                log_bug_fix("scripts/monitor.py", f"시스템 메트릭 수집 에러 수정: {str(e)}")
            except:
                pass
            
            # 기본값 반환
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                disk_total_gb=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0,
                load_average=[0.0, 0.0, 0.0],
                process_count=0,
                temperature=None
            )
    def check_alerts(self, bot_status: BotStatus, system_metrics: SystemMetrics):
        """고도화된 알림 조건 확인 및 발송"""
        try:
            current_time = datetime.now()
            alerts_to_send = []
            
            # 1. 봇 상태 알림
            if not bot_status.is_running and self.alert_config.bot_down_alert:
                alert_key = "bot_down"
                if self._should_send_alert(alert_key, current_time):
                    alerts_to_send.append({
                        "type": "critical",
                        "title": "🚨 트레이딩 봇 중지",
                        "message": f"CoinBot이 중지되었습니다.\n재시작 횟수: {bot_status.restart_count}\n마지막 에러: {bot_status.last_error or '없음'}",
                        "key": alert_key
                    })
            
            # 2. CPU 사용률 알림
            if system_metrics.cpu_percent > self.alert_config.cpu_threshold:
                alert_key = "high_cpu"
                if self._should_send_alert(alert_key, current_time):
                    alerts_to_send.append({
                        "type": "warning",
                        "title": "⚠️ 높은 CPU 사용률",
                        "message": f"CPU 사용률: {system_metrics.cpu_percent:.1f}%\n임계값: {self.alert_config.cpu_threshold}%",
                        "key": alert_key
                    })
            
            # 3. 메모리 사용률 알림
            if system_metrics.memory_percent > self.alert_config.memory_threshold:
                alert_key = "high_memory"
                if self._should_send_alert(alert_key, current_time):
                    alerts_to_send.append({
                        "type": "warning",
                        "title": "⚠️ 높은 메모리 사용률",
                        "message": f"메모리 사용률: {system_metrics.memory_percent:.1f}%\n사용량: {system_metrics.memory_used_mb:.1f}MB",
                        "key": alert_key
                    })
            
            # 4. 디스크 사용률 알림
            if system_metrics.disk_usage_percent > self.alert_config.disk_threshold:
                alert_key = "high_disk"
                if self._should_send_alert(alert_key, current_time):
                    alerts_to_send.append({
                        "type": "critical",
                        "title": "🚨 디스크 공간 부족",
                        "message": f"디스크 사용률: {system_metrics.disk_usage_percent:.1f}%\n남은 공간: {system_metrics.disk_free_gb:.2f}GB",
                        "key": alert_key
                    })
            
            # 5. 봇 활동 부재 알림
            if bot_status.is_running and bot_status.last_activity:
                try:
                    last_activity_time = datetime.fromisoformat(bot_status.last_activity)
                    inactive_duration = (current_time - last_activity_time).total_seconds() / 3600  # 시간 단위
                    
                    if inactive_duration > 2:  # 2시간 이상 비활성
                        alert_key = "bot_inactive"
                        if self._should_send_alert(alert_key, current_time):
                            alerts_to_send.append({
                                "type": "warning",
                                "title": "⚠️ 봇 활동 없음",
                                "message": f"마지막 활동으로부터 {inactive_duration:.1f}시간 경과\n마지막 활동: {bot_status.last_activity}",
                                "key": alert_key
                            })
                except:
                    pass
            
            # 6. 에러 횟수 알림
            if bot_status.error_count > self.alert_config.error_count_threshold:
                alert_key = "high_errors"
                if self._should_send_alert(alert_key, current_time):
                    alerts_to_send.append({
                        "type": "warning",
                        "title": "⚠️ 높은 에러 발생률",
                        "message": f"에러 횟수: {bot_status.error_count}\n최근 에러: {bot_status.last_error}",
                        "key": alert_key
                    })
            
            # 알림 발송
            for alert in alerts_to_send:
                self._send_alert(alert)
                self.alerts_sent[alert["key"]] = current_time
                
        except Exception as e:
            self.logger.error(f"알림 확인 중 오류: {e}")
            try:
                log_bug_fix("scripts/monitor.py", f"알림 시스템 에러 수정: {str(e)}")
            except:
                pass
    
    def _should_send_alert(self, alert_key: str, current_time: datetime) -> bool:
        """알림 쿨다운 확인"""
        if alert_key not in self.alerts_sent:
            return True
        
        last_sent = self.alerts_sent[alert_key]
        cooldown_minutes = self.alert_config.alert_cooldown_minutes
        
        return (current_time - last_sent).total_seconds() > (cooldown_minutes * 60)
    
    def _send_alert(self, alert: Dict[str, str]):
        """알림 발송"""
        try:
            message = f"{alert['title']}\n\n{alert['message']}\n\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 텔레그램 알림
            if self.telegram_bot and self.alert_config.telegram_enabled:
                try:
                    self.telegram_bot.send_message(message)
                    self.logger.info(f"📱 텔레그램 알림 발송: {alert['title']}")
                except Exception as e:
                    self.logger.error(f"텔레그램 알림 발송 실패: {e}")
            
            # 로그 기록
            log_level = "ERROR" if alert["type"] == "critical" else "WARNING"
            self.logger.log(getattr(logging, log_level), message)
            
        except Exception as e:
            self.logger.error(f"알림 발송 실패: {e}")
    
    def restart_bot(self) -> bool:
        """봇 재시작"""
        try:
            self.logger.info("🔄 봇 재시작 시도")
            
            # 기존 프로세스 종료
            self._stop_bot_process()
            
            # 잠시 대기
            time.sleep(3)
            
            # 새 프로세스 시작
            bot_script_path = PROJECT_ROOT / self.config["bot_script"]
            if not bot_script_path.exists():
                self.logger.error(f"봇 스크립트를 찾을 수 없음: {bot_script_path}")
                return False
            
            # 프로세스 시작
            process = subprocess.Popen(
                [self.config["python_executable"], str(bot_script_path)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # 시작 확인
            time.sleep(5)
            if process.poll() is None:  # 프로세스가 살아있음
                self.restart_count += 1
                self.last_restart = datetime.now().isoformat()
                self.logger.info(f"✅ 봇 재시작 성공 (PID: {process.pid})")
                
                try:
                    log_feature_add("scripts/monitor.py", f"봇 자동 재시작 성공 #{self.restart_count}")
                except:
                    pass
                
                # 성공 알림
                if self.telegram_bot:
                    try:
                        message = f"✅ CoinBot 재시작 완료\n재시작 횟수: {self.restart_count}\n시간: {self.last_restart}"
                        self.telegram_bot.send_message(message)
                    except:
                        pass
                
                return True
            else:
                self.logger.error("❌ 봇 재시작 실패 - 프로세스가 즉시 종료됨")
                return False
                
        except Exception as e:
            self.logger.error(f"봇 재시작 실패: {e}")
            try:
                log_bug_fix("scripts/monitor.py", f"봇 재시작 에러 수정: {str(e)}")
            except:
                pass
            return False
    
    def _stop_bot_process(self):
        """봇 프로세스 안전하게 종료"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline and 'python' in cmdline:
                        self.logger.info(f"봇 프로세스 종료 중: PID {proc.pid}")
                        
                        # 우선 SIGTERM으로 정상 종료 시도
                        proc.terminate()
                        
                        # 3초 대기 후 강제 종료
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            self.logger.warning("강제 종료 중...")
                            proc.kill()
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            self.logger.error(f"프로세스 종료 실패: {e}")
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """성과 지표 수집"""
        try:
            # 실제 구현에서는 데이터베이스나 로그 파일에서 읽어올 수 있음
            # 현재는 기본값 반환
            
            # 거래 로그 파일에서 정보 추출 시도
            trade_log_file = PROJECT_ROOT / "data/logs/trades.log"
            if trade_log_file.exists():
                # 로그 파일 분석 로직 (간단한 예시)
                try:
                    with open(trade_log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # 오늘 거래만 확인
                    today = datetime.now().strftime('%Y-%m-%d')
                    today_trades = [line for line in lines if today in line]
                    
                    successful_trades = len([line for line in today_trades if 'SUCCESS' in line])
                    failed_trades = len([line for line in today_trades if 'FAILED' in line])
                    total_trades = successful_trades + failed_trades
                    
                    win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
                    
                    self.performance_metrics.total_trades = total_trades
                    self.performance_metrics.successful_trades = successful_trades
                    self.performance_metrics.failed_trades = failed_trades
                    self.performance_metrics.win_rate = win_rate
                    
                except Exception as e:
                    self.logger.debug(f"거래 로그 분석 실패: {e}")
            
            return self.performance_metrics
            
        except Exception as e:
            self.logger.error(f"성과 지표 수집 실패: {e}")
            return PerformanceMetrics()
    
    def cleanup_old_metrics(self):
        """오래된 메트릭 정리"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.config["metrics_retention_hours"])
            cutoff_str = cutoff_time.isoformat()
            
            original_count = len(self.metrics_history)
            self.metrics_history = [
                metric for metric in self.metrics_history
                if metric.get("timestamp", "") > cutoff_str
            ]
            
            cleaned_count = original_count - len(self.metrics_history)
            if cleaned_count > 0:
                self.logger.debug(f"오래된 메트릭 {cleaned_count}개 정리됨")
                
        except Exception as e:
            self.logger.error(f"메트릭 정리 실패: {e}")
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict]:
        """지정된 시간 범위의 메트릭 히스토리 반환"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_str = cutoff_time.isoformat()
            
            filtered_metrics = [
                metric for metric in self.metrics_history
                if metric.get("timestamp", "") > cutoff_str
            ]
            
            return filtered_metrics[-100:]  # 최대 100개 반환
            
        except Exception as e:
            self.logger.error(f"메트릭 히스토리 조회 실패: {e}")
            return []
    def _setup_routes(self):
        """Flask API 라우트 설정"""
        
        @self.app.route('/')
        def dashboard():
            """모니터링 대시보드 메인 페이지"""
            return render_template_string(ENHANCED_DASHBOARD_TEMPLATE)
        
        @self.app.route('/api/status')
        def api_status():
            """봇 상태 API - 자세한 정보 포함"""
            try:
                status = self.get_bot_status()
                return jsonify({
                    "success": True,
                    "data": asdict(status),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/metrics')
        def api_metrics():
            """시스템 메트릭 API"""
            try:
                metrics = self.get_system_metrics()
                return jsonify({
                    "success": True,
                    "data": asdict(metrics),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/performance')
        def api_performance():
            """성과 지표 API"""
            try:
                performance = self.get_performance_metrics()
                return jsonify({
                    "success": True,
                    "data": asdict(performance),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/history')
        def api_history():
            """메트릭 히스토리 API"""
            try:
                hours = int(request.args.get('hours', 1))
                history = self.get_metrics_history(hours)
                return jsonify({
                    "success": True,
                    "data": history,
                    "count": len(history),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/restart', methods=['POST'])
        def api_restart():
            """봇 재시작 API"""
            try:
                success = self.restart_bot()
                return jsonify({
                    "success": success,
                    "message": "재시작 성공" if success else "재시작 실패",
                    "restart_count": self.restart_count,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/stop', methods=['POST'])
        def api_stop():
            """봇 중지 API"""
            try:
                self._stop_bot_process()
                return jsonify({
                    "success": True,
                    "message": "봇 중지 완료",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def api_config():
            """설정 조회/변경 API"""
            try:
                if request.method == 'GET':
                    return jsonify({
                        "success": True,
                        "data": self.config,
                        "timestamp": datetime.now().isoformat()
                    })
                else:  # POST
                    new_config = request.get_json()
                    if new_config:
                        old_config = self.config.copy()
                        self.config.update(new_config)
                        
                        try:
                            log_config_change("scripts/monitor.py", "모니터링 설정 변경", 
                                            {"old": old_config, "new": self.config})
                        except:
                            pass
                        
                        return jsonify({
                            "success": True,
                            "message": "설정 업데이트 완료",
                            "data": self.config,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        return jsonify({
                            "success": False,
                            "error": "유효하지 않은 설정 데이터"
                        }), 400
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/health')
        def api_health():
            """헬스체크 API"""
            try:
                bot_status = self.get_bot_status()
                system_metrics = self.get_system_metrics()
                
                health_score = 100
                issues = []
                
                # 건강도 계산
                if not bot_status.is_running:
                    health_score -= 50
                    issues.append("봇이 실행되지 않음")
                
                if system_metrics.cpu_percent > 90:
                    health_score -= 20
                    issues.append("높은 CPU 사용률")
                
                if system_metrics.memory_percent > 90:
                    health_score -= 15
                    issues.append("높은 메모리 사용률")
                
                if system_metrics.disk_usage_percent > 95:
                    health_score -= 15
                    issues.append("디스크 공간 부족")
                
                health_status = "excellent" if health_score >= 90 else \
                               "good" if health_score >= 70 else \
                               "warning" if health_score >= 50 else "critical"
                
                return jsonify({
                    "success": True,
                    "health_score": max(0, health_score),
                    "status": health_status,
                    "issues": issues,
                    "uptime_seconds": int((datetime.now() - self.start_time).total_seconds()),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "health_score": 0,
                    "status": "error"
                }), 500
    
    def monitoring_loop(self):
        """메인 모니터링 루프"""
        self.logger.info("🔍 모니터링 루프 시작")
        
        loop_count = 0
        
        while self.running:
            try:
                loop_count += 1
                
                # 봇 상태 및 시스템 메트릭 수집
                bot_status = self.get_bot_status()
                system_metrics = self.get_system_metrics()
                performance_metrics = self.get_performance_metrics()
                
                # 메트릭 히스토리에 추가
                combined_metrics = {
                    "loop_count": loop_count,
                    "bot_status": asdict(bot_status),
                    "system_metrics": asdict(system_metrics),
                    "performance_metrics": asdict(performance_metrics),
                    "timestamp": datetime.now().isoformat()
                }
                self.metrics_history.append(combined_metrics)
                
                # 알림 확인
                self.check_alerts(bot_status, system_metrics)
                
                # 자동 재시작 확인
                if (not bot_status.is_running and 
                    self.config["auto_restart"] and 
                    self.restart_count < self.config["restart_threshold"]):
                    
                    self.logger.warning("🔄 봇 자동 재시작 조건 충족")
                    self.restart_bot()
                
                # 메트릭 정리 (매 100번째 루프마다)
                if loop_count % 100 == 0:
                    self.cleanup_old_metrics()
                
                # 상태 로그 (매 20번째 루프마다, 즉 5분마다)
                if loop_count % 20 == 0:
                    status_msg = (f"📊 상태: 봇{'실행중' if bot_status.is_running else '중지'} | "
                                f"CPU: {system_metrics.cpu_percent:.1f}% | "
                                f"메모리: {system_metrics.memory_percent:.1f}% | "
                                f"거래: {performance_metrics.total_trades}회")
                    self.logger.info(status_msg)
                
                # 백업 (설정된 간격마다)
                if (self.config.get("backup_enabled", False) and 
                    loop_count % (self.config.get("backup_interval_hours", 6) * 240) == 0):  # 6시간 = 240 루프
                    self._create_backup()
                
                time.sleep(self.config["check_interval"])
                
            except KeyboardInterrupt:
                self.logger.info("⏹️ 사용자에 의한 모니터링 중지")
                break
            except Exception as e:
                self.logger.error(f"❌ 모니터링 루프 오류: {e}")
                try:
                    log_bug_fix("scripts/monitor.py", f"모니터링 루프 에러 수정: {str(e)}")
                except:
                    pass
                time.sleep(10)  # 오류 시 10초 대기
        
        self.logger.info("🛑 모니터링 루프 종료")
    
    def _create_backup(self):
        """데이터 백업 생성"""
        try:
            backup_dir = PROJECT_ROOT / "data/backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"monitor_backup_{timestamp}.json"
            
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "config": self.config,
                "metrics_history": self.metrics_history[-1000:],  # 최근 1000개만
                "restart_count": self.restart_count,
                "last_restart": self.last_restart
            }
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 백업 생성 완료: {backup_file}")
            
        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
    
    def start_web_server(self):
        """웹 서버 시작"""
        try:
            self.logger.info(f"🌐 웹 서버 시작 중... 포트: {self.config['web_port']}")
            self.app.run(
                host='0.0.0.0',
                port=self.config["web_port"],
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            self.logger.error(f"웹 서버 시작 실패: {e}")
            try:
                log_bug_fix("scripts/monitor.py", f"웹 서버 시작 에러 수정: {str(e)}")
            except:
                pass
    
    def run(self, web_server: bool = True):
        """고도화된 모니터 실행"""
        try:
            self.logger.info("🚀 고도화된 CoinBot 모니터링 시스템 시작")
            
            # 초기 상태 체크
            initial_status = self.get_bot_status()
            if initial_status.is_running:
                self.logger.info(f"✅ 봇이 이미 실행 중 (PID: {initial_status.pid})")
            else:
                self.logger.warning("⚠️ 봇이 실행되지 않음")
            
            # 웹 서버를 별도 스레드에서 실행
            if web_server:
                web_thread = threading.Thread(target=self.start_web_server, daemon=True)
                web_thread.start()
                self.logger.info(f"🌐 웹 대시보드: http://localhost:{self.config['web_port']}")
            
            # 시작 알림
            if self.telegram_bot:
                try:
                    start_message = f"🚀 CoinBot 모니터링 시스템 시작\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n대시보드: http://localhost:{self.config['web_port']}"
                    self.telegram_bot.send_message(start_message)
                except:
                    pass
            
            # 메인 모니터링 루프 실행
            self.monitoring_loop()
            
        except KeyboardInterrupt:
            self.logger.info("🛑 모니터링 시스템 종료")
        except Exception as e:
            self.logger.error(f"❌ 모니터링 시스템 오류: {e}")
        finally:
            self.running = False
            # 종료 알림
            if self.telegram_bot:
                try:
                    end_message = f"🛑 CoinBot 모니터링 시스템 종료\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    self.telegram_bot.send_message(end_message)
                except:
                    pass

# 고도화된 대시보드 HTML 템플릿 (간소화된 버전)
ENHANCED_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🎯 CoinBot 고도화 모니터링</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8f9fa; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .metric { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #eee; }
        .metric:last-child { border-bottom: none; }
        .metric-value { font-weight: bold; font-size: 1.2em; }
        .status-good { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-danger { color: #dc3545; }
        .button { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-warning { background: #ffc107; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .loading { text-align: center; color: #666; padding: 20px; }
        #lastUpdate { text-align: center; margin-top: 20px; color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 CoinBot 고도화 모니터링 시스템</h1>
            <p>실시간 봇 상태 및 시스템 모니터링</p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>🤖 봇 상태</h3>
                <div id="botStatus" class="loading">로딩 중...</div>
            </div>
            
            <div class="card">
                <h3>💻 시스템 메트릭</h3>
                <div id="systemMetrics" class="loading">로딩 중...</div>
            </div>
            
            <div class="card">
                <h3>📊 성과 지표</h3>
                <div id="performanceMetrics" class="loading">로딩 중...</div>
            </div>
            
            <div class="card">
                <h3>🎮 제어판</h3>
                <button class="button btn-success" onclick="restartBot()">🔄 재시작</button>
                <button class="button btn-danger" onclick="stopBot()">⏹️ 중지</button>
                <button class="button btn-primary" onclick="refreshData()">🔃 새로고침</button>
                <div id="controlStatus" style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    시스템 정상 운영 중
                </div>
            </div>
        </div>
        
        <div id="lastUpdate"></div>
    </div>

    <script>
        function updateDashboard() {
            // 봇 상태 업데이트
            fetch('/api/status')
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        const data = result.data;
                        const statusClass = data.is_running ? 'status-good' : 'status-danger';
                        const uptime = formatUptime(data.uptime_seconds);
                        
                        document.getElementById('botStatus').innerHTML = \`
                            <div class="metric">
                                <span>상태</span>
                                <span class="metric-value \${statusClass}">
                                    \${data.is_running ? '🟢 실행중' : '🔴 중지'}
                                </span>
                            </div>
                            <div class="metric">
                                <span>가동시간</span>
                                <span class="metric-value">\${uptime}</span>
                            </div>
                            <div class="metric">
                                <span>재시작 횟수</span>
                                <span class="metric-value">\${data.restart_count}</span>
                            </div>
                            <div class="metric">
                                <span>CPU 사용률</span>
                                <span class="metric-value">\${data.cpu_percent.toFixed(1)}%</span>
                            </div>
                        \`;
                    }
                })
                .catch(error => {
                    document.getElementById('botStatus').innerHTML = '<div class="metric"><span class="status-danger">⚠️ 상태 조회 실패</span></div>';
                });
            
            // 시스템 메트릭 업데이트
            fetch('/api/metrics')
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        const data = result.data;
                        
                        document.getElementById('systemMetrics').innerHTML = \`
                            <div class="metric">
                                <span>CPU</span>
                                <span class="metric-value \${data.cpu_percent > 80 ? 'status-danger' : 'status-good'}">
                                    \${data.cpu_percent.toFixed(1)}%
                                </span>
                            </div>
                            <div class="metric">
                                <span>메모리</span>
                                <span class="metric-value \${data.memory_percent > 80 ? 'status-warning' : 'status-good'}">
                                    \${data.memory_percent.toFixed(1)}%
                                </span>
                            </div>
                            <div class="metric">
                                <span>디스크</span>
                                <span class="metric-value \${data.disk_usage_percent > 90 ? 'status-danger' : 'status-good'}">
                                    \${data.disk_usage_percent.toFixed(1)}%
                                </span>
                            </div>
                            <div class="metric">
                                <span>남은 용량</span>
                                <span class="metric-value">\${data.disk_free_gb.toFixed(1)}GB</span>
                            </div>
                        \`;
                    }
                })
                .catch(error => {
                    document.getElementById('systemMetrics').innerHTML = '<div class="metric"><span class="status-danger">⚠️ 메트릭 조회 실패</span></div>';
                });
            
            // 성과 지표 업데이트
            fetch('/api/performance')
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        const data = result.data;
                        
                        document.getElementById('performanceMetrics').innerHTML = \`
                            <div class="metric">
                                <span>총 거래</span>
                                <span class="metric-value">\${data.total_trades}회</span>
                            </div>
                            <div class="metric">
                                <span>성공률</span>
                                <span class="metric-value \${data.win_rate > 50 ? 'status-good' : 'status-warning'}">
                                    \${data.win_rate.toFixed(1)}%
                                </span>
                            </div>
                            <div class="metric">
                                <span>성공/실패</span>
                                <span class="metric-value">\${data.successful_trades}/\${data.failed_trades}</span>
                            </div>
                        \`;
                    }
                })
                .catch(error => {
                    document.getElementById('performanceMetrics').innerHTML = '<div class="metric"><span class="status-danger">⚠️ 성과 조회 실패</span></div>';
                });
            
            // 마지막 업데이트 시간
            document.getElementById('lastUpdate').textContent = 
                '마지막 업데이트: ' + new Date().toLocaleTimeString();
        }
        
        function formatUptime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return \`\${hours}시간 \${minutes}분\`;
        }
        
        function restartBot() {
            if (confirm('봇을 재시작하시겠습니까?')) {
                fetch('/api/restart', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.success ? '✅ 재시작 완료' : '❌ 재시작 실패');
                        setTimeout(updateDashboard, 2000);
                    })
                    .catch(error => alert('❌ 재시작 요청 실패'));
            }
        }
        
        function stopBot() {
            if (confirm('봇을 중지하시겠습니까?')) {
                fetch('/api/stop', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.success ? '✅ 중지 완료' : '❌ 중지 실패');
                        setTimeout(updateDashboard, 2000);
                    })
                    .catch(error => alert('❌ 중지 요청 실패'));
            }
        }
        
        function refreshData() {
            updateDashboard();
        }
        
        // 초기 로드 및 주기적 업데이트
        updateDashboard();
        setInterval(updateDashboard, 10000); // 10초마다 업데이트
    </script>
</body>
</html>
'''

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="🎯 CoinBot 고도화 모니터링 시스템")
    parser.add_argument("--config", "-c", help="설정 파일 경로")
    parser.add_argument("--no-web", action="store_true", help="웹 서버 비활성화")
    parser.add_argument("--port", "-p", type=int, default=8888, help="웹 서버 포트")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help="로그 레벨")
    
    args = parser.parse_args()
    
    try:
        # 모니터 생성
        monitor = EnhancedBotMonitor(args.config)
        
        # 포트 설정 오버라이드
        if args.port != 8888:
            monitor.config["web_port"] = args.port
            try:
                log_config_change("scripts/monitor.py", "웹 포트 변경", 
                                {"port": {"old": 8888, "new": args.port}})
            except:
                pass
        
        # 로그 레벨 설정
        monitor.logger.setLevel(getattr(logging, args.log_level))
        
        # 모니터 실행
        monitor.run(web_server=not args.no_web)
        
    except Exception as e:
        print(f"❌ 모니터링 시스템 시작 실패: {e}")
        try:
            log_bug_fix("scripts/monitor.py", f"시스템 시작 에러 수정: {str(e)}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
                                
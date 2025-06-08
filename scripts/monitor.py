#!/usr/bin/env python3
"""
트레이딩 봇 외부 모니터링 스크립트
- 봇 프로세스 상태 모니터링
- 시스템 리소스 모니터링
- 성능 지표 추적
- 자동 알림 및 재시작
- 웹 API 제공
"""

import os
import sys
import time
import json
import psutil
import argparse
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from flask import Flask, jsonify, render_template_string
import requests

# 프로젝트 루트 디렉토리 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

@dataclass
class SystemMetrics:
    """시스템 메트릭 데이터 클래스"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float

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

class BotMonitor:
    def __init__(self, config_file: str = None):
        self.config = self.load_config(config_file)
        self.bot_process = None
        self.start_time = datetime.now()
        self.restart_count = 0
        self.last_restart = None
        self.metrics_history = []
        self.alerts_sent = set()
        self.running = True
        
        # Flask 앱 초기화
        self.app = Flask(__name__)
        self.setup_routes()
        
        # 초기 네트워크 통계
        self.initial_net_io = psutil.net_io_counters()
        
    def load_config(self, config_file: str = None) -> Dict[str, Any]:
        """설정 파일 로드"""
        default_config = {
            "bot_script": "main.py",
            "check_interval": 30,  # 30초마다 확인
            "restart_threshold": 3,  # 3회까지 재시작
            "cpu_alert_threshold": 80,  # CPU 80% 이상 시 알림
            "memory_alert_threshold": 500,  # 메모리 500MB 이상 시 알림
            "disk_alert_threshold": 90,  # 디스크 90% 이상 시 알림
            "web_port": 8888,
            "telegram_alerts": True,
            "auto_restart": True,
            "log_file": "logs/monitor.log",
            "metrics_retention_hours": 24
        }
        
        if config_file and Path(config_file).exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                
        return default_config
        
    def setup_routes(self):
        """Flask 라우트 설정"""
        
        @self.app.route('/')
        def dashboard():
            """모니터링 대시보드"""
            return render_template_string(DASHBOARD_TEMPLATE)
            
        @self.app.route('/api/status')
        def api_status():
            """봇 상태 API"""
            return jsonify(asdict(self.get_bot_status()))
            
        @self.app.route('/api/metrics')
        def api_metrics():
            """시스템 메트릭 API"""
            return jsonify(asdict(self.get_system_metrics()))
            
        @self.app.route('/api/history')
        def api_history():
            """메트릭 히스토리 API"""
            hours = int(request.args.get('hours', 1))
            return jsonify(self.get_metrics_history(hours))
            
        @self.app.route('/api/restart', methods=['POST'])
        def api_restart():
            """봇 재시작 API"""
            success = self.restart_bot()
            return jsonify({"success": success})
            
        @self.app.route('/api/stop', methods=['POST'])
        def api_stop():
            """봇 중지 API"""
            success = self.stop_bot()
            return jsonify({"success": success})
    
    def find_bot_process(self) -> Optional[psutil.Process]:
        """봇 프로세스 찾기"""
        bot_script = self.config["bot_script"]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if bot_script in cmdline and 'python' in cmdline.lower():
                        return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def get_bot_status(self) -> BotStatus:
        """봇 상태 조회"""
        bot_proc = self.find_bot_process()
        
        if bot_proc:
            try:
                uptime = int((datetime.now() - datetime.fromtimestamp(bot_proc.create_time())).total_seconds())
                cpu_percent = bot_proc.cpu_percent()
                memory_mb = bot_proc.memory_info().rss / (1024 * 1024)
                
                return BotStatus(
                    is_running=True,
                    pid=bot_proc.pid,
                    uptime_seconds=uptime,
                    last_restart=self.last_restart,
                    restart_count=self.restart_count,
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    status_message="정상 실행 중"
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return BotStatus(
            is_running=False,
            pid=None,
            uptime_seconds=0,
            last_restart=self.last_restart,
            restart_count=self.restart_count,
            cpu_percent=0.0,
            memory_mb=0.0,
            status_message="봇이 실행되지 않음"
        )
    
    def get_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 사용률
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        
        # 디스크 사용률
        disk = psutil.disk_usage(PROJECT_ROOT)
        disk_percent = (disk.used / disk.total) * 100
        disk_free_gb = disk.free / (1024**3)
        
        # 네트워크 사용률
        current_net_io = psutil.net_io_counters()
        net_sent_mb = (current_net_io.bytes_sent - self.initial_net_io.bytes_sent) / (1024 * 1024)
        net_recv_mb = (current_net_io.bytes_recv - self.initial_net_io.bytes_recv) / (1024 * 1024)
        
        return SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            disk_usage_percent=disk_percent,
            disk_free_gb=disk_free_gb,
            network_sent_mb=net_sent_mb,
            network_recv_mb=net_recv_mb
        )
    
    def check_alerts(self, bot_status: BotStatus, system_metrics: SystemMetrics):
        """알림 조건 확인 및 발송"""
        alerts = []
        current_time = datetime.now().isoformat()
        
        # 봇 상태 알림
        if not bot_status.is_running:
            alert_key = f"bot_down_{current_time[:13]}"  # 시간별로 중복 방지
            if alert_key not in self.alerts_sent:
                alerts.append("🚨 트레이딩 봇이 중지되었습니다!")
                self.alerts_sent.add(alert_key)
        
        # CPU 사용률 알림
        if system_metrics.cpu_percent > self.config["cpu_alert_threshold"]:
            alert_key = f"high_cpu_{current_time[:13]}"
            if alert_key not in self.alerts_sent:
                alerts.append(f"⚠️ 높은 CPU 사용률: {system_metrics.cpu_percent:.1f}%")
                self.alerts_sent.add(alert_key)
        
        # 메모리 사용률 알림
        if bot_status.memory_mb > self.config["memory_alert_threshold"]:
            alert_key = f"high_memory_{current_time[:13]}"
            if alert_key not in self.alerts_sent:
                alerts.append(f"⚠️ 높은 메모리 사용량: {bot_status.memory_mb:.1f}MB")
                self.alerts_sent.add(alert_key)
        
        # 디스크 사용률 알림
        if system_metrics.disk_usage_percent > self.config["disk_alert_threshold"]:
            alert_key = f"high_disk_{current_time[:13]}"
            if alert_key not in self.alerts_sent:
                alerts.append(f"⚠️ 높은 디스크 사용률: {system_metrics.disk_usage_percent:.1f}%")
                self.alerts_sent.add(alert_key)
        
        # 알림 발송
        if alerts and self.config["telegram_alerts"]:
            self.send_telegram_alerts(alerts)
    
    def send_telegram_alerts(self, alerts: List[str]):
        """텔레그램 알림 발송"""
        try:
            from utils.telegram_bot import TelegramBot
            
            # .env에서 텔레그램 설정 로드
            from dotenv import load_dotenv
            load_dotenv()
            
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if bot_token and chat_id:
                telegram_bot = TelegramBot(bot_token, chat_id)
                
                message = "🔔 **모니터링 알림**\n\n" + "\n".join(alerts)
                telegram_bot.send_message(message)
                
        except Exception as e:
            self.log(f"텔레그램 알림 발송 실패: {e}")
    
    def restart_bot(self) -> bool:
        """봇 재시작"""
        try:
            # 기존 봇 프로세스 종료
            bot_proc = self.find_bot_process()
            if bot_proc:
                bot_proc.terminate()
                bot_proc.wait(timeout=10)
            
            # 새 봇 프로세스 시작
            bot_script_path = PROJECT_ROOT / self.config["bot_script"]
            subprocess.Popen([
                sys.executable, str(bot_script_path)
            ], cwd=PROJECT_ROOT)
            
            self.restart_count += 1
            self.last_restart = datetime.now().isoformat()
            self.log(f"봇 재시작 완료 (#{self.restart_count})")
            
            return True
            
        except Exception as e:
            self.log(f"봇 재시작 실패: {e}")
            return False
    
    def stop_bot(self) -> bool:
        """봇 중지"""
        try:
            bot_proc = self.find_bot_process()
            if bot_proc:
                bot_proc.terminate()
                bot_proc.wait(timeout=10)
                self.log("봇 중지 완료")
                return True
            return False
            
        except Exception as e:
            self.log(f"봇 중지 실패: {e}")
            return False
    
    def cleanup_old_metrics(self):
        """오래된 메트릭 데이터 정리"""
        cutoff_time = datetime.now() - timedelta(hours=self.config["metrics_retention_hours"])
        cutoff_str = cutoff_time.isoformat()
        
        self.metrics_history = [
            metric for metric in self.metrics_history
            if metric.get("timestamp", "") > cutoff_str
        ]
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict]:
        """메트릭 히스토리 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()
        
        return [
            metric for metric in self.metrics_history
            if metric.get("timestamp", "") > cutoff_str
        ]
    
    def log(self, message: str, level: str = "INFO"):
        """로그 기록"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        
        print(log_message)
        
        # 로그 파일에 기록
        log_file = PROJECT_ROOT / self.config["log_file"]
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + "\n")
    
    def monitoring_loop(self):
        """메인 모니터링 루프"""
        self.log("🔍 모니터링 시작")
        
        while self.running:
            try:
                # 봇 상태 및 시스템 메트릭 수집
                bot_status = self.get_bot_status()
                system_metrics = self.get_system_metrics()
                
                # 메트릭 히스토리에 추가
                combined_metrics = {
                    **asdict(bot_status),
                    **asdict(system_metrics)
                }
                self.metrics_history.append(combined_metrics)
                
                # 알림 확인
                self.check_alerts(bot_status, system_metrics)
                
                # 자동 재시작 확인
                if (not bot_status.is_running and 
                    self.config["auto_restart"] and 
                    self.restart_count < self.config["restart_threshold"]):
                    
                    self.log("🔄 봇 자동 재시작 시도")
                    self.restart_bot()
                
                # 오래된 메트릭 정리
                self.cleanup_old_metrics()
                
                # 상태 로그 (5분마다)
                if int(time.time()) % 300 == 0:
                    status_msg = f"봇 상태: {'실행중' if bot_status.is_running else '중지'}, "
                    status_msg += f"CPU: {system_metrics.cpu_percent:.1f}%, "
                    status_msg += f"메모리: {system_metrics.memory_used_mb:.1f}MB"
                    self.log(status_msg)
                
                time.sleep(self.config["check_interval"])
                
            except KeyboardInterrupt:
                self.log("모니터링 중지됨")
                break
            except Exception as e:
                self.log(f"모니터링 오류: {e}", "ERROR")
                time.sleep(10)
    
    def start_web_server(self):
        """웹 서버 시작"""
        try:
            self.app.run(
                host='0.0.0.0',
                port=self.config["web_port"],
                debug=False,
                use_reloader=False
            )
        except Exception as e:
            self.log(f"웹 서버 시작 실패: {e}", "ERROR")
    
    def run(self, web_server: bool = True):
        """모니터 실행"""
        try:
            # 웹 서버를 별도 스레드에서 실행
            if web_server:
                web_thread = threading.Thread(target=self.start_web_server, daemon=True)
                web_thread.start()
                self.log(f"🌐 웹 대시보드 시작: http://localhost:{self.config['web_port']}")
            
            # 메인 모니터링 루프 실행
            self.monitoring_loop()
            
        except KeyboardInterrupt:
            self.log("🛑 모니터링 종료")
        finally:
            self.running = False

# 웹 대시보드 HTML 템플릿
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>트레이딩 봇 모니터</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-good { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-danger { color: #dc3545; }
        .metric { display: inline-block; margin: 10px 20px 10px 0; }
        .metric-value { font-size: 24px; font-weight: bold; }
        .metric-label { font-size: 12px; color: #666; }
        .btn { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .refresh-indicator { float: right; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 트레이딩 봇 모니터 <span class="refresh-indicator" id="lastUpdate"></span></h1>
        
        <div class="card">
            <h2>봇 상태</h2>
            <div id="botStatus"></div>
            <button class="btn" onclick="restartBot()">재시작</button>
            <button class="btn btn-danger" onclick="stopBot()">중지</button>
        </div>
        
        <div class="card">
            <h2>시스템 메트릭</h2>
            <div id="systemMetrics"></div>
        </div>
        
        <div class="card">
            <h2>실시간 차트</h2>
            <canvas id="metricsChart" width="800" height="400"></canvas>
        </div>
    </div>

    <script>
        function updateDashboard() {
            // 봇 상태 업데이트
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const statusElement = document.getElementById('botStatus');
                    const statusClass = data.is_running ? 'status-good' : 'status-danger';
                    const uptime = formatUptime(data.uptime_seconds);
                    
                    statusElement.innerHTML = `
                        <div class="metric">
                            <div class="metric-value ${statusClass}">
                                ${data.is_running ? '🟢 실행중' : '🔴 중지'}
                            </div>
                            <div class="metric-label">상태</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${uptime}</div>
                            <div class="metric-label">가동시간</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${data.cpu_percent.toFixed(1)}%</div>
                            <div class="metric-label">CPU</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${data.memory_mb.toFixed(1)}MB</div>
                            <div class="metric-label">메모리</div>
                        </div>
                    `;
                });
            
            // 시스템 메트릭 업데이트
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {
                    const metricsElement = document.getElementById('systemMetrics');
                    
                    metricsElement.innerHTML = `
                        <div class="metric">
                            <div class="metric-value ${data.cpu_percent > 80 ? 'status-danger' : 'status-good'}">
                                ${data.cpu_percent.toFixed(1)}%
                            </div>
                            <div class="metric-label">전체 CPU</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value ${data.memory_percent > 80 ? 'status-warning' : 'status-good'}">
                                ${data.memory_percent.toFixed(1)}%
                            </div>
                            <div class="metric-label">메모리 사용률</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value ${data.disk_usage_percent > 90 ? 'status-danger' : 'status-good'}">
                                ${data.disk_usage_percent.toFixed(1)}%
                            </div>
                            <div class="metric-label">디스크 사용률</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${data.disk_free_gb.toFixed(1)}GB</div>
                            <div class="metric-label">남은 용량</div>
                        </div>
                    `;
                });
            
            // 마지막 업데이트 시간
            document.getElementById('lastUpdate').textContent = 
                '마지막 업데이트: ' + new Date().toLocaleTimeString();
        }
        
        function formatUptime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}시간 ${minutes}분`;
        }
        
        function restartBot() {
            if (confirm('봇을 재시작하시겠습니까?')) {
                fetch('/api/restart', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.success ? '재시작 완료' : '재시작 실패');
                        updateDashboard();
                    });
            }
        }
        
        function stopBot() {
            if (confirm('봇을 중지하시겠습니까?')) {
                fetch('/api/stop', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.success ? '중지 완료' : '중지 실패');
                        updateDashboard();
                    });
            }
        }
        
        // 초기 로드 및 주기적 업데이트
        updateDashboard();
        setInterval(updateDashboard, 5000); // 5초마다 업데이트
    </script>
</body>
</html>
'''

def main():
    parser = argparse.ArgumentParser(description="트레이딩 봇 모니터링 스크립트")
    parser.add_argument("--config", "-c", help="설정 파일 경로")
    parser.add_argument("--no-web", action="store_true", help="웹 서버 비활성화")
    parser.add_argument("--port", "-p", type=int, default=8888, help="웹 서버 포트")
    
    args = parser.parse_args()
    
    # 모니터 생성 및 실행
    monitor = BotMonitor(args.config)
    
    if args.port != 8888:
        monitor.config["web_port"] = args.port
    
    monitor.run(web_server=not args.no_web)

if __name__ == "__main__":
    main()
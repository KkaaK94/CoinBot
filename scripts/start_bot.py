#!/usr/bin/env python3
"""
안전한 트레이딩 봇 시작 스크립트
- 환경 검증
- 안전 모드 지원
- 자동 재시작
- 로그 관리
- 긴급 정지 기능
"""

import os
import sys
import time
import signal
import psutil
import logging
import argparse
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class BotLauncher:
    def __init__(self):
        self.bot_process = None
        self.should_restart = True
        self.restart_count = 0
        self.max_restarts = 5
        self.restart_interval = 30  # 30초
        self.safe_mode = False
        self.setup_logging()
        
    def setup_logging(self):
        """로깅 설정"""
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / f"launcher_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("BotLauncher")
        
    def check_environment(self):
        """환경 및 설정 검증"""
        self.logger.info("🔍 환경 검증 시작...")
        
        checks = []
        
        # 1. Python 버전 확인
        if sys.version_info < (3, 8):
            checks.append("❌ Python 3.8 이상이 필요합니다")
        else:
            checks.append("✅ Python 버전 확인")
            
        # 2. 필수 파일 확인
        required_files = [
            ".env",
            "main.py",
            "config/settings.py",
            "requirements.txt"
        ]
        
        for file_path in required_files:
            if (PROJECT_ROOT / file_path).exists():
                checks.append(f"✅ {file_path} 존재")
            else:
                checks.append(f"❌ {file_path} 누락")
                
        # 3. 환경 변수 확인
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
        
        required_env_vars = [
            "UPBIT_ACCESS_KEY",
            "UPBIT_SECRET_KEY",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID"
        ]
        
        for var in required_env_vars:
            if os.getenv(var):
                checks.append(f"✅ {var} 설정됨")
            else:
                checks.append(f"❌ {var} 누락")
                
        # 4. 디스크 공간 확인
        disk_usage = psutil.disk_usage(PROJECT_ROOT)
        free_gb = disk_usage.free / (1024**3)
        if free_gb > 1.0:
            checks.append(f"✅ 디스크 공간 충분 ({free_gb:.1f}GB)")
        else:
            checks.append(f"⚠️ 디스크 공간 부족 ({free_gb:.1f}GB)")
            
        # 5. 메모리 확인
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        if available_gb > 0.5:
            checks.append(f"✅ 메모리 충분 ({available_gb:.1f}GB)")
        else:
            checks.append(f"⚠️ 메모리 부족 ({available_gb:.1f}GB)")
            
        # 결과 출력
        for check in checks:
            self.logger.info(check)
            
        # 실패한 검사가 있는지 확인
        failed_checks = [check for check in checks if check.startswith("❌")]
        if failed_checks:
            self.logger.error("환경 검증 실패. 위 문제들을 해결한 후 다시 시도하세요.")
            return False
            
        self.logger.info("✅ 환경 검증 완료!")
        return True
        
    def install_dependencies(self):
        """의존성 패키지 설치"""
        self.logger.info("📦 의존성 패키지 확인 중...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", 
                str(PROJECT_ROOT / "requirements.txt")
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info("✅ 의존성 패키지 설치 완료")
                return True
            else:
                self.logger.error(f"❌ 패키지 설치 실패: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("❌ 패키지 설치 시간 초과")
            return False
        except Exception as e:
            self.logger.error(f"❌ 패키지 설치 오류: {e}")
            return False
            
    def check_bot_running(self):
        """다른 봇 인스턴스가 실행 중인지 확인"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    if proc.pid != os.getpid():
                        return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
        
    def start_bot(self):
        """봇 프로세스 시작"""
        if self.bot_process and self.bot_process.poll() is None:
            self.logger.warning("봇이 이미 실행 중입니다.")
            return False
            
        try:
            cmd = [sys.executable, "main.py"]
            if self.safe_mode:
                cmd.extend(["--safe-mode"])
                
            self.logger.info(f"🚀 봇 시작: {' '.join(cmd)}")
            
            self.bot_process = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 봇 출력을 실시간으로 로깅
            self.start_output_logging()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 봇 시작 실패: {e}")
            return False
            
    def start_output_logging(self):
        """봇 출력을 실시간으로 로깅"""
        def log_output(pipe, level):
            for line in iter(pipe.readline, ''):
                if line.strip():
                    getattr(self.logger, level)(f"[BOT] {line.strip()}")
                    
        # stdout과 stderr를 별도 스레드에서 처리
        threading.Thread(
            target=log_output, 
            args=(self.bot_process.stdout, 'info'),
            daemon=True
        ).start()
        
        threading.Thread(
            target=log_output, 
            args=(self.bot_process.stderr, 'error'),
            daemon=True
        ).start()
        
    def monitor_bot(self):
        """봇 프로세스 모니터링"""
        self.logger.info("📊 봇 모니터링 시작...")
        
        while self.should_restart:
            if self.bot_process is None:
                break
                
            # 프로세스 상태 확인
            return_code = self.bot_process.poll()
            
            if return_code is None:
                # 프로세스가 실행 중
                try:
                    # CPU 및 메모리 사용량 확인
                    proc = psutil.Process(self.bot_process.pid)
                    cpu_percent = proc.cpu_percent()
                    memory_mb = proc.memory_info().rss / (1024 * 1024)
                    
                    if cpu_percent > 80:
                        self.logger.warning(f"⚠️ 높은 CPU 사용률: {cpu_percent:.1f}%")
                    if memory_mb > 500:
                        self.logger.warning(f"⚠️ 높은 메모리 사용량: {memory_mb:.1f}MB")
                        
                except psutil.NoSuchProcess:
                    self.logger.error("❌ 봇 프로세스를 찾을 수 없습니다")
                    break
                    
            else:
                # 프로세스가 종료됨
                if return_code == 0:
                    self.logger.info("✅ 봇이 정상적으로 종료되었습니다")
                    break
                else:
                    self.logger.error(f"❌ 봇이 비정상적으로 종료되었습니다 (코드: {return_code})")
                    
                    if self.should_restart and self.restart_count < self.max_restarts:
                        self.restart_count += 1
                        self.logger.info(f"🔄 봇 재시작 시도 {self.restart_count}/{self.max_restarts}")
                        time.sleep(self.restart_interval)
                        
                        if self.start_bot():
                            continue
                        else:
                            self.logger.error("❌ 봇 재시작 실패")
                            break
                    else:
                        self.logger.error("❌ 최대 재시작 횟수 초과 또는 재시작 비활성화")
                        break
                        
            time.sleep(10)  # 10초마다 확인
            
    def stop_bot(self):
        """봇 프로세스 중지"""
        self.should_restart = False
        
        if self.bot_process and self.bot_process.poll() is None:
            self.logger.info("🛑 봇 중지 중...")
            
            try:
                # 정상적인 종료 시도
                self.bot_process.terminate()
                
                # 5초 대기
                try:
                    self.bot_process.wait(timeout=5)
                    self.logger.info("✅ 봇이 정상적으로 중지되었습니다")
                except subprocess.TimeoutExpired:
                    # 강제 종료
                    self.logger.warning("⚠️ 강제 종료 중...")
                    self.bot_process.kill()
                    self.bot_process.wait()
                    self.logger.info("✅ 봇이 강제로 중지되었습니다")
                    
            except Exception as e:
                self.logger.error(f"❌ 봇 중지 오류: {e}")
                
    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        signal_names = {
            signal.SIGINT: "SIGINT",
            signal.SIGTERM: "SIGTERM"
        }
        
        signal_name = signal_names.get(signum, f"Signal {signum}")
        self.logger.info(f"📨 {signal_name} 신호 수신됨")
        self.stop_bot()
        sys.exit(0)
        
    def run(self, safe_mode=False, no_restart=False):
        """메인 실행 함수"""
        self.safe_mode = safe_mode
        if no_restart:
            self.should_restart = False
            
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.logger.info("🎯 트레이딩 봇 런처 시작")
        
        # 1. 다른 봇 인스턴스 확인
        existing_bot = self.check_bot_running()
        if existing_bot:
            self.logger.error(f"❌ 다른 봇 인스턴스가 실행 중입니다 (PID: {existing_bot.pid})")
            response = input("기존 봇을 중지하고 계속하시겠습니까? (y/N): ")
            if response.lower() == 'y':
                existing_bot.terminate()
                time.sleep(2)
            else:
                return False
                
        # 2. 환경 검증
        if not self.check_environment():
            return False
            
        # 3. 의존성 설치
        if not self.install_dependencies():
            return False
            
        # 4. 봇 시작
        if not self.start_bot():
            return False
            
        # 5. 모니터링 시작
        try:
            self.monitor_bot()
        except KeyboardInterrupt:
            self.logger.info("📨 키보드 인터럽트 수신됨")
            self.stop_bot()
            
        return True

def main():
    parser = argparse.ArgumentParser(description="트레이딩 봇 안전 런처")
    parser.add_argument("--safe-mode", action="store_true", 
                       help="안전 모드로 실행 (실제 거래 비활성화)")
    parser.add_argument("--no-restart", action="store_true",
                       help="자동 재시작 비활성화")
    parser.add_argument("--check-only", action="store_true",
                       help="환경 검증만 수행")
    
    args = parser.parse_args()
    
    launcher = BotLauncher()
    
    if args.check_only:
        # 환경 검증만 수행
        success = launcher.check_environment()
        sys.exit(0 if success else 1)
    else:
        # 봇 실행
        success = launcher.run(
            safe_mode=args.safe_mode,
            no_restart=args.no_restart
        )
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
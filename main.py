#!/usr/bin/env python3
"""
CoinBot - 고도화 암호화폐 자동매매봇
목표: 16만원 → 50만원 (212% 수익)
개발환경: VS Code + Python + AWS EC2
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 패스 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

from config.settings import Settings
from core.strategy_engine import StrategyEngine
from core.trader import Trader
from core.risk_manager import RiskManager
from learning.performance_tracker import PerformanceTracker
from utils.logger import Logger
from utils.telegram_bot import TelegramBot

class CoinBot:
    """메인 매매봇 클래스"""
    
    def __init__(self):
        """초기화"""
        self.settings = Settings()
        self.logger = Logger()
        self.telegram = TelegramBot()
        
        # 핵심 모듈들 초기화
        self.strategy_engine = StrategyEngine(self.settings)
        self.trader = Trader(self.settings)
        self.risk_manager = RiskManager(self.settings)
        self.performance_tracker = PerformanceTracker(self.settings)
        
        self.is_running = False
        
        self.logger.info("🚀 CoinBot 초기화 완료")
        self.telegram.send_message("🤖 CoinBot이 시작되었습니다!")
    
    def start(self):
        """매매봇 시작"""
        try:
            self.is_running = True
            self.logger.info("📈 매매 시작")
            
            while self.is_running:
                try:
                    # 메인 매매 루프
                    self._trading_cycle()
                    
                except KeyboardInterrupt:
                    self.logger.info("🛑 사용자 중단 요청")
                    break
                except Exception as e:
                    self.logger.error(f"❌ 매매 루프 오류: {e}")
                    self.telegram.send_message(f"⚠️ 오류 발생: {str(e)}")
                    
        except Exception as e:
            self.logger.critical(f"🚨 시스템 오류: {e}")
        finally:
            self.stop()
    
    def _trading_cycle(self):
        """매매 사이클 실행"""
        # TODO: 핵심 매매 로직 구현
        pass
    
    def stop(self):
        """매매봇 중지"""
        self.is_running = False
        self.logger.info("🔴 CoinBot 종료")
        self.telegram.send_message("🛑 CoinBot이 종료되었습니다")

def main():
    """메인 실행 함수"""
    print("=" * 50)
    print("🚀 CoinBot v1.0 시작")
    print("💰 목표: 16만원 → 50만원")
    print("=" * 50)
    
    try:
        bot = CoinBot()
        bot.start()
    except Exception as e:
        print(f"❌ 시작 실패: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
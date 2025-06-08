#!/usr/bin/env python3
"""
간단한 트레이딩 봇 테스트 버전
문제 해결을 위한 최소 구현
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 설정만 import
from config.settings import init_settings

class SimpleTradingBot:
    """간단한 트레이딩 봇"""
    
    def __init__(self, safe_mode=True):
        self.safe_mode = safe_mode
        self.running = False
        
        print(f"🎯 간단 트레이딩 봇 시작 - 모드: {'안전' if safe_mode else '실제'}")
        
        # 설정 로드
        try:
            self.settings = init_settings(safe_mode=safe_mode)
            print("✅ 설정 로드 완료")
            print(f"• 거래 금액: {self.settings.trading.trade_amount:,}원")
            print(f"• 대상 코인: {len(self.settings.trading.target_coins)}개")
        except Exception as e:
            print(f"❌ 설정 로드 실패: {e}")
            raise
    
    async def simple_loop(self):
        """간단한 루프"""
        print("🔄 간단한 트레이딩 루프 시작")
        
        loop_count = 0
        
        while self.running:
            try:
                loop_count += 1
                print(f"📊 루프 #{loop_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # 각 코인에 대해 간단한 처리
                for symbol in self.settings.trading.target_coins:
                    print(f"  📈 {symbol} 분석 중...")
                    
                    # 임시 분석 결과
                    mock_analysis = {
                        "symbol": symbol,
                        "price": 50000,  # 임시 가격
                        "signal": "HOLD",
                        "rsi": 45
                    }
                    
                    print(f"  ✅ {symbol}: {mock_analysis['signal']} (RSI: {mock_analysis['rsi']})")
                
                print(f"✅ 루프 #{loop_count} 완료")
                
                # 30초 대기
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                print("\n🛑 사용자 중단")
                break
            except Exception as e:
                print(f"❌ 루프 오류: {e}")
                await asyncio.sleep(10)
    
    async def start(self):
        """봇 시작"""
        try:
            self.running = True
            print("🚀 봇 시작!")
            
            # 텔레그램 테스트 메시지
            if self.settings.api.telegram_bot_token:
                print("📱 텔레그램 설정 확인됨")
                # 실제 메시지는 보내지 않고 로그만
                print("📤 텔레그램 시작 메시지 (시뮬레이션)")
            
            # 간단한 루프 실행
            await self.simple_loop()
            
        except Exception as e:
            print(f"❌ 봇 실행 오류: {e}")
            raise
    
    def stop(self):
        """봇 중지"""
        print("🛑 봇 중지")
        self.running = False

async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="간단한 트레이딩 봇 테스트")
    parser.add_argument("--safe-mode", action="store_true", help="안전 모드")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🎯 간단한 트레이딩 봇 테스트")
    print("=" * 50)
    
    try:
        bot = SimpleTradingBot(safe_mode=args.safe_mode)
        await bot.start()
        
    except KeyboardInterrupt:
        print("\n👋 사용자 중단")
        return 0
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 프로그램 중단")
        sys.exit(0)
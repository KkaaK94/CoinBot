#!/usr/bin/env python3
"""
🎯 작동하는 간단한 CoinBot
- 복잡한 기능 제거
- 핵심 매매 로직만 포함
- 확실한 오류 방지
"""

import os
import asyncio
import time
import logging
from datetime import datetime
import pyupbit
import pandas as pd
import numpy as np

# 환경변수 설정
os.environ['UPBIT_ACCESS_KEY'] = "g2mwE3842nYhBpcYYxbFnCmYUKoeCrNkxwxZMs34"
os.environ['UPBIT_SECRET_KEY'] = "gbtsxYZtDHgCzKGHxqbl5xDDlJ8bxDXDPVquN5KT"
os.environ['TELEGRAM_BOT_TOKEN'] = "7548424998:AAFms0yZHILp9fnCzxc8dhEK-uQ64GhOTXk"
os.environ['TELEGRAM_CHAT_ID'] = "1195430324"

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - SimpleCoinBot - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleCoinBot:
    """간단하지만 작동하는 코인봇"""
    
    def __init__(self):
        self.running = True
        self.target_coins = ['KRW-BTC', 'KRW-ETH', 'KRW-ADA']
        
        # 업비트 API 초기화
        try:
            self.upbit = pyupbit.Upbit(
                os.environ['UPBIT_ACCESS_KEY'],
                os.environ['UPBIT_SECRET_KEY']
            )
            logger.info("✅ 업비트 API 연결 성공")
        except Exception as e:
            logger.error(f"❌ 업비트 API 연결 실패: {e}")
            self.upbit = None
        
        # 텔레그램 설정
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        logger.info("🚀 SimpleCoinBot 초기화 완료")
    
    def send_telegram_message(self, message):
        """텔레그램 메시지 발송"""
        try:
            if not self.telegram_token or not self.telegram_chat_id:
                return
            
            import requests
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("📱 텔레그램 메시지 발송 성공")
            else:
                logger.warning(f"📱 텔레그램 발송 실패: {response.status_code}")
        except Exception as e:
            logger.error(f"📱 텔레그램 오류: {e}")
    
    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            current_rsi = rsi.iloc[-1]
            
            if pd.isna(current_rsi):
                return 50.0
            
            return float(current_rsi)
            
        except Exception as e:
            logger.error(f"❌ RSI 계산 오류: {e}")
            return 50.0
    
    def analyze_coin(self, symbol):
        """코인 분석"""
        try:
            logger.info(f"🔍 {symbol} 분석 시작")
            
            # 현재가 조회
            current_price = pyupbit.get_current_price(symbol)
            if not current_price:
                logger.warning(f"⚠️ {symbol} 현재가 조회 실패")
                return None
            
            # 15분봉 데이터 조회
            df = pyupbit.get_ohlcv(symbol, interval="minute15", count=50)
            if df is None or df.empty or len(df) < 20:
                logger.warning(f"⚠️ {symbol} 차트 데이터 부족")
                return None
            
            # RSI 계산
            rsi = self.calculate_rsi(df['close'])
            
            # 신호 결정
            signal = "HOLD"
            confidence = 0.3
            
            if rsi <= 30:
                signal = "BUY"
                confidence = 0.8
                logger.info(f"🟢 {symbol}: 강한 매수 신호 (RSI: {rsi:.1f})")
            elif rsi <= 35:
                signal = "BUY"
                confidence = 0.6
                logger.info(f"🟢 {symbol}: 매수 신호 (RSI: {rsi:.1f})")
            elif rsi >= 70:
                signal = "SELL"
                confidence = 0.8
                logger.info(f"🔴 {symbol}: 강한 매도 신호 (RSI: {rsi:.1f})")
            elif rsi >= 65:
                signal = "SELL"
                confidence = 0.6
                logger.info(f"🔴 {symbol}: 매도 신호 (RSI: {rsi:.1f})")
            else:
                logger.info(f"🟡 {symbol}: 관망 (RSI: {rsi:.1f})")
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'rsi': rsi,
                'signal': signal,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"❌ {symbol} 분석 오류: {e}")
            return None
    
    def execute_trade(self, analysis):
        """거래 실행"""
        try:
            if not analysis or analysis['signal'] == 'HOLD':
                return
            
            if not self.upbit:
                logger.warning("⚠️ 업비트 API 없음 - 시뮬레이션 모드")
                self.simulate_trade(analysis)
                return
            
            symbol = analysis['symbol']
            signal = analysis['signal']
            confidence = analysis['confidence']
            current_price = analysis['current_price']
            
            # 신뢰도가 낮으면 거래 안함
            if confidence < 0.5:
                logger.info(f"⚠️ {symbol}: 신뢰도 낮음 ({confidence:.2f}) - 거래 건너뜀")
                return
            
            # 잔고 확인
            krw_balance = self.upbit.get_balance("KRW")
            if not krw_balance or krw_balance < 10000:
                logger.warning("⚠️ KRW 잔고 부족")
                return
            
            if signal == "BUY":
                # 매수 실행
                trade_amount = min(50000, krw_balance * 0.3)  # 잔고의 30% 또는 5만원
                
                logger.info(f"🟢 {symbol} 매수 시도: {trade_amount:,.0f}원")
                
                # 실제 주문 (시장가)
                result = self.upbit.buy_market_order(symbol, trade_amount)
                
                if result:
                    message = f"🟢 매수 체결!\n" \
                             f"코인: {symbol}\n" \
                             f"금액: {trade_amount:,.0f}원\n" \
                             f"가격: {current_price:,.0f}원\n" \
                             f"RSI: {analysis['rsi']:.1f}"
                    
                    logger.info(message.replace('\n', ' '))
                    self.send_telegram_message(message)
                else:
                    logger.error(f"❌ {symbol} 매수 실패")
            
            elif signal == "SELL":
                # 보유 수량 확인
                coin_name = symbol.split('-')[1]
                coin_balance = self.upbit.get_balance(coin_name)
                
                if not coin_balance or coin_balance <= 0:
                    logger.info(f"⚠️ {symbol}: 보유 수량 없음")
                    return
                
                logger.info(f"🔴 {symbol} 매도 시도: {coin_balance} 개")
                
                # 실제 주문 (시장가)
                result = self.upbit.sell_market_order(symbol, coin_balance)
                
                if result:
                    message = f"🔴 매도 체결!\n" \
                             f"코인: {symbol}\n" \
                             f"수량: {coin_balance}\n" \
                             f"가격: {current_price:,.0f}원\n" \
                             f"RSI: {analysis['rsi']:.1f}"
                    
                    logger.info(message.replace('\n', ' '))
                    self.send_telegram_message(message)
                else:
                    logger.error(f"❌ {symbol} 매도 실패")
                    
        except Exception as e:
            logger.error(f"❌ 거래 실행 오류: {e}")
    
    def simulate_trade(self, analysis):
        """거래 시뮬레이션 (API 없을 때)"""
        symbol = analysis['symbol']
        signal = analysis['signal']
        current_price = analysis['current_price']
        rsi = analysis['rsi']
        
        message = f"🎮 시뮬레이션 거래\n" \
                 f"코인: {symbol}\n" \
                 f"신호: {signal}\n" \
                 f"가격: {current_price:,.0f}원\n" \
                 f"RSI: {rsi:.1f}"
        
        logger.info(message.replace('\n', ' '))
        self.send_telegram_message(message)
    
    async def run_trading_loop(self):
        """메인 트레이딩 루프"""
        loop_count = 0
        
        logger.info("🚀 트레이딩 루프 시작")
        self.send_telegram_message("🚀 SimpleCoinBot 시작!")
        
        while self.running:
            try:
                loop_count += 1
                logger.info(f"🔄 트레이딩 루프 #{loop_count}")
                
                # 각 코인 분석 및 거래
                for symbol in self.target_coins:
                    try:
                        # 분석 실행
                        analysis = self.analyze_coin(symbol)
                        
                        if analysis:
                            # 거래 실행
                            self.execute_trade(analysis)
                        
                        # API 호출 제한 대응
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"❌ {symbol} 처리 오류: {e}")
                
                logger.info(f"✅ 루프 #{loop_count} 완료")
                
                # 1분 대기
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("🛑 사용자 중단")
                break
            except Exception as e:
                logger.error(f"❌ 루프 오류: {e}")
                await asyncio.sleep(30)
    
    def stop(self):
        """봇 중지"""
        self.running = False
        logger.info("🛑 SimpleCoinBot 중지")

async def main():
    """메인 함수"""
    bot = SimpleCoinBot()
    
    try:
        await bot.run_trading_loop()
    except KeyboardInterrupt:
        logger.info("🛑 프로그램 종료")
    finally:
        bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
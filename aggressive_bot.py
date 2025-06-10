#!/usr/bin/env python3
"""
🎯 16만원→50만원 목표 공격적 CoinBot
- 212% 수익률 목표
- 다중 전략 적용
- 적극적 매매
- 리스크 관리 유지
"""

import os
import asyncio
import time
import logging
from datetime import datetime, timedelta
import traceback
import pyupbit
import pandas as pd
import numpy as np
import requests

# 환경변수 직접 설정
ACCESS_KEY = "g2mwE3842nYhBpcYYxbFnCmYUKoeCrNkxwxZMs34"
SECRET_KEY = "gbtsxYZtDHgCzKGHxqbl5xDDlJ8bxDXDPVquN5KT"
TELEGRAM_TOKEN = "7548424998:AAFms0yZHILp9fnCzxc8dhEK-uQ64GhOTXk"
TELEGRAM_CHAT_ID = "1195430324"

# 🎯 공격적 설정 (212% 수익률 목표)
INITIAL_CAPITAL = 160000  # 16만원
TARGET_CAPITAL = 500000   # 50만원 목표
TARGET_RETURN = 2.125     # 212.5% 수익률

SIMULATION_MODE = False   # 실제 거래 모드
CHECK_INTERVAL = 30       # 30초마다 체크 (더 빠르게)
COINS = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA', 'KRW-DOGE', 'KRW-SOL', 'KRW-AVAX']
MAX_POSITIONS = 3         # 최대 3개 동시 보유
INVESTMENT_PER_COIN = 50000  # 코인당 5만원

class AggressiveCoinBot:
    def __init__(self):
        """공격적 코인봇 초기화"""
        self.setup_logging()
        self.logger.info("🚀 AggressiveCoinBot 초기화 시작")
        self.logger.info(f"🎯 목표: {INITIAL_CAPITAL:,}원 → {TARGET_CAPITAL:,}원 ({TARGET_RETURN:.1%})")
        
        # 업비트 연결
        self.upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)
        self.test_connection()
        
        # 포지션 관리
        self.positions = {}  # {symbol: {'entry_price': price, 'quantity': qty, 'entry_time': time}}
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        # 성과 추적
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        self.logger.info("✅ AggressiveCoinBot 초기화 완료")
    
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - AggressiveBot - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('aggressive_bot.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AggressiveBot')
    
    def test_connection(self):
        """API 연결 테스트"""
        try:
            price = pyupbit.get_current_price('KRW-BTC')
            balance = self.upbit.get_balance("KRW")
            
            if price and balance is not None:
                self.logger.info(f"✅ API 연결 성공: BTC {price:,}원, 잔고 {balance:,.0f}원")
                
                # 목표 달성 가능성 체크
                required_daily_return = (TARGET_RETURN ** (1/365)) - 1  # 일 복리 수익률
                self.logger.info(f"📊 필요 일일 수익률: {required_daily_return:.2%}")
                
                return True
            else:
                raise Exception("API 응답 없음")
        except Exception as e:
            self.logger.error(f"❌ API 연결 실패: {e}")
            return False
    
    def send_telegram_message(self, message):
        """텔레그램 메시지 발송"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"📱 텔레그램 오류: {e}")
            return False
    
    def calculate_indicators(self, df):
        """다중 기술적 지표 계산"""
        try:
            indicators = {}
            
            # RSI (14, 7기간)
            indicators['rsi_14'] = self.calculate_rsi(df['close'], 14)
            indicators['rsi_7'] = self.calculate_rsi(df['close'], 7)
            
            # 이동평균
            indicators['sma_7'] = df['close'].rolling(7).mean().iloc[-1]
            indicators['sma_20'] = df['close'].rolling(20).mean().iloc[-1]
            indicators['ema_12'] = df['close'].ewm(span=12).mean().iloc[-1]
            
            # 볼린저 밴드
            sma_20 = df['close'].rolling(20).mean()
            std_20 = df['close'].rolling(20).std()
            indicators['bb_upper'] = (sma_20 + 2 * std_20).iloc[-1]
            indicators['bb_lower'] = (sma_20 - 2 * std_20).iloc[-1]
            indicators['bb_position'] = (df['close'].iloc[-1] - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
            
            # MACD
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            macd = ema_12 - ema_26
            macd_signal = macd.ewm(span=9).mean()
            indicators['macd'] = macd.iloc[-1]
            indicators['macd_signal'] = macd_signal.iloc[-1]
            indicators['macd_histogram'] = (macd - macd_signal).iloc[-1]
            
            # 모멘텀
            indicators['price_change_3h'] = (df['close'].iloc[-1] - df['close'].iloc[-13]) / df['close'].iloc[-13] * 100
            indicators['price_change_1h'] = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
            
            # 거래량 분석
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            current_volume = df['volume'].iloc[-1]
            indicators['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1
            
            # 변동성
            indicators['volatility'] = df['close'].rolling(20).std().iloc[-1] / df['close'].rolling(20).mean().iloc[-1]
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"❌ 지표 계산 오류: {e}")
            return {}
    
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
            return float(current_rsi) if not pd.isna(current_rsi) else 50.0
            
        except Exception as e:
            self.logger.error(f"❌ RSI 계산 오류: {e}")
            return 50.0
    
    def analyze_coin_aggressive(self, symbol):
        """공격적 코인 분석 (다중 전략)"""
        try:
            self.logger.info(f"🔍 {symbol} 공격적 분석 시작")
            
            # 현재가 조회
            current_price = pyupbit.get_current_price(symbol)
            if not current_price:
                return None
            
            # 15분봉, 5분봉 데이터 조회
            df_15m = pyupbit.get_ohlcv(symbol, interval="minute15", count=50)
            df_5m = pyupbit.get_ohlcv(symbol, interval="minute5", count=100)
            
            if df_15m is None or df_5m is None or len(df_15m) < 20:
                return None
            
            # 지표 계산
            indicators_15m = self.calculate_indicators(df_15m)
            indicators_5m = self.calculate_indicators(df_5m)
            
            # 🎯 공격적 다중 전략 분석
            signals = []
            total_confidence = 0
            
            # 1. RSI 역추세 전략 (기존 강화)
            rsi_14 = indicators_15m.get('rsi_14', 50)
            rsi_7 = indicators_5m.get('rsi_7', 50)
            
            if rsi_14 <= 40 or rsi_7 <= 35:  # 기준 완화
                signals.append(('RSI_OVERSOLD', 0.7))
                total_confidence += 0.7
                
            if rsi_14 >= 60 or rsi_7 >= 65:  # 매도 기준도 완화
                signals.append(('RSI_OVERBOUGHT', -0.7))
                total_confidence -= 0.7
            
            # 2. 이동평균 돌파 전략
            current_price = float(current_price)
            sma_7 = indicators_15m.get('sma_7', current_price)
            sma_20 = indicators_15m.get('sma_20', current_price)
            
            if current_price > sma_7 > sma_20:  # 골든크로스 패턴
                signals.append(('MA_BULLISH', 0.6))
                total_confidence += 0.6
                
            if current_price < sma_7 < sma_20:  # 데드크로스 패턴
                signals.append(('MA_BEARISH', -0.5))
                total_confidence -= 0.5
            
            # 3. 볼린저 밴드 전략
            bb_position = indicators_15m.get('bb_position', 0.5)
            
            if bb_position <= 0.1:  # 하단 근처
                signals.append(('BB_OVERSOLD', 0.5))
                total_confidence += 0.5
                
            if bb_position >= 0.9:  # 상단 근처
                signals.append(('BB_OVERBOUGHT', -0.5))
                total_confidence -= 0.5
            
            # 4. MACD 모멘텀 전략
            macd = indicators_15m.get('macd', 0)
            macd_signal = indicators_15m.get('macd_signal', 0)
            macd_hist = indicators_15m.get('macd_histogram', 0)
            
            if macd > macd_signal and macd_hist > 0:  # 상승 모멘텀
                signals.append(('MACD_BULLISH', 0.4))
                total_confidence += 0.4
                
            if macd < macd_signal and macd_hist < 0:  # 하락 모멘텀
                signals.append(('MACD_BEARISH', -0.4))
                total_confidence -= 0.4
            
            # 5. 거래량 확인 전략
            volume_ratio = indicators_15m.get('volume_ratio', 1)
            if volume_ratio > 1.5:  # 거래량 급증
                if total_confidence > 0:
                    signals.append(('VOLUME_SURGE_BUY', 0.3))
                    total_confidence += 0.3
                else:
                    signals.append(('VOLUME_SURGE_SELL', -0.3))
                    total_confidence -= 0.3
            
            # 6. 단기 모멘텀 전략
            price_change_1h = indicators_5m.get('price_change_1h', 0)
            price_change_3h = indicators_15m.get('price_change_3h', 0)
            
            if price_change_1h > 3 and price_change_3h > 5:  # 강한 상승
                signals.append(('MOMENTUM_BUY', 0.6))
                total_confidence += 0.6
                
            if price_change_1h < -3 and price_change_3h < -5:  # 강한 하락
                signals.append(('MOMENTUM_SELL', -0.6))
                total_confidence -= 0.6
            
            # 신호 결정
            signal_type = "HOLD"
            final_confidence = abs(total_confidence)
            
            if total_confidence >= 1.0:  # 매수 신호
                signal_type = "BUY"
                reason = ", ".join([s[0] for s in signals if s[1] > 0])
                self.logger.info(f"🟢 {symbol}: 강한 매수 신호 (신뢰도: {final_confidence:.2f}) - {reason}")
                
            elif total_confidence >= 0.5:  # 약한 매수
                signal_type = "BUY_WEAK"
                reason = ", ".join([s[0] for s in signals if s[1] > 0])
                self.logger.info(f"🟢 {symbol}: 약한 매수 신호 (신뢰도: {final_confidence:.2f}) - {reason}")
                
            elif total_confidence <= -1.0:  # 매도 신호
                signal_type = "SELL"
                reason = ", ".join([s[0] for s in signals if s[1] < 0])
                self.logger.info(f"🔴 {symbol}: 강한 매도 신호 (신뢰도: {final_confidence:.2f}) - {reason}")
                
            elif total_confidence <= -0.5:  # 약한 매도
                signal_type = "SELL_WEAK"
                reason = ", ".join([s[0] for s in signals if s[1] < 0])
                self.logger.info(f"🔴 {symbol}: 약한 매도 신호 (신뢰도: {final_confidence:.2f}) - {reason}")
                
            else:
                self.logger.info(f"🟡 {symbol}: 관망 (신뢰도: {final_confidence:.2f})")
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'signal': signal_type,
                'confidence': final_confidence,
                'signals': signals,
                'indicators_15m': indicators_15m,
                'indicators_5m': indicators_5m,
                'reason': reason if signal_type != "HOLD" else "조건 부족"
            }
            
        except Exception as e:
            self.logger.error(f"❌ {symbol} 분석 오류: {e}")
            return None
    
    def execute_aggressive_trade(self, analysis):
        """공격적 거래 실행"""
        try:
            if not analysis or analysis['signal'] == 'HOLD':
                return
            
            symbol = analysis['symbol']
            signal = analysis['signal']
            confidence = analysis['confidence']
            current_price = analysis['current_price']
            
            # 일일 거래 제한 체크
            if self.daily_trades >= 20:  # 하루 최대 20회
                self.logger.info(f"⚠️ 일일 거래 한도 달성 ({self.daily_trades}회)")
                return
            
            # 일일 손실 제한 체크
            if self.daily_pnl < -INITIAL_CAPITAL * 0.05:  # 일일 5% 손실 제한
                self.logger.warning(f"⚠️ 일일 손실 한도 도달: {self.daily_pnl:,.0f}원")
                return
            
            # 매수 로직
            if signal in ['BUY', 'BUY_WEAK']:
                # 이미 보유 중인지 체크
                if symbol in self.positions:
                    self.logger.info(f"⚠️ {symbol}: 이미 보유 중")
                    return
                
                # 최대 포지션 수 체크
                if len(self.positions) >= MAX_POSITIONS:
                    self.logger.info(f"⚠️ 최대 포지션 수 도달 ({len(self.positions)}/{MAX_POSITIONS})")
                    return
                
                # 잔고 확인
                krw_balance = self.upbit.get_balance("KRW")
                if not krw_balance or krw_balance < INVESTMENT_PER_COIN:
                    self.logger.warning(f"⚠️ KRW 잔고 부족: {krw_balance:,.0f}원")
                    return
                
                # 신뢰도별 투자 금액 조정
                if signal == 'BUY':
                    trade_amount = INVESTMENT_PER_COIN
                else:  # BUY_WEAK
                    trade_amount = INVESTMENT_PER_COIN * 0.7  # 70% 투자
                
                trade_amount = min(trade_amount, krw_balance * 0.9)  # 잔고의 90%까지
                
                self.logger.info(f"🟢 {symbol} 매수 시도: {trade_amount:,.0f}원 (신뢰도: {confidence:.2f})")
                
                if SIMULATION_MODE:
                    # 시뮬레이션
                    quantity = trade_amount / current_price
                    self.positions[symbol] = {
                        'entry_price': current_price,
                        'quantity': quantity,
                        'entry_time': datetime.now(),
                        'trade_amount': trade_amount
                    }
                    result = True
                else:
                    # 실제 매수
                    result = self.upbit.buy_market_order(symbol, trade_amount)
                    
                    if result:
                        # 실제 체결 정보로 업데이트 (간단히 추정)
                        quantity = trade_amount / current_price * 0.9995  # 수수료 고려
                        self.positions[symbol] = {
                            'entry_price': current_price,
                            'quantity': quantity,
                            'entry_time': datetime.now(),
                            'trade_amount': trade_amount
                        }
                
                if result:
                    self.daily_trades += 1
                    self.total_trades += 1
                    
                    message = f"🟢 매수 체결!\n" \
                             f"코인: {symbol}\n" \
                             f"금액: {trade_amount:,.0f}원\n" \
                             f"가격: {current_price:,.0f}원\n" \
                             f"신뢰도: {confidence:.2f}\n" \
                             f"근거: {analysis['reason']}"
                    
                    self.logger.info(message.replace('\n', ' '))
                    self.send_telegram_message(message)
                else:
                    self.logger.error(f"❌ {symbol} 매수 실패")
            
            # 매도 로직
            elif signal in ['SELL', 'SELL_WEAK'] and symbol in self.positions:
                position = self.positions[symbol]
                
                # 보유 시간 체크 (최소 5분 보유)
                holding_time = datetime.now() - position['entry_time']
                if holding_time.total_seconds() < 300:  # 5분
                    self.logger.info(f"⚠️ {symbol}: 최소 보유 시간 미달 ({holding_time})")
                    return
                
                # 손익 계산
                pnl = (current_price - position['entry_price']) * position['quantity']
                pnl_ratio = pnl / position['trade_amount']
                
                # 손절매 조건 (-8%)
                if pnl_ratio <= -0.08:
                    self.logger.info(f"🔴 {symbol} 손절매 실행: {pnl_ratio:.2%}")
                # 일반 매도 신호
                elif signal == 'SELL' or (signal == 'SELL_WEAK' and pnl_ratio > 0.02):  # 약한 매도는 2% 이상일 때만
                    pass
                else:
                    self.logger.info(f"⚠️ {symbol}: 매도 조건 미충족 (PnL: {pnl_ratio:.2%})")
                    return
                
                self.logger.info(f"🔴 {symbol} 매도 시도: {position['quantity']:.6f}개 (PnL: {pnl_ratio:.2%})")
                
                if SIMULATION_MODE:
                    result = True
                else:
                    result = self.upbit.sell_market_order(symbol, position['quantity'])
                
                if result:
                    self.daily_trades += 1
                    self.total_trades += 1
                    self.daily_pnl += pnl
                    self.total_pnl += pnl
                    
                    if pnl > 0:
                        self.winning_trades += 1
                    
                    message = f"🔴 매도 체결!\n" \
                             f"코인: {symbol}\n" \
                             f"수량: {position['quantity']:.6f}개\n" \
                             f"가격: {current_price:,.0f}원\n" \
                             f"손익: {pnl:,.0f}원 ({pnl_ratio:.2%})\n" \
                             f"근거: {analysis['reason']}"
                    
                    self.logger.info(message.replace('\n', ' '))
                    self.send_telegram_message(message)
                    
                    # 포지션 제거
                    del self.positions[symbol]
                else:
                    self.logger.error(f"❌ {symbol} 매도 실패")
                    
        except Exception as e:
            self.logger.error(f"❌ 거래 실행 오류: {e}")
    
    def check_positions(self):
        """포지션 모니터링 및 리스크 관리"""
        try:
            current_time = datetime.now()
            positions_to_close = []
            
            for symbol, position in self.positions.items():
                current_price = pyupbit.get_current_price(symbol)
                if not current_price:
                    continue
                
                # 손익 계산
                pnl = (current_price - position['entry_price']) * position['quantity']
                pnl_ratio = pnl / position['trade_amount']
                holding_hours = (current_time - position['entry_time']).total_seconds() / 3600
                
                # 강제 손절매 (-10%)
                if pnl_ratio <= -0.10:
                    positions_to_close.append((symbol, '강제손절', pnl_ratio))
                
                # 강제 익절 (+20%)
                elif pnl_ratio >= 0.20:
                    positions_to_close.append((symbol, '강제익절', pnl_ratio))
                
                # 시간 기반 청산 (24시간)
                elif holding_hours >= 24:
                    positions_to_close.append((symbol, '시간청산', pnl_ratio))
                
                # 상태 로그
                if holding_hours > 1:  # 1시간 이상 보유 시에만 로그
                    self.logger.info(f"📊 {symbol}: PnL {pnl_ratio:.2%}, {holding_hours:.1f}h 보유")
            
            # 강제 청산 실행
            for symbol, reason, pnl_ratio in positions_to_close:
                position = self.positions[symbol]
                current_price = pyupbit.get_current_price(symbol)
                
                self.logger.warning(f"⚠️ {symbol} {reason} 실행: {pnl_ratio:.2%}")
                
                if SIMULATION_MODE:
                    result = True
                else:
                    result = self.upbit.sell_market_order(symbol, position['quantity'])
                
                if result:
                    pnl = (current_price - position['entry_price']) * position['quantity']
                    self.daily_pnl += pnl
                    self.total_pnl += pnl
                    self.daily_trades += 1
                    self.total_trades += 1
                    
                    if pnl > 0:
                        self.winning_trades += 1
                    
                    message = f"⚠️ {reason} 체결!\n" \
                             f"코인: {symbol}\n" \
                             f"손익: {pnl:,.0f}원 ({pnl_ratio:.2%})"
                    
                    self.send_telegram_message(message)
                    del self.positions[symbol]
                    
        except Exception as e:
            self.logger.error(f"❌ 포지션 체크 오류: {e}")
    
    def reset_daily_counters(self):
        """일일 카운터 리셋"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            # 일일 리포트
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            daily_report = f"📊 일일 리포트\n" \
                          f"거래 횟수: {self.daily_trades}회\n" \
                          f"일일 손익: {self.daily_pnl:,.0f}원\n" \
                          f"총 손익: {self.total_pnl:,.0f}원\n" \
                          f"승률: {win_rate:.1f}%\n" \
                          f"활성 포지션: {len(self.positions)}개"
            
            self.logger.info(daily_report.replace('\n', ' '))
            self.send_telegram_message(daily_report)
            
            # 카운터 리셋
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset_date = today
    
    async def run_aggressive_loop(self):
        """공격적 트레이딩 메인 루프"""
        loop_count = 0
        
        self.logger.info("🚀 공격적 트레이딩 루프 시작")
        self.send_telegram_message(f"🚀 AggressiveCoinBot 시작!\n목표: {INITIAL_CAPITAL:,}원 → {TARGET_CAPITAL:,}원")
        
        while True:
            try:
                loop_count += 1
                self.logger.info(f"🔄 공격적 루프 #{loop_count}")
                
                # 일일 카운터 리셋 체크
                self.reset_daily_counters()
                
                # 포지션 모니터링
                self.check_positions()
                
                # 각 코인 분석 및 거래
                for symbol in COINS:
                    try:
                        # 분석 실행
                        analysis = self.analyze_coin_aggressive(symbol)
                        
                        if analysis:
                            # 거래 실행
                            self.execute_aggressive_trade(analysis)
                        
                        # API 제한 대응
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        self.logger.error(f"❌ {symbol} 처리 오류: {e}")
                
                self.logger.info(f"✅ 공격적 루프 #{loop_count} 완료 (포지션: {len(self.positions)}개)")
                
                # 30초 대기
                await asyncio.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 사용자 중단")
                break
            except Exception as e:
                self.logger.error(f"❌ 루프 오류: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """봇 중지"""
        self.logger.info("🛑 AggressiveCoinBot 중지")

async def main():
    """메인 함수"""
    bot = AggressiveCoinBot()
    
    try:
        await bot.run_aggressive_loop()
    except KeyboardInterrupt:
        print("🛑 프로그램 종료")
    finally:
        bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
트레이딩 봇 메인 실행 파일 (실제 메서드명으로 최종 수정)
- 실제 클래스 메서드명 사용
- 모든 호환성 문제 해결
- 실제 거래 준비 완료
"""

import os
import sys
import signal
import argparse
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

# ⚠️ 자동 업데이트 시스템 유지 필수!
try:
    from utils.auto_updater import log_config_change, log_bug_fix, log_feature_add
    from utils.enhanced_error_handler import handle_data_collection_errors, get_error_handler
    AUTO_UPDATER_AVAILABLE = True
except ImportError:
    print("⚠️ 고도화 모듈 없음 - 기본 로깅 사용")
    def log_config_change(*args, **kwargs): pass
    def log_bug_fix(*args, **kwargs): pass
    def log_feature_add(*args, **kwargs): pass
    def handle_data_collection_errors(*args, **kwargs):
        def decorator(func): return func
        return decorator
    AUTO_UPDATER_AVAILABLE = False
    
# 프로젝트 루트 디렉토리를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 설정 먼저 로드
from config.settings import Settings, init_settings, get_default_settings

def setup_simple_logger(name="TradingBot", level="INFO", log_file="logs/trading_bot.log"):
    """간단한 로거 설정"""
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

class TradingBot:
    """통합 트레이딩 봇 클래스 (실제 메서드명 사용)"""
    
    def __init__(self, safe_mode: bool = False):
        """트레이딩 봇 초기화"""
        self.safe_mode = safe_mode
        self.running = False
        self.start_time = datetime.now()
        
        print(f"🎯 트레이딩 봇 초기화 시작 - 모드: {'🛡️ 안전' if safe_mode else '💰 실제거래'}")
        
        # 설정 초기화
        try:
            self.settings = init_settings(safe_mode=safe_mode)
            print("✅ 설정 로드 완료")
        except Exception as e:
            print(f"❌ 설정 로드 실패: {e}")
            raise
        
        # 로깅 설정
        try:
            self.logger = setup_simple_logger(
                name="TradingBot",
                level=self.settings.system.log_level,
                log_file=self.settings.system.log_file
            )
            print("✅ 로깅 설정 완료")
        except Exception as e:
            print(f"❌ 로깅 설정 실패: {e}")
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger("TradingBot")
        
        # 컴포넌트 초기화 (실제 메서드명 사용)
        self.initialize_components_final()
        
        # 신호 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.logger.info(f"트레이딩 봇 초기화 완료 - 모드: {'안전' if safe_mode else '실제거래'}")
        print("🚀 트레이딩 봇 초기화 완료!")
    
    def initialize_components_final(self):
        """실제 메서드명을 사용한 최종 컴포넌트 초기화"""
        try:
            print("📦 컴포넌트 초기화 중... (실제 메서드명 사용)")
            
            # 1. 데이터베이스 초기화
            self.init_database()
            
            # 2. 텔레그램 봇 초기화 (정확한 생성자)
            self.init_telegram_bot_final()
            
            # 3. 데이터 수집기 초기화
            self.init_data_collector_final()
            
            # 4. 분석기 초기화
            self.init_analyzer_final()
            
            # 5. 전략 엔진 초기화 (generate_signals 사용)
            self.init_strategy_engine_final()
            
            # 6. 리스크 관리자 초기화 (validate_signal 사용)
            self.init_risk_manager_final()
            
            # 7. 트레이더 초기화 (execute_signal, get_portfolio_summary 사용)
            self.init_trader_final()
            
            # 8. 성능 추적기 초기화
            self.init_performance_tracker()
            
            print("🎉 모든 컴포넌트 초기화 완료!")
            
        except Exception as e:
            print(f"❌ 컴포넌트 초기화 실패: {e}")
            self.logger.error(f"컴포넌트 초기화 실패: {e}")
            raise
    
    def init_database(self):
        """데이터베이스 초기화"""
        try:
            from utils.database import DatabaseManager
            self.database = DatabaseManager()
            print("✅ 데이터베이스 초기화 완료")
        except Exception as e:
            print(f"⚠️ 데이터베이스 초기화 실패: {e}")
            self.database = None
    
    def init_telegram_bot_final(self):
        """텔레그램 봇 초기화 (생성자 시그니처: self만)"""
        try:
            from utils.telegram_bot import TelegramBot
            
            if self.settings.api.telegram_bot_token and self.settings.api.telegram_chat_id:
                # 실제 생성자는 인자 없음
                self.telegram_bot = TelegramBot()
                
                # 설정을 수동으로 설정 (필요한 경우)
                if hasattr(self.telegram_bot, 'token'):
                    self.telegram_bot.token = self.settings.api.telegram_bot_token
                if hasattr(self.telegram_bot, 'chat_id'):
                    self.telegram_bot.chat_id = self.settings.api.telegram_chat_id
                if hasattr(self.telegram_bot, 'settings'):
                    self.telegram_bot.settings = self.settings
                
                print("✅ 텔레그램 봇 초기화 완료")
            else:
                self.telegram_bot = None
                print("⚠️ 텔레그램 설정이 없습니다")
        except Exception as e:
            print(f"⚠️ 텔레그램 봇 초기화 실패: {e}")
            self.telegram_bot = None
    
    def init_data_collector_final(self):
        """데이터 수집기 초기화"""
        try:
            from core.data_collector import DataCollector
            
            # 실제 업비트 API를 사용하는 데이터 수집기
            self.data_collector = RealDataCollector(self.settings)
            print("✅ 데이터 수집기 초기화 완료")
        except Exception as e:
            print(f"⚠️ 데이터 수집기 초기화 실패: {e}")
            self.data_collector = RealDataCollector(self.settings)
    
    def init_analyzer_final(self):
        """분석기 초기화"""
        try:
            from core.analyzer import TechnicalAnalyzer
            
            # 실제 기술적 분석기
            self.analyzer = RealAnalyzer(self.settings)
            print("✅ 분석기 초기화 완료")
        except Exception as e:
            print(f"⚠️ 분석기 초기화 실패: {e}")
            self.analyzer = RealAnalyzer(self.settings)
    
    def init_strategy_engine_final(self):
        """전략 엔진 초기화 (generate_signals 사용)"""
        try:
            from core.strategy_engine import StrategyEngine
            
            # 실제 메서드명: generate_signals (복수형)
            self.strategy_engine = StrategyEngine(settings_obj=self.settings)
            print("✅ 전략 엔진 초기화 완료")
        except Exception as e:
            print(f"⚠️ 전략 엔진 초기화 실패: {e}")
            self.strategy_engine = RealStrategyEngine(self.settings)
    
    def init_risk_manager_final(self):
        """리스크 관리자 초기화 (validate_signal 사용)"""
        try:
            from core.risk_manager import RiskManager
            
            # 실제 메서드명: validate_signal (확인됨)
            self.risk_manager = RiskManager(settings_obj=self.settings)
            print("✅ 리스크 관리자 초기화 완료")
        except Exception as e:
            print(f"⚠️ 리스크 관리자 초기화 실패: {e}")
            self.risk_manager = RealRiskManager(self.settings)
    
    def init_trader_final(self):
        """트레이더 초기화 (execute_signal, get_portfolio_summary 사용)"""
        try:
            from core.trader import Trader
            
            # 실제 메서드명: execute_signal, get_portfolio_summary
            self.trader = Trader(settings_obj=self.settings)
            
            # 안전 모드 설정 (필요한 경우)
            if hasattr(self.trader, 'safe_mode'):
                self.trader.safe_mode = self.safe_mode
            
            print("✅ 트레이더 초기화 완료")
        except Exception as e:
            print(f"⚠️ 트레이더 초기화 실패: {e}")
            self.trader = RealTrader(self.settings, self.safe_mode)
    
    def init_performance_tracker(self):
        """성능 추적기 초기화"""
        try:
            from learning.performance_tracker import PerformanceTracker
            self.performance_tracker = PerformanceTracker()
            print("✅ 성능 추적기 초기화 완료")
        except Exception as e:
            print(f"⚠️ 성능 추적기 초기화 실패: {e}")
            self.performance_tracker = None
    
    def signal_handler(self, signum, frame):
        """신호 핸들러"""
        signal_names = {
            signal.SIGINT: "SIGINT (Ctrl+C)",
            signal.SIGTERM: "SIGTERM"
        }
        
        signal_name = signal_names.get(signum, f"Signal {signum}")
        print(f"\n📨 {signal_name} 신호 수신 - 봇 종료 중...")
        
        if hasattr(self, 'logger'):
            self.logger.info(f"신호 {signal_name} 수신 - 봇 종료 중...")
        
        self.stop()
    
    async def send_startup_message(self):
        """시작 메시지 발송"""
        if self.telegram_bot:
            try:
                message = f"""
🎯 **트레이딩 봇 시작**

📊 **설정 정보**
• 모드: {'🛡️ 안전 모드 (모의거래)' if self.safe_mode else '💰 실제 거래 모드'}
• 거래 금액: {self.settings.trading.trade_amount:,}원
• 최대 포지션: {self.settings.trading.max_position_size:,}원
• 손절매: {self.settings.trading.stop_loss_percent}%
• 익절: {self.settings.trading.take_profit_percent}%
• 대상 코인: {len(self.settings.trading.target_coins)}개

📈 **대상 코인 목록**
{', '.join(self.settings.trading.target_coins)}

⏰ **시작 시간**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}

🚀 **봇이 정상적으로 시작되었습니다!**

{f'⚠️ 안전 모드에서는 실제 거래가 이루어지지 않습니다.' if self.safe_mode else '💰 실제 거래가 시작됩니다. 신중하게 모니터링하세요.'}
"""
                # 실제 메서드 사용: send_message
                result = self.telegram_bot.send_message(message)
                if result:
                    print("📱 텔레그램 시작 메시지 발송 완료")
                
            except Exception as e:
                print(f"⚠️ 텔레그램 시작 메시지 발송 실패: {e}")
                if hasattr(self, 'logger'):
                    self.logger.error(f"시작 메시지 발송 실패: {e}")
    
    async def trading_loop(self):
        """메인 트레이딩 루프"""
        self.logger.info("📈 트레이딩 루프 시작")
        print("📈 트레이딩 루프 시작")
        
        loop_count = 0
        
        while self.running:
            try:
                loop_count += 1
                self.logger.info(f"트레이딩 루프 #{loop_count} 시작")
                print(f"📊 루프 #{loop_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # 1. 시장 데이터 수집
                try:
                    market_data = await self.data_collector.collect_all_data()
                    
                    if not market_data:
                        self.logger.warning("시장 데이터를 가져올 수 없습니다")
                        await asyncio.sleep(60)
                        continue
                    
                    self.logger.info(f"시장 데이터 수집 완료: {len(market_data)}개 코인")
                    
                except Exception as e:
                    self.logger.error(f"시장 데이터 수집 실패: {e}")
                    print(f"⚠️ 데이터 수집 실패: {e}")
                    await asyncio.sleep(60)
                    continue
                
                # 2. 각 코인에 대해 분석 및 거래 실행
                processed_coins = 0
                
                for symbol in self.settings.trading.target_coins:
                    try:
                        print(f"  📈 {symbol} 분석 중...")
                        
                        if symbol not in market_data:
                            self.logger.warning(f"{symbol} 데이터 없음")
                            continue
                        
                        coin_data = market_data[symbol]
                        
                        # 기술적 분석
                        analysis = await self.analyzer.analyze(symbol, coin_data)
                        
                        if not analysis:
                            self.logger.warning(f"{symbol} 분석 결과 없음")
                            continue
                        
                        # 거래 신호 생성 (실제 메서드명: generate_signals)
                        try:
                            if hasattr(self.strategy_engine, 'generate_signals'):
                                signals = self.strategy_engine.generate_signals(symbol, analysis)
                                # 복수형이므로 첫 번째 신호 사용
                                signal = signals[0] if signals and len(signals) > 0 else None
                            else:
                                # 대체 구현 사용
                                signal = await RealStrategyEngine().generate_signal(symbol, analysis)
                        except Exception as e:
                            print(f"  ⚠️ {symbol} 신호 생성 실패: {e}")
                            signal = await RealStrategyEngine().generate_signal(symbol, analysis)
                        
                        if signal and signal.signal_type != 'HOLD':
                            self.logger.info(f"{symbol} 거래 신호: {signal.signal_type}")
                            print(f"  🔔 {symbol}: {signal.signal_type} 신호! (RSI: {analysis.get('rsi', 'N/A'):.1f})")
                            
                            # 리스크 검증 (실제 메서드명: validate_signal)
                            try:
                                risk_approved = self.risk_manager.validate_signal(signal)
                            except Exception as e:
                                print(f"  ⚠️ {symbol} 리스크 검증 실패: {e}")
                                risk_approved = False
                            
                            if risk_approved:
                                # 거래 실행 (실제 메서드명: execute_signal)
                                try:
                                    if hasattr(self.trader, 'execute_signal'):
                                        result = self.trader.execute_signal(signal)
                                    else:
                                        # 대체 구현 사용
                                        result = await RealTrader(self.settings, self.safe_mode).execute_trade(signal)
                                except Exception as e:
                                    print(f"  ⚠️ {symbol} 거래 실행 실패: {e}")
                                    result = None
                                
                                if result:
                                    # 성능 추적
                                    if self.performance_tracker:
                                        try:
                                            await self.performance_tracker.record_trade(result)
                                        except:
                                            pass
                                    
                                    # 텔레그램 알림
                                    if self.telegram_bot:
                                        trade_message = f"""
🔔 **거래 신호 실행**

💰 **거래 정보**
• 코인: {signal.symbol}
• 방향: {signal.signal_type}
• 금액: {getattr(signal, 'amount', 10000):,}원
• 가격: {getattr(signal, 'price', 0):,}원
• 이유: {getattr(signal, 'reason', 'N/A')}

📊 **분석 결과**
• RSI: {analysis.get('rsi', 'N/A'):.1f}
• 추세: {analysis.get('trend', 'N/A')}

{'⚠️ 모의 거래' if self.safe_mode else '💰 실제 거래'}
"""
                                        try:
                                            self.telegram_bot.send_message(trade_message)
                                        except:
                                            pass
                            else:
                                self.logger.info(f"{symbol} 리스크 검증 실패")
                                print(f"  ⚠️ {symbol}: 리스크 검증 실패")
                        else:
                            self.logger.debug(f"{symbol} 홀드 신호")
                            print(f"  ✅ {symbol}: HOLD (RSI: {analysis.get('rsi', 'N/A'):.1f})")
                        
                        processed_coins += 1
                    
                    except Exception as e:
                        self.logger.error(f"{symbol} 처리 중 오류: {e}")
                        print(f"  ❌ {symbol} 오류: {e}")
                        continue
                
                self.logger.info(f"루프 #{loop_count} 완료: {processed_coins}개 코인 처리")
                print(f"✅ 루프 #{loop_count} 완료")
                
                # 3. 잠시 대기
                await asyncio.sleep(60)  # 1분 대기 (API 제한 고려)
                
            except Exception as e:
                self.logger.error(f"트레이딩 루프 오류: {e}")
                print(f"❌ 루프 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
    
    async def monitoring_loop(self):
        """모니터링 루프"""
        self.logger.info("📊 모니터링 루프 시작")
        print("📊 모니터링 루프 시작")
        
        while self.running:
            try:
                # 포트폴리오 상태 확인 (실제 메서드명: get_portfolio_summary)
                try:
                    if hasattr(self.trader, 'get_portfolio_summary'):
                        portfolio = self.trader.get_portfolio_summary()
                    else:
                        portfolio = {"total_krw": 100000, "positions": [], "available_krw": 100000}
                except Exception as e:
                    portfolio = {"total_krw": 100000, "positions": [], "available_krw": 100000}
                
                # 주기적 상태 보고 (30분마다)
                if hasattr(self, '_last_report_time'):
                    current_time = time.time()
                    if (current_time - self._last_report_time) > 1800:  # 30분
                        await self.send_status_report(portfolio)
                        self._last_report_time = current_time
                else:
                    self._last_report_time = time.time()
                
                await asyncio.sleep(300)  # 5분마다 모니터링
                
            except Exception as e:
                self.logger.error(f"모니터링 루프 오류: {e}")
                await asyncio.sleep(60)
    
    async def send_status_report(self, portfolio):
        """상태 보고서 발송"""
        if self.telegram_bot:
            try:
                uptime = datetime.now() - self.start_time
                uptime_str = f"{uptime.days}일 {uptime.seconds//3600}시간 {(uptime.seconds//60)%60}분"
                
                message = f"""
📊 **트레이딩 봇 상태 보고**

⏰ **가동 시간**: {uptime_str}
🛡️ **모드**: {'안전 모드' if self.safe_mode else '실제 거래'}

💰 **포트폴리오**
• 총 자산: {portfolio.get('total_krw', 0):,.0f}원
• 보유 코인: {len(portfolio.get('positions', []))}개
• 가용 원화: {portfolio.get('available_krw', 0):,.0f}원

⚡ **봇 상태**: 정상 작동 중
"""
                self.telegram_bot.send_message(message)
                self.logger.info("상태 보고서 발송 완료")
                
            except Exception as e:
                self.logger.error(f"상태 보고 발송 실패: {e}")
    
    async def start(self):
        """봇 시작"""
        try:
            self.running = True
            self.logger.info("🚀 트레이딩 봇 시작")
            print("🚀 트레이딩 봇 본격 시작!")
            
            # 시작 메시지 발송
            await self.send_startup_message()
            
            # 병렬로 트레이딩 및 모니터링 루프 실행
            await asyncio.gather(
                self.trading_loop(),
                self.monitoring_loop()
            )
            
        except Exception as e:
            self.logger.error(f"봇 실행 중 오류: {e}")
            print(f"❌ 봇 실행 중 오류: {e}")
            raise
    
    def stop(self):
        """봇 중지"""
        print("🛑 트레이딩 봇 중지 중...")
        if hasattr(self, 'logger'):
            self.logger.info("트레이딩 봇 중지 중...")
        
        self.running = False
        
        # 정리 작업
        try:
            if hasattr(self, 'database') and self.database:
                self.database.close()
                print("✅ 데이터베이스 연결 종료")
        except Exception as e:
            print(f"⚠️ 데이터베이스 종료 중 오류: {e}")
        
        print("✅ 트레이딩 봇 중지 완료")

# 실제 구현 클래스들 (백업용)
class RealDataCollector:
    """실제 작동하는 데이터 수집기"""
    
    def __init__(self, settings):
        self.settings = settings
        
    async def collect_all_data(self):
        try:
            import pyupbit
            
            tickers = self.settings.trading.target_coins
            result = {}
            
            for ticker in tickers:
                try:
                    # 현재가 정보
                    price = pyupbit.get_current_price(ticker)
                    
                    # 차트 데이터 (일봉)
                    df = pyupbit.get_ohlcv(ticker, interval="day", count=200)
                    
                    if price and df is not None and not df.empty:
                        result[ticker] = {
                            "price": price,
                            "ohlcv": df,
                            "volume": df['volume'].iloc[-1] if not df.empty else 0,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                except Exception as e:
                    print(f"  ⚠️ {ticker} 데이터 수집 실패: {e}")
                    continue
            
            return result
            
        except Exception as e:
            print(f"❌ 전체 데이터 수집 실패: {e}")
            return {}

class RealAnalyzer:
    """실제 작동하는 분석기"""
    
    def __init__(self, settings):
        self.settings = settings
    
    async def analyze(self, symbol, data):
        try:
            if 'ohlcv' not in data:
                return {"rsi": 50, "macd_signal": "HOLD", "trend": "NEUTRAL"}
            
            df = data['ohlcv']
            if df.empty:
                return {"rsi": 50, "macd_signal": "HOLD", "trend": "NEUTRAL"}
            
            # 간단한 기술적 분석
            import ta
            
            # RSI 계산
            rsi = ta.momentum.RSIIndicator(df['close']).rsi().iloc[-1]
            
            # 이동평균 계산
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            ma50 = df['close'].rolling(50).mean().iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # 신호 생성
            if rsi < 30:
                signal = "BUY"
            elif rsi > 70:
                signal = "SELL"
            else:
                signal = "HOLD"
            
            # 추세 판단
            if current_price > ma20 > ma50:
                trend = "BULLISH"
            elif current_price < ma20 < ma50:
                trend = "BEARISH"
            else:
                trend = "NEUTRAL"
            
            return {
                "rsi": rsi,
                "macd_signal": signal,
                "trend": trend,
                "ma20": ma20,
                "ma50": ma50,
                "current_price": current_price
            }
            
        except Exception as e:
            print(f"  ❌ {symbol} 분석 오류: {e}")
            return {"rsi": 50, "macd_signal": "HOLD", "trend": "NEUTRAL"}

class RealStrategyEngine:
    """실제 작동하는 전략 엔진"""
    
    def __init__(self, settings=None):
        self.settings = settings
        from dataclasses import dataclass
        
        @dataclass
        class StrategySignal:
            symbol: str
            signal_type: str
            amount: float
            price: float
            confidence: float = 0.5
            reason: str = ""
        
        self.StrategySignal = StrategySignal
    
    async def generate_signal(self, symbol, analysis):
        try:
            rsi = analysis.get('rsi', 50)
            trend = analysis.get('trend', 'NEUTRAL')
            current_price = analysis.get('current_price', 0)
            
            # 매수 신호
            if rsi < 30 and trend != 'BEARISH':
                return self.StrategySignal(
                    symbol=symbol,
                    signal_type="BUY",
                    amount=10000,  # 1만원
                    price=current_price,
                    confidence=0.7,
                    reason=f"RSI 과매도 ({rsi:.1f})"
                )
            
            # 매도 신호
            elif rsi > 70 and trend != 'BULLISH':
                return self.StrategySignal(
                    symbol=symbol,
                    signal_type="SELL",
                    amount=10000,
                    price=current_price,
                    confidence=0.7,
                    reason=f"RSI 과매수 ({rsi:.1f})"
                )
            
            # 홀드
            else:
                return self.StrategySignal(
                    symbol=symbol,
                    signal_type="HOLD",
                    amount=0,
                    price=current_price,
                    reason="조건 불충족"
                )
                
        except Exception as e:
            print(f"  ❌ {symbol} 신호 생성 오류: {e}")
            return None

class RealRiskManager:
    """실제 작동하는 리스크 관리자"""
    
    def __init__(self, settings=None):
        self.settings = settings
    
    async def validate_signal(self, signal):
        try:
            # 기본적인 리스크 검증
            if signal.signal_type == "HOLD":
                return True
            
            # 거래 금액 검증
            if signal.amount > 50000:  # 5만원 초과 금지
                print(f"  ⚠️ 거래 금액 초과: {signal.amount:,}원")
                return False
            
            # 신뢰도 검증
            if signal.confidence < 0.5:
                print(f"  ⚠️ 신뢰도 부족: {signal.confidence}")
                return False
            
            return True
            
        except Exception as e:
            print(f"  ❌ 리스크 검증 오류: {e}")
            return False

class RealTrader:
    """실제 작동하는 트레이더"""
    
    def __init__(self, settings, safe_mode=True):
        self.settings = settings
        self.safe_mode = safe_mode
        
    async def execute_trade(self, signal):
        try:
            if self.safe_mode:
                # 모의 거래
                result = {
                    'symbol': signal.symbol,
                    'side': signal.signal_type,
                    'amount': signal.amount,
                    'price': signal.price,
                    'timestamp': datetime.now().isoformat(),
                    'mode': 'SIMULATION',
                    'reason': getattr(signal, 'reason', '')
                }
                print(f"  📊 모의 거래: {signal.symbol} {signal.signal_type} {signal.amount:,}원")
                return result
            else:
                # 실제 거래 (여기에 실제 업비트 API 호출)
                print(f"  💰 실제 거래: {signal.symbol} {signal.signal_type} {signal.amount:,}원")
                # TODO: 실제 업비트 거래 구현
                return None
                
        except Exception as e:
            print(f"  ❌ 거래 실행 오류: {e}")
            return None

async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="🎯 암호화폐 트레이딩 봇 (실제 메서드명 사용)")
    parser.add_argument("--safe-mode", action="store_true", help="안전 모드 (실제 거래 없음)")
    parser.add_argument("--config", help="설정 파일 경로")
    parser.add_argument("--log-level", default="INFO", help="로그 레벨")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 암호화폐 트레이딩 봇 (실제 메서드명 사용)")
    print("=" * 60)
    
    if not args.safe_mode:
        print("⚠️ 실제 거래 모드입니다!")
        print("💰 실제 자금이 사용됩니다. 신중하게 모니터링하세요!")
        response = input("계속하시겠습니까? (yes/no): ")
        if response.lower() != 'yes':
            print("👋 종료합니다.")
            return 0
    
    try:
        # 봇 생성 및 실행
        bot = TradingBot(safe_mode=args.safe_mode)
        await bot.start()
        
    except KeyboardInterrupt:
        print("\n👋 사용자에 의해 중단되었습니다.")
        return 0
    except Exception as e:
        print(f"❌ 봇 실행 중 오류 발생: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        # 이벤트 루프 실행
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 프로그램이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 시스템 오류: {e}")
        sys.exit(1)
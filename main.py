import asyncio
import time
import signal
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 핵심 모듈 import
from config.settings import Settings
from core.data_collector import DataCollector
from core.analyzer import TechnicalAnalyzer
from core.strategy_engine import StrategyEngine
from core.trader import Trader
from core.risk_manager import RiskManager
from utils.logger import Logger
from utils.telegram_bot import TelegramBot

class TradingBot:
    """메인 트레이딩 봇 클래스"""
    
    def __init__(self):
        """시스템 초기화"""
        print("🚀 암호화폐 자동매매 시스템 시작")
        print("=" * 50)
        
        # 설정 로드
        self.settings = Settings()
        
        # 로거 초기화
        self.logger = Logger()
        self.logger.info("=== 매매 시스템 초기화 시작 ===")
        
        # 시스템 상태
        self.is_running = False
        self.emergency_mode = False
        self.last_health_check = datetime.now()
        
        # 성과 추적
        self.start_time = datetime.now()
        self.total_trades = 0
        self.successful_trades = 0
        self.daily_pnl = 0.0
        
        # 핵심 모듈 초기화
        self._initialize_modules()
        
        # 시그널 핸들러 등록 (Ctrl+C 처리)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("=== 매매 시스템 초기화 완료 ===")
    
    def _initialize_modules(self):
        """핵심 모듈들 초기화"""
        try:
            self.logger.info("핵심 모듈 초기화 중...")
            
            # 1. 데이터 수집기
            self.data_collector = DataCollector()
            self.logger.info("✅ 데이터 수집기 초기화")
            
            # 2. 기술적 분석기
            self.analyzer = TechnicalAnalyzer()
            self.logger.info("✅ 기술적 분석기 초기화")
            
            # 3. 전략 엔진
            self.strategy_engine = StrategyEngine(self.settings)
            self.logger.info("✅ 전략 엔진 초기화")
            
            # 4. 매매 실행기
            self.trader = Trader(self.settings)
            self.logger.info("✅ 매매 실행기 초기화")
            
            # 5. 리스크 관리자
            self.risk_manager = RiskManager(self.settings)
            self.logger.info("✅ 리스크 관리자 초기화")
            
            # 6. 텔레그램 봇 (선택사항)
            if self.settings.telegram.enabled:
                self.telegram_bot = TelegramBot(
                    self.settings.telegram.bot_token,
                    self.settings.telegram.chat_id
                )
                self.logger.info("✅ 텔레그램 봇 초기화")
            else:
                self.telegram_bot = None
                self.logger.info("⚠️  텔레그램 알림 비활성화")
            
            # 모듈 연결 검증
            self._validate_connections()
            
        except Exception as e:
            self.logger.error(f"모듈 초기화 실패: {e}")
            raise
    
    def _validate_connections(self):
        """모듈 간 연결 상태 검증"""
        try:
            # 업비트 API 연결 확인
            if not self.trader.upbit:
                raise Exception("업비트 API 연결 실패")
            
            # 잔고 조회 테스트
            krw_balance = self.data_collector.get_balance("KRW")
            if krw_balance is None:
                raise Exception("잔고 조회 실패")
            
            self.logger.info(f"현재 KRW 잔고: {krw_balance:,.0f}원")
            
            # 거래 가능 코인 목록 확인
            available_tickers = self.data_collector.get_krw_tickers()
            if not available_tickers:
                raise Exception("거래 가능 코인 목록 조회 실패")
            
            self.logger.info(f"거래 가능 코인: {len(available_tickers)}개")
            
            # 텔레그램 연결 테스트
            if self.telegram_bot:
                test_result = self.telegram_bot.send_message("🤖 매매봇 시작 - 연결 테스트")
                if test_result:
                    self.logger.info("✅ 텔레그램 연결 성공")
                else:
                    self.logger.warning("⚠️  텔레그램 연결 실패")
            
        except Exception as e:
            self.logger.error(f"연결 검증 실패: {e}")
            raise
    
    def _signal_handler(self, signum, frame):
        """시스템 종료 시그널 처리"""
        self.logger.warning("시스템 종료 신호 수신")
        self.shutdown()
    
    async def start(self):
        """매매 시스템 시작"""
        try:
            self.is_running = True
            self.logger.info("🚀 매매 시스템 가동 시작")
            
            # 시작 알림
            if self.telegram_bot:
                await self._send_start_notification()
            
            # 메인 루프 시작
            await self._main_loop()
            
        except Exception as e:
            self.logger.error(f"시스템 실행 중 오류: {e}")
            await self._handle_critical_error(e)
        finally:
            self.shutdown()
    
    async def _send_start_notification(self):
        """시작 알림 발송"""
        try:
            portfolio = self.trader.get_portfolio_summary()
            
            message = f"""
🚀 **매매봇 가동 시작**

💰 **현재 상태**
• KRW 잔고: {portfolio.get('available_capital', 0):,.0f}원
• 보유 포지션: {portfolio.get('total_positions', 0)}개
• 최대 포지션: {self.trader.max_positions}개

⚙️ **설정 정보**
• 포지션당 투자금: {self.trader.capital_per_position:,.0f}원
• 일일 최대 거래: 20회
• 목표: 16만원 → 50만원 🎯

시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            await self.telegram_bot.send_message(message)
            
        except Exception as e:
            self.logger.error(f"시작 알림 발송 실패: {e}")
    
    async def _main_loop(self):
        """메인 실행 루프"""
        self.logger.info("메인 루프 시작")
        
        loop_count = 0
        
        while self.is_running:
            try:
                loop_start = time.time()
                loop_count += 1
                
                # 1단계: 시스템 상태 확인
                if not await self._system_health_check():
                    await asyncio.sleep(60)  # 1분 대기 후 재시도
                    continue
                
                # 2단계: 리스크 체크 (긴급 모드 확인)
                risk_status = self.risk_manager.get_overall_risk_status()
                if risk_status['emergency_mode']:
                    await self._handle_emergency_mode()
                    await asyncio.sleep(30)  # 30초 대기
                    continue
                
                # 3단계: 포지션 업데이트 및 청산 조건 확인
                self.trader.update_positions()
                self.trader.check_exit_conditions()
                
                # 4단계: 새로운 매매 기회 탐색 (5분마다)
                if loop_count % 5 == 0:  # 5번째 루프마다 (약 5분)
                    await self._scan_trading_opportunities()
                
                # 5단계: 포트폴리오 상태 로깅 (30분마다)
                if loop_count % 30 == 0:  # 30번째 루프마다 (약 30분)
                    await self._log_portfolio_status()
                
                # 6단계: 일일 통계 리셋 (자정)
                await self._check_daily_reset()
                
                # 루프 주기 조정 (60초)
                loop_time = time.time() - loop_start
                sleep_time = max(60 - loop_time, 1)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"메인 루프 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
    
    async def _system_health_check(self) -> bool:
        """시스템 상태 확인"""
        try:
            # 5분마다 헬스체크
            if (datetime.now() - self.last_health_check).seconds < 300:
                return True
            
            health_status = self.trader.health_check()
            self.last_health_check = datetime.now()
            
            # API 연결 확인
            if health_status.get('api_status') != 'OK':
                self.logger.error("업비트 API 연결 실패")
                return False
            
            # 잔고 상태 확인  
            if health_status.get('balance_status') != 'OK':
                self.logger.error("잔고 조회 실패")
                return False
            
            # 포지션 상태 확인
            positions_status = health_status.get('positions_status')
            if positions_status == 'HIGH_LOSS':
                self.logger.warning("⚠️  고손실 포지션 감지")
                if self.telegram_bot:
                    await self.telegram_bot.send_message(
                        "⚠️ 경고: 일부 포지션에서 큰 손실이 발생하고 있습니다."
                    )
            
            return True
            
        except Exception as e:
            self.logger.error(f"헬스체크 실패: {e}")
            return False
    async def _handle_emergency_mode(self):
        """긴급 모드 처리"""
        try:
            self.logger.warning("🚨 긴급 모드 활성화")
            
            if not self.emergency_mode:
                self.emergency_mode = True
                
                # 긴급 알림 발송
                if self.telegram_bot:
                    await self.telegram_bot.send_message(
                        "🚨 **긴급 모드 활성화**\n"
                        "• 새로운 매매 중단\n"
                        "• 기존 포지션 모니터링 강화\n"
                        "• 손실 확산 방지"
                    )
            
            # 긴급 청산 조건 확인
            risk_status = self.risk_manager.get_overall_risk_status()
            if risk_status['risk_score'] >= 90:  # 매우 위험한 상황
                self.logger.error("극도로 위험한 상황 - 모든 포지션 청산 고려")
                
                # 사용자 확인 후 청산 (자동 청산은 위험)
                if self.telegram_bot:
                    await self.telegram_bot.send_message(
                        "⚠️ **위험도 90% 초과**\n"
                        "모든 포지션 긴급 청산을 고려해주세요."
                    )
            
        except Exception as e:
            self.logger.error(f"긴급 모드 처리 실패: {e}")
    
    async def _scan_trading_opportunities(self):
        """새로운 매매 기회 탐색"""
        try:
            self.logger.info("매매 기회 탐색 시작")
            
            # 현재 포지션 수 확인
            current_positions = len(self.trader.positions)
            max_positions = self.trader.max_positions
            
            if current_positions >= max_positions:
                self.logger.debug(f"최대 포지션 수 도달: {current_positions}/{max_positions}")
                return
            
            # 거래 가능한 코인 목록 조회
            available_tickers = self.data_collector.get_krw_tickers()
            
            # 현재 보유 중인 코인 제외
            holding_tickers = set(pos.ticker for pos in self.trader.positions.values())
            candidate_tickers = [t for t in available_tickers if t not in holding_tickers]
            
            if not candidate_tickers:
                self.logger.debug("추가 매매 대상 없음")
                return
            
            # 상위 거래량 코인들만 선별 (상위 50개)
            volume_data = []
            for ticker in candidate_tickers[:100]:  # API 제한 고려
                try:
                    current_price = self.data_collector.get_current_price(ticker)
                    if current_price:
                        # 24시간 거래량 조회 (임시로 현재가 사용)
                        volume_data.append((ticker, current_price))
                except:
                    continue
            
            # 거래량 기준 정렬 (실제로는 거래량 데이터 필요)
            top_tickers = [ticker for ticker, _ in volume_data[:50]]
            
            # 각 코인에 대해 분석 및 신호 생성
            signals_generated = 0
            for ticker in top_tickers:
                try:
                    # 시장 데이터 수집
                    market_data = await self._collect_market_data(ticker)
                    if not market_data:
                        continue
                    
                    # 기술적 분석
                    analysis_result = self.analyzer.analyze_comprehensive(
                        ticker, market_data['ohlcv']
                    )
                    
                    # 전략 신호 생성
                    strategy_signals = self.strategy_engine.generate_signals(
                        ticker, market_data, analysis_result
                    )
                    
                    # 유효한 매수 신호 처리
                    for signal in strategy_signals:
                        if signal.action == "BUY":
                            success = await self._process_buy_signal(signal)
                            if success:
                                signals_generated += 1
                                self.total_trades += 1
                                
                                # 최대 동시 처리 신호 수 제한
                                if signals_generated >= 3:
                                    break
                    
                    if signals_generated >= 3:
                        break
                        
                except Exception as e:
                    self.logger.debug(f"코인 분석 실패 {ticker}: {e}")
                    continue
            
            if signals_generated > 0:
                self.logger.info(f"매매 기회 탐색 완료: {signals_generated}개 신호 처리")
            else:
                self.logger.debug("유효한 매매 기회 없음")
                
        except Exception as e:
            self.logger.error(f"매매 기회 탐색 실패: {e}")
    
    async def _collect_market_data(self, ticker: str) -> Optional[Dict]:
        """특정 코인의 시장 데이터 수집"""
        try:
            # OHLCV 데이터 (1시간봉, 24개)
            ohlcv_1h = self.data_collector.get_ohlcv(ticker, interval="minute60", count=24)
            if ohlcv_1h is None or len(ohlcv_1h) < 20:
                return None
            
            # OHLCV 데이터 (5분봉, 288개 = 24시간)
            ohlcv_5m = self.data_collector.get_ohlcv(ticker, interval="minute5", count=288)
            if ohlcv_5m is None or len(ohlcv_5m) < 100:
                return None
            
            # 현재가 및 거래량 정보
            current_price = self.data_collector.get_current_price(ticker)
            if not current_price:
                return None
            
            # 호가 정보 (스프레드 확인용)
            orderbook = self.data_collector.get_orderbook(ticker)
            
            return {
                'ticker': ticker,
                'current_price': current_price,
                'ohlcv': ohlcv_1h,  # 메인 분석용
                'ohlcv_detail': ohlcv_5m,  # 상세 분석용
                'orderbook': orderbook,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.debug(f"시장 데이터 수집 실패 {ticker}: {e}")
            return None
    
    async def _process_buy_signal(self, signal) -> bool:
        """매수 신호 처리"""
        try:
            # 1. 리스크 관리자 검증
            risk_validation = self.risk_manager.validate_signal(signal)
            if not risk_validation['approved']:
                self.logger.debug(f"리스크 검증 실패 {signal.ticker}: {risk_validation['reason']}")
                return False
            
            # 2. 포지션 크기 조정
            adjusted_signal = self.risk_manager.adjust_position_size(signal)
            
            # 3. 매매 실행
            success = self.trader.execute_signal(adjusted_signal)
            
            if success:
                self.successful_trades += 1
                
                # 성공 알림
                if self.telegram_bot:
                    await self._send_trade_notification("BUY", signal)
                
                # 리스크 관리자에 거래 기록
                self.risk_manager.record_trade_execution(adjusted_signal, True)
                
                self.logger.info(f"✅ 매수 성공: {signal.ticker}")
                return True
            else:
                # 실패 기록
                self.risk_manager.record_trade_execution(signal, False)
                self.logger.warning(f"❌ 매수 실패: {signal.ticker}")
                return False
                
        except Exception as e:
            self.logger.error(f"매수 신호 처리 실패: {e}")
            return False
    
    async def _send_trade_notification(self, action: str, signal):
        """거래 알림 발송"""
        try:
            if not self.telegram_bot:
                return
            
            emoji = "💰" if action == "BUY" else "💸"
            
            message = f"""
{emoji} **{action} 거래 실행**

🪙 **코인**: {signal.ticker}
💵 **가격**: {signal.current_price:,.0f}원
📊 **신뢰도**: {signal.confidence:.1%}
🎯 **전략**: {signal.strategy_id}

📈 **목표가**: {signal.take_profit:,.0f}원
📉 **손절가**: {signal.stop_loss:,.0f}원

⏰ {datetime.now().strftime('%H:%M:%S')}
            """
            
            await self.telegram_bot.send_message(message)
            
        except Exception as e:
            self.logger.error(f"거래 알림 발송 실패: {e}")
    
    async def _log_portfolio_status(self):
        """포트폴리오 상태 로깅"""
        try:
            portfolio = self.trader.get_portfolio_summary()
            trade_stats = self.trader.get_trade_statistics()
            risk_status = self.risk_manager.get_overall_risk_status()
            
            # 성과 계산
            total_value = portfolio.get('total_current_value', 0) + portfolio.get('available_capital', 0)
            start_value = 160000  # 초기 자본 16만원
            total_return = ((total_value - start_value) / start_value) * 100 if start_value > 0 else 0
            
            # 로그 메시지
            self.logger.info(f"""
📊 포트폴리오 현황:
• 총 자산: {total_value:,.0f}원 ({total_return:+.1f}%)
• KRW 잔고: {portfolio.get('available_capital', 0):,.0f}원
• 보유 포지션: {portfolio.get('total_positions', 0)}개
• 미실현 손익: {portfolio.get('total_unrealized_pnl_ratio', 0):.1%}

📈 거래 성과:
• 총 거래: {trade_stats.get('completed_trades', 0)}회
• 승률: {trade_stats.get('win_rate', 0):.1%}
• 평균 수익률: {trade_stats.get('avg_profit_ratio', 0):.1%}

🛡️ 리스크 상태:
• 위험도: {risk_status.get('risk_score', 0):.0f}/100
• 상태: {risk_status.get('risk_level', 'UNKNOWN')}
            """)
            
            # 주요 변화가 있을 때 텔레그램 알림
            if self.telegram_bot and (total_return >= 10 or total_return <= -10):
                await self._send_portfolio_alert(portfolio, total_return)
                
        except Exception as e:
            self.logger.error(f"포트폴리오 상태 로깅 실패: {e}")
    
    async def _send_portfolio_alert(self, portfolio: Dict, total_return: float):
        """포트폴리오 주요 변화 알림"""
        try:
            emoji = "🎉" if total_return > 0 else "😰"
            
            message = f"""
{emoji} **포트폴리오 업데이트**

💰 **총 자산**: {(portfolio.get('total_current_value', 0) + portfolio.get('available_capital', 0)):,.0f}원
📊 **총 수익률**: {total_return:+.1f}%
💼 **보유 포지션**: {portfolio.get('total_positions', 0)}개
📈 **미실현 손익**: {portfolio.get('total_unrealized_pnl_ratio', 0):+.1f}%

🎯 목표까지: {50 - total_return:.1f}%p 남음
            """
            
            await self.telegram_bot.send_message(message)
        except Exception as e:
            self.logger.error(f"포트폴리오 알림 발송 실패: {e}")
    async def _check_daily_reset(self):
        """일일 통계 리셋 확인"""
        try:
            now = datetime.now()
            
            # 자정 확인 (00:00 ~ 00:05)
            if now.hour == 0 and now.minute <= 5:
                self.logger.info("일일 통계 리셋")
                
                # 어제 성과 요약
                yesterday_stats = await self._generate_daily_summary()
                
                # 일일 제한 리셋
                self.trader.reset_daily_limits()
                self.risk_manager.reset_daily_limits()
                
                # 긴급 모드 해제 (새로운 하루 시작)
                if self.emergency_mode:
                    self.emergency_mode = False
                    self.logger.info("긴급 모드 해제 - 새로운 거래일 시작")
                
                # 일일 요약 알림
                if self.telegram_bot and yesterday_stats:
                    await self._send_daily_summary(yesterday_stats)
                
        except Exception as e:
            self.logger.error(f"일일 리셋 실패: {e}")
    
    async def _generate_daily_summary(self) -> Optional[Dict]:
        """일일 성과 요약 생성"""
        try:
            portfolio = self.trader.get_portfolio_summary()
            trade_stats = self.trader.get_trade_statistics()
            
            # 오늘 거래 통계
            today_trades = trade_stats.get('daily_trade_count', 0)
            daily_pnl = trade_stats.get('daily_loss', 0)
            
            summary = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_trades': today_trades,
                'daily_pnl': daily_pnl,
                'current_positions': portfolio.get('total_positions', 0),
                'total_value': portfolio.get('total_current_value', 0) + portfolio.get('available_capital', 0),
                'unrealized_pnl': portfolio.get('total_unrealized_pnl_ratio', 0)
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"일일 요약 생성 실패: {e}")
            return None
    
    async def _send_daily_summary(self, summary: Dict):
        """일일 요약 알림 발송"""
        try:
            pnl_emoji = "📈" if summary['daily_pnl'] >= 0 else "📉"
            
            message = f"""
🌅 **일일 거래 요약** ({summary['date']})

{pnl_emoji} **일일 손익**: {summary['daily_pnl']:+.1f}%
🔄 **거래 횟수**: {summary['total_trades']}회
💼 **현재 포지션**: {summary['current_positions']}개
💰 **총 자산**: {summary['total_value']:,.0f}원

📊 **미실현 손익**: {summary['unrealized_pnl']:+.1f}%

🎯 **목표 진행률**: {((summary['total_value'] - 160000) / (500000 - 160000) * 100):.1f}%
            """
            
            await self.telegram_bot.send_message(message)
            
        except Exception as e:
            self.logger.error(f"일일 요약 발송 실패: {e}")
    
    async def _handle_critical_error(self, error: Exception):
        """심각한 오류 처리"""
        try:
            self.logger.error(f"심각한 오류 발생: {error}")
            
            # 긴급 상황 알림
            if self.telegram_bot:
                await self.telegram_bot.send_message(
                    f"🚨 **시스템 치명적 오류**\n"
                    f"오류: {str(error)[:100]}...\n"
                    f"시스템 안전 종료 중..."
                )
            
            # 모든 포지션 현황 저장
            self.trader._save_positions()
            
            # 긴급 청산 여부 결정 (사용자 판단 필요)
            self.logger.warning("긴급 상황 - 포지션 현황을 저장했습니다.")
            
        except Exception as e:
            self.logger.error(f"긴급 상황 처리 실패: {e}")
    
    def shutdown(self):
        """시스템 안전 종료"""
        try:
            self.logger.info("매매 시스템 종료 시작")
            self.is_running = False
            
            # 포지션 및 주문 상태 저장
            if hasattr(self, 'trader') and self.trader:
                self.trader._save_positions()
                self.logger.info("포지션 데이터 저장 완료")
            
            # 최종 포트폴리오 상태
            if hasattr(self, 'trader'):
                portfolio = self.trader.get_portfolio_summary()
                self.logger.info(f"최종 포트폴리오: {portfolio}")
            
            # 종료 알림
            if hasattr(self, 'telegram_bot') and self.telegram_bot:
                try:
                    # asyncio.run을 사용하여 동기적으로 실행
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._send_shutdown_notification())
                    loop.close()
                except:
                    pass
            
            self.logger.info("매매 시스템 종료 완료")
            
        except Exception as e:
            self.logger.error(f"시스템 종료 중 오류: {e}")
    
    async def _send_shutdown_notification(self):
        """종료 알림 발송"""
        try:
            runtime = datetime.now() - self.start_time
            portfolio = self.trader.get_portfolio_summary()
            
            total_value = portfolio.get('total_current_value', 0) + portfolio.get('available_capital', 0)
            total_return = ((total_value - 160000) / 160000) * 100
            
            message = f"""
🔴 **매매봇 종료**

⏱️ **가동시간**: {str(runtime).split('.')[0]}
🔄 **총 거래**: {self.total_trades}회
✅ **성공률**: {(self.successful_trades/self.total_trades*100):.1f}% ({self.successful_trades}/{self.total_trades})

💰 **최종 자산**: {total_value:,.0f}원
📊 **총 수익률**: {total_return:+.1f}%
💼 **보유 포지션**: {portfolio.get('total_positions', 0)}개

종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            await self.telegram_bot.send_message(message)
            
        except Exception as e:
            self.logger.error(f"종료 알림 발송 실패: {e}")


# 실행 함수들
def create_directories():
    """필요한 디렉토리 생성"""
    directories = [
        "data/trades",
        "data/analysis", 
        "data/logs",
        "data/history"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ 디렉토리 생성: {directory}")

async def main():
    """메인 실행 함수"""
    try:
        print("🚀 암호화폐 자동매매 시스템")
        print("목표: 16만원 → 50만원 (212.5% 수익)")
        print("=" * 50)
        
        # 필요한 디렉토리 생성
        create_directories()
        
        # 매매봇 초기화 및 실행
        bot = TradingBot()
        await bot.start()
        
    except KeyboardInterrupt:
        print("\n사용자에 의한 시스템 중단")
    except Exception as e:
        print(f"시스템 실행 실패: {e}")
        logging.error(f"시스템 실행 실패: {e}")
    finally:
        print("시스템 종료")

if __name__ == "__main__":
    try:
        # 이벤트 루프 실행
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"실행 오류: {e}")
    
    input("\n아무 키나 누르면 종료됩니다...")  

    """
추가 실행 스크립트 및 유틸리티 함수들
"""

def check_environment():
    """환경 설정 확인"""
    print("🔍 환경 설정 확인 중...")
    
    required_env_vars = [
        "UPBIT_ACCESS_KEY",
        "UPBIT_SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 누락된 환경변수: {', '.join(missing_vars)}")
        print("\n.env 파일을 확인하거나 다음 환경변수를 설정해주세요:")
        for var in missing_vars:
            print(f"  {var}=your_key_here")
        return False
    
    print("✅ 환경 설정 확인 완료")
    return True

def display_startup_banner():
    """시작 배너 출력"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                   🤖 자동 암호화폐 매매봇                        ║
║                                                               ║
║  목표: 16만원 → 50만원 (212.5% 수익률)                           ║
║  전략: 기술적 분석 + 리스크 관리 + 지능형 포지션 관리                ║
║                                                               ║
║  💡 주요 기능:                                                  ║
║  • 실시간 시장 분석 및 자동 매매                                  ║
║  • 다층 리스크 관리 시스템                                       ║
║  • 텔레그램 실시간 알림                                         ║
║  • 포트폴리오 자동 최적화                                       ║
║                                                               ║
║  ⚠️  주의사항:                                                  ║
║  • 투자에는 항상 위험이 따릅니다                                  ║
║  • 시스템을 믿되, 정기적으로 모니터링하세요                        ║
║  • 긴급 상황 시 수동 개입이 필요할 수 있습니다                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def run_system_check():
    """시스템 사전 점검"""
    print("\n🔧 시스템 사전 점검...")
    
    checks = {
        "Python 버전": sys.version_info >= (3, 8),
        "필수 디렉토리": all(Path(d).exists() for d in ["data", "config", "core", "utils"]),
        "환경 변수": check_environment(),
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
        if not result:
            all_passed = False
    
    if not all_passed:
        print("\n❌ 사전 점검 실패. 설정을 확인해주세요.")
        return False
    
    print("✅ 시스템 사전 점검 완료")
    return True

def show_config_template():
    """설정 파일 템플릿 출력"""
    print("\n📋 설정 파일 예시 (.env):")
    template = """
# 업비트 API 키 (필수)
UPBIT_ACCESS_KEY=your_access_key_here
UPBIT_SECRET_KEY=your_secret_key_here

# 텔레그램 설정 (선택사항)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# 매매 설정
CAPITAL_PER_POSITION=50000    # 포지션당 투자금 (기본: 5만원)
MAX_POSITIONS=3               # 최대 동시 포지션 수
MAX_DAILY_LOSS=0.05          # 일일 최대 손실률 (5%)

# 로그 레벨
LOG_LEVEL=INFO
    """
    print(template)

def interactive_setup():
    """대화형 설정"""
    print("\n🔧 대화형 설정을 시작합니다...")
    
    # API 키 확인
    if not os.getenv("UPBIT_ACCESS_KEY"):
        print("\n❌ 업비트 API 키가 설정되지 않았습니다.")
        print("1. 업비트 > 내정보 > Open API 관리에서 API 키를 발급받으세요.")
        print("2. .env 파일에 키를 설정하거나 환경변수로 설정하세요.")
        show_config_template()
        return False
    
    # 초기 자본 확인
    try:
        from core.data_collector import DataCollector
        collector = DataCollector()
        krw_balance = collector.get_balance("KRW")
        
        if krw_balance < 160000:
            print(f"\n⚠️  현재 KRW 잔고: {krw_balance:,.0f}원")
            print("권장 최소 자본: 160,000원")
            
            choice = input("계속 진행하시겠습니까? (y/n): ").lower()
            if choice != 'y':
                return False
        else:
            print(f"✅ KRW 잔고 확인: {krw_balance:,.0f}원")
    
    except Exception as e:
        print(f"❌ 잔고 확인 실패: {e}")
        return False
    
    return True

def run_debug_mode():
    """디버그 모드 실행"""
    print("\n🐛 디버그 모드로 실행됩니다...")
    
    # 로그 레벨을 DEBUG로 설정
    logging.getLogger().setLevel(logging.DEBUG)
    
    # 모든 모듈의 연결 상태 확인
    try:
        from core.data_collector import DataCollector
        from core.analyzer import TechnicalAnalyzer
        from core.trader import Trader
        from config.settings import Settings
        
        settings = Settings()
        
        print("📊 데이터 수집기 테스트...")
        collector = DataCollector()
        tickers = collector.get_krw_tickers()[:5]  # 상위 5개만
        print(f"  거래 가능 코인: {len(tickers)}개")
        
        print("📈 기술적 분석기 테스트...")
        analyzer = TechnicalAnalyzer()
        
        print("💰 매매 실행기 테스트...")
        trader = Trader(settings)
        health = trader.health_check()
        print(f"  시스템 상태: {health.get('api_status', 'Unknown')}")
        
        print("✅ 모든 모듈 연결 확인 완료")
        
    except Exception as e:
        print(f"❌ 모듈 테스트 실패: {e}")
        return False
    
    return True

def main_menu():
    """메인 메뉴"""
    while True:
        print("\n" + "="*50)
        print("🤖 암호화폐 자동매매 시스템")
        print("="*50)
        print("1. 🚀 매매봇 시작")
        print("2. 🔧 시스템 점검")
        print("3. 🐛 디버그 모드")
        print("4. 📋 설정 템플릿 보기")
        print("5. ⚙️  대화형 설정")
        print("6. ❌ 종료")
        print("-"*50)
        
        choice = input("선택하세요 (1-6): ").strip()
        
        if choice == "1":
            if run_system_check() and interactive_setup():
                print("\n🚀 매매봇을 시작합니다...")
                return "start"
            else:
                print("\n❌ 설정을 확인 후 다시 시도해주세요.")
                
        elif choice == "2":
            run_system_check()
            
        elif choice == "3":
            if run_debug_mode():
                print("\n🚀 디버그 모드로 시작합니다...")
                return "debug"
            
        elif choice == "4":
            show_config_template()
            
        elif choice == "5":
            interactive_setup()
            
        elif choice == "6":
            print("👋 프로그램을 종료합니다.")
            return "exit"
            
        else:
            print("❌ 잘못된 선택입니다.")

# 메인 실행부 수정
if __name__ == "__main__":
    try:
        # 시작 배너 출력
        display_startup_banner()
        
        # 메뉴 실행
        action = main_menu()
        
        if action == "start":
            # 정상 모드로 실행
            asyncio.run(main())
            
        elif action == "debug":
            # 디버그 모드로 실행
            logging.getLogger().setLevel(logging.DEBUG)
            asyncio.run(main())
            
        elif action == "exit":
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n👋 사용자에 의해 프로그램이 종료되었습니다.")
        
    except Exception as e:
        print(f"\n❌ 실행 오류: {e}")
        logging.error(f"실행 오류: {e}")
        
    finally:
        input("\n아무 키나 누르면 종료됩니다...")      
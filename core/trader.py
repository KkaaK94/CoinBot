import pyupbit
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import uuid

from config.settings import settings
from core.data_collector import DataCollector
from core.strategy_engine import StrategySignal
from utils.logger import Logger

@dataclass
class Order:
    """주문 클래스"""
    order_id: str
    ticker: str
    order_type: str  # BUY, SELL
    order_side: str  # market, limit
    price: float
    quantity: float
    total_amount: float
    status: str  # PENDING, FILLED, CANCELLED, FAILED
    strategy_id: str
    created_at: datetime
    filled_at: Optional[datetime] = None
    upbit_uuid: Optional[str] = None

@dataclass
class Position:
    """포지션 클래스"""
    position_id: str
    ticker: str
    strategy_id: str
    entry_price: float
    quantity: float
    total_invested: float
    current_price: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_ratio: float
    
    # 청산 조건
    stop_loss: float
    take_profit: float
    
    # 메타 정보
    entry_time: datetime
    last_updated: datetime
    
    # 전략 정보
    strategy_name: str
    reasoning: str

class Trader:
    """매매 실행기 클래스"""
    
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.logger = Logger()
        self.data_collector = DataCollector()
        
        # 업비트 API 초기화
        self.upbit = None
        self._initialize_upbit()
        
        # 포지션 관리
        self.positions: Dict[str, Position] = {}
        self.order_history: List[Order] = []
        self.active_orders: Dict[str, Order] = {}
        
        # 거래 제한
        self.max_positions = settings_obj.trading.max_positions
        self.capital_per_position = settings_obj.trading.capital_per_position
        self.min_order_amount = settings_obj.trading.min_order_amount
        
        # 안전장치
        self.daily_trade_count = 0
        self.daily_loss = 0.0
        self.last_trade_time = {}
        
        # 포지션 데이터 로드
        self._load_positions()
        
        self.logger.info("매매 실행기 초기화 완료")
    
    def _initialize_upbit(self):
        """업비트 API 초기화"""
        try:
            if self.settings.upbit_access_key and self.settings.upbit_secret_key:
                self.upbit = pyupbit.Upbit(
                    self.settings.upbit_access_key,
                    self.settings.upbit_secret_key
                )
                
                # API 연결 테스트
                balance = self.upbit.get_balance("KRW")
                if balance is not None:
                    self.logger.info(f"업비트 API 연결 성공 - KRW 잔고: {float(balance):,.0f}원")
                else:
                    raise Exception("잔고 조회 실패")
            else:
                raise Exception("API 키가 설정되지 않음")
                
        except Exception as e:
            self.logger.error(f"업비트 API 초기화 실패: {e}")
            self.upbit = None
    def execute_signal(self, signal: StrategySignal) -> bool:
        """전략 신호 실행"""
        try:
            if not self.upbit:
                self.logger.error("업비트 API가 초기화되지 않음")
                return False
            
            # 거래 가능성 검증
            if not self._validate_trading_conditions(signal):
                return False
            
            if signal.action == "BUY":
                return self._execute_buy_order(signal)
            elif signal.action == "SELL":
                return self._execute_sell_order(signal)
            else:
                self.logger.debug(f"HOLD 신호 - 거래 없음: {signal.ticker}")
                return False
                
        except Exception as e:
            self.logger.error(f"신호 실행 실패: {e}")
            return False
    
    def _validate_trading_conditions(self, signal: StrategySignal) -> bool:
        """거래 조건 검증"""
        try:
            # 1. 기본 신호 검증
            if signal.confidence < 0.6:
                self.logger.debug(f"신뢰도 부족: {signal.confidence:.2f}")
                return False
            
            # 2. 포지션 수 제한
            if signal.action == "BUY" and len(self.positions) >= self.max_positions:
                self.logger.debug(f"최대 포지션 수 초과: {len(self.positions)}/{self.max_positions}")
                return False
            
            # 3. 중복 포지션 방지
            if signal.action == "BUY" and signal.ticker in [p.ticker for p in self.positions.values()]:
                self.logger.debug(f"이미 보유 중인 코인: {signal.ticker}")
                return False
            
            # 4. 최소 주문 금액
            if signal.action == "BUY" and self.capital_per_position < self.min_order_amount:
                self.logger.debug(f"최소 주문 금액 미달: {self.capital_per_position}")
                return False
            
            # 5. 일일 거래 제한
            if self.daily_trade_count >= 20:  # 일일 최대 20회
                self.logger.warning("일일 거래 횟수 초과")
                return False
            
            # 6. 연속 거래 방지 (같은 코인 3분 간격)
            last_trade = self.last_trade_time.get(signal.ticker, datetime.min)
            if (datetime.now() - last_trade).seconds < 180:
                self.logger.debug(f"연속 거래 방지: {signal.ticker}")
                return False
            
            # 7. 일일 손실 한도
            if self.daily_loss < -self.settings.trading.max_daily_loss:
                self.logger.warning(f"일일 손실 한도 초과: {self.daily_loss:.2%}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"거래 조건 검증 실패: {e}")
            return False
    def _execute_buy_order(self, signal: StrategySignal) -> bool:
        """매수 주문 실행"""
        try:
            ticker = signal.ticker
            amount = self.capital_per_position
            
            # 현재가 확인
            current_price = self.data_collector.get_current_price(ticker)
            if not current_price:
                self.logger.error(f"현재가 조회 실패: {ticker}")
                return False
            
            # KRW 잔고 확인
            krw_balance = self.data_collector.get_balance("KRW")
            if krw_balance < amount:
                self.logger.warning(f"KRW 잔고 부족: {krw_balance:,.0f} < {amount:,.0f}")
                return False
            
            # 주문 생성
            order = Order(
                order_id=str(uuid.uuid4()),
                ticker=ticker,
                order_type="BUY",
                order_side="market",
                price=current_price,
                quantity=amount / current_price,
                total_amount=amount,
                status="PENDING",
                strategy_id=signal.strategy_id,
                created_at=datetime.now()
            )
            
            # 업비트 주문 실행
            result = self.upbit.buy_market_order(ticker, amount)
            
            if result and result.get('uuid'):
                order.upbit_uuid = result['uuid']
                order.status = "FILLED"
                order.filled_at = datetime.now()
                
                # 주문 기록
                self.order_history.append(order)
                
                # 포지션 생성
                self._create_position(order, signal)
                
                # 거래 통계 업데이트
                self.daily_trade_count += 1
                self.last_trade_time[ticker] = datetime.now()
                
                # 로깅
                self.logger.trade_log("BUY", ticker, current_price, order.quantity, 
                                    f"{signal.strategy_id} 전략")
                
                self.logger.info(f"✅ 매수 성공: {ticker} {amount:,.0f}원 ({order.quantity:.6f})")
                
                return True
            else:
                order.status = "FAILED"
                self.order_history.append(order)
                self.logger.error(f"❌ 매수 실패: {ticker} - 주문 결과: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"매수 주문 실행 실패: {e}")
            return False
    
    def _create_position(self, order: Order, signal: StrategySignal):
        """포지션 생성"""
        try:
            position = Position(
                position_id=str(uuid.uuid4()),
                ticker=order.ticker,
                strategy_id=order.strategy_id,
                entry_price=order.price,
                quantity=order.quantity,
                total_invested=order.total_amount,
                current_price=order.price,
                current_value=order.total_amount,
                unrealized_pnl=0.0,
                unrealized_pnl_ratio=0.0,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                entry_time=order.filled_at,
                last_updated=datetime.now(),
                strategy_name=f"전략_{signal.strategy_id[:8]}",
                reasoning=signal.reasoning
            )
            
            self.positions[position.position_id] = position
            
            # 포지션 데이터 저장
            self._save_positions()
            
            self.logger.info(f"포지션 생성: {order.ticker} (ID: {position.position_id[:8]})")
            
        except Exception as e:
            self.logger.error(f"포지션 생성 실패: {e}") 
    def _execute_sell_order(self, signal: StrategySignal) -> bool:
        """매도 주문 실행 (기존 포지션 청산)"""
        try:
            ticker = signal.ticker
            
            # 해당 티커의 포지션 찾기
            position = self._find_position_by_ticker(ticker)
            if not position:
                self.logger.warning(f"매도할 포지션 없음: {ticker}")
                return False
            
            return self._close_position(position, "STRATEGY_SIGNAL", signal.reasoning)
            
        except Exception as e:
            self.logger.error(f"매도 주문 실행 실패: {e}")
            return False
    
    def _find_position_by_ticker(self, ticker: str) -> Optional[Position]:
        """티커로 포지션 찾기"""
        for position in self.positions.values():
            if position.ticker == ticker:
                return position
        return None

    def _close_position(self, position: Position, reason: str, detail: str = "") -> bool:
        """포지션 청산"""
        try:
            ticker = position.ticker
            
            # 실제 보유량 확인
            actual_balance = self.data_collector.get_balance(ticker)
            if actual_balance <= 0:
                self.logger.warning(f"실제 보유량 없음: {ticker}")
                self._remove_position(position.position_id)
                return False
            
            # 현재가 확인
            current_price = self.data_collector.get_current_price(ticker)
            if not current_price:
                self.logger.error(f"현재가 조회 실패: {ticker}")
                return False
            
            # 매도 주문 생성
            order = Order(
                order_id=str(uuid.uuid4()),
                ticker=ticker,
                order_type="SELL",
                order_side="market",
                price=current_price,
                quantity=actual_balance,
                total_amount=current_price * actual_balance,
                status="PENDING",
                strategy_id=position.strategy_id,
                created_at=datetime.now()
            )
            
            # 업비트 매도 주문 실행
            result = self.upbit.sell_market_order(ticker, actual_balance)
            
            if result and result.get('uuid'):
                order.upbit_uuid = result['uuid']
                order.status = "FILLED"
                order.filled_at = datetime.now()
                
                # 수익률 계산
                profit_amount = order.total_amount - position.total_invested
                profit_ratio = profit_amount / position.total_invested
                
                # 주문 기록
                self.order_history.append(order)
                
                # 거래 통계 업데이트
                self.daily_trade_count += 1
                self.daily_loss += profit_ratio
                self.last_trade_time[ticker] = datetime.now()
                
                # 포지션 제거
                self._remove_position(position.position_id)
                
                # 로깅
                self.logger.trade_log("SELL", ticker, current_price, actual_balance, 
                                    f"{reason}: {detail}")
                
                profit_emoji = "📈" if profit_ratio >= 0 else "📉"
                self.logger.info(f"✅ 매도 성공: {ticker} {profit_emoji} "
                               f"수익률: {profit_ratio:+.2%} ({profit_amount:+,.0f}원)")
                
                # 전략 성과 업데이트를 위한 결과 반환
                self._record_trade_result(position, order, profit_ratio)
                
                return True
            else:
                order.status = "FAILED"
                self.order_history.append(order)
                self.logger.error(f"❌ 매도 실패: {ticker} - 주문 결과: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"포지션 청산 실패: {e}")
            return False
    def _record_trade_result(self, position: Position, sell_order: Order, profit_ratio: float):
        """거래 결과 기록"""
        try:
            trade_result = {
                'position_id': position.position_id,
                'ticker': position.ticker,
                'strategy_id': position.strategy_id,
                'entry_time': position.entry_time.isoformat(),
                'exit_time': sell_order.filled_at.isoformat(),
                'duration_hours': (sell_order.filled_at - position.entry_time).total_seconds() / 3600,
                'entry_price': position.entry_price,
                'exit_price': sell_order.price,
                'quantity': position.quantity,
                'invested_amount': position.total_invested,
                'received_amount': sell_order.total_amount,
                'profit_amount': sell_order.total_amount - position.total_invested,
                'profit_ratio': profit_ratio,
                'reasoning': position.reasoning
            }
            
            # 거래 결과 파일에 저장
            self._save_trade_result(trade_result)
            
        except Exception as e:
            self.logger.error(f"거래 결과 기록 실패: {e}")
    
    def _save_trade_result(self, trade_result: Dict):
        """거래 결과 저장"""
        try:
            # 거래 결과 파일 로드
            results_file = "data/trades/trade_results.json"
            
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    results_data = json.load(f)
            except FileNotFoundError:
                results_data = {'trades': []}
            
            # 새 결과 추가
            results_data['trades'].append(trade_result)
            
            # 최근 1000개 결과만 유지
            if len(results_data['trades']) > 1000:
                results_data['trades'] = results_data['trades'][-1000:]
            
            # 파일 저장
            os.makedirs(os.path.dirname(results_file), exist_ok=True)
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"거래 결과 저장 실패: {e}")
    
    def update_positions(self):
        """포지션 현황 업데이트"""
        try:
            if not self.positions:
                return
            
            # 모든 포지션의 현재가 업데이트
            tickers = [p.ticker for p in self.positions.values()]
            current_prices = self.data_collector.get_current_prices(tickers)
            
            for position_id, position in self.positions.items():
                ticker = position.ticker
                current_price = current_prices.get(ticker)
                
                if current_price:
                    # 포지션 정보 업데이트
                    position.current_price = current_price
                    position.current_value = position.quantity * current_price
                    position.unrealized_pnl = position.current_value - position.total_invested
                    position.unrealized_pnl_ratio = position.unrealized_pnl / position.total_invested
                    position.last_updated = datetime.now()
            
            # 업데이트된 포지션 저장
            self._save_positions()
            
        except Exception as e:
            self.logger.error(f"포지션 업데이트 실패: {e}")
    
    def check_exit_conditions(self):
        """청산 조건 체크"""
        try:
            positions_to_close = []
            
            for position_id, position in self.positions.items():
                exit_reason = self._should_close_position(position)
                if exit_reason:
                    positions_to_close.append((position, exit_reason))
            
             # 청산 실행
            for position, reason in positions_to_close:
                self._close_position(position, reason['type'], reason['detail'])
            
        except Exception as e:
            self.logger.error(f"청산 조건 체크 실패: {e}")
    def _should_close_position(self, position: Position) -> Optional[Dict]:
        """포지션 청산 여부 판단"""
        try:
            current_price = position.current_price
            entry_price = position.entry_price
            
            # 1. 손절 조건
            if current_price <= position.stop_loss:
                return {
                    'type': 'STOP_LOSS',
                    'detail': f'손절 실행 ({current_price:,.0f} <= {position.stop_loss:,.0f})'
                }
            
            # 2. 익절 조건
            if current_price >= position.take_profit:
                return {
                    'type': 'TAKE_PROFIT',
                    'detail': f'익절 실행 ({current_price:,.0f} >= {position.take_profit:,.0f})'
                }
            
            # 3. 시간 기반 청산 (24시간 이상 보유)
            holding_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
            if holding_hours >= 24:
                # 손실 상태에서 24시간 초과 시 청산
                if position.unrealized_pnl_ratio < -0.02:  # -2% 이하
                    return {
                        'type': 'TIME_BASED',
                        'detail': f'장기보유 손실청산 ({holding_hours:.1f}h, {position.unrealized_pnl_ratio:.2%})'
                    }
            
            # 4. 강제 청산 (72시간 초과)
            if holding_hours >= 72:
                return {
                    'type': 'FORCE_TIME',
                    'detail': f'강제 시간청산 ({holding_hours:.1f}h)'
                }
            
            # 5. 급격한 하락 (진입가 대비 -10% 이하)
            if position.unrealized_pnl_ratio <= -0.10:
                return {
                    'type': 'EMERGENCY',
                    'detail': f'급락 응급청산 ({position.unrealized_pnl_ratio:.2%})'
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"청산 조건 판단 실패: {e}")
            return None
    
    def _remove_position(self, position_id: str):
        """포지션 제거"""
        try:
            if position_id in self.positions:
                position = self.positions.pop(position_id)
                self.logger.info(f"포지션 제거: {position.ticker} (ID: {position_id[:8]})")
                
                # 포지션 데이터 저장
                self._save_positions()
        
        except Exception as e:
            self.logger.error(f"포지션 제거 실패: {e}")
    
    def _save_positions(self):
        """포지션 데이터 저장"""
        try:
            positions_data = {}
            
            for position_id, position in self.positions.items():
                positions_data[position_id] = {
                    'position_id': position.position_id,
                    'ticker': position.ticker,
                    'strategy_id': position.strategy_id,
                    'entry_price': position.entry_price,
                    'quantity': position.quantity,
                    'total_invested': position.total_invested,
                    'current_price': position.current_price,
                    'current_value': position.current_value,
                    'unrealized_pnl': position.unrealized_pnl,
                    'unrealized_pnl_ratio': position.unrealized_pnl_ratio,
                    'stop_loss': position.stop_loss,
                    'take_profit': position.take_profit,
                    'entry_time': position.entry_time.isoformat(),
                    'last_updated': position.last_updated.isoformat(),
                    'strategy_name': position.strategy_name,
                    'reasoning': position.reasoning
                }
            
            # 파일 저장
            positions_file = "data/trades/positions.json"
            os.makedirs(os.path.dirname(positions_file), exist_ok=True)
            
            with open(positions_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'positions': positions_data,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"포지션 저장 실패: {e}")
    
    def _load_positions(self):
        """포지션 데이터 로드"""
        try:
            positions_file = "data/trades/positions.json"
            
            if not os.path.exists(positions_file):
                return
            
            with open(positions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            positions_data = data.get('positions', {})
            
            for position_id, position_data in positions_data.items():
                position = Position(
                    position_id=position_data['position_id'],
                    ticker=position_data['ticker'],
                    strategy_id=position_data['strategy_id'],
                    entry_price=position_data['entry_price'],
                    quantity=position_data['quantity'],
                    total_invested=position_data['total_invested'],
                    current_price=position_data['current_price'],
                    current_value=position_data['current_value'],
                    unrealized_pnl=position_data['unrealized_pnl'],
                    unrealized_pnl_ratio=position_data['unrealized_pnl_ratio'],
                    stop_loss=position_data['stop_loss'],
                    take_profit=position_data['take_profit'],
                    entry_time=datetime.fromisoformat(position_data['entry_time']),
                    last_updated=datetime.fromisoformat(position_data['last_updated']),
                    strategy_name=position_data['strategy_name'],
                    reasoning=position_data['reasoning']
                )
                
                self.positions[position_id] = position
            
            self.logger.info(f"포지션 데이터 로드: {len(self.positions)}개")
            
        except Exception as e:
            self.logger.error(f"포지션 로드 실패: {e}")
            self.positions = {}  
    def get_portfolio_summary(self) -> Dict[str, any]:
        """포트폴리오 요약"""
        try:
            if not self.positions:
                return {
                    'total_positions': 0,
                    'total_invested': 0,
                    'total_current_value': 0,
                    'total_unrealized_pnl': 0,
                    'total_unrealized_pnl_ratio': 0,
                    'available_capital': self.data_collector.get_balance("KRW"),
                    'positions': []
                }
            
            total_invested = sum(p.total_invested for p in self.positions.values())
            total_current_value = sum(p.current_value for p in self.positions.values())
            total_unrealized_pnl = total_current_value - total_invested
            total_unrealized_pnl_ratio = total_unrealized_pnl / total_invested if total_invested > 0 else 0
            
            # 개별 포지션 정보
            positions_info = []
            for position in self.positions.values():
                positions_info.append({
                    'ticker': position.ticker,
                    'strategy_name': position.strategy_name,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'quantity': position.quantity,
                    'invested': position.total_invested,
                    'current_value': position.current_value,
                    'pnl': position.unrealized_pnl,
                    'pnl_ratio': position.unrealized_pnl_ratio,
                    'holding_hours': (datetime.now() - position.entry_time).total_seconds() / 3600
                })
            
            return {
                'total_positions': len(self.positions),
                'total_invested': total_invested,
                'total_current_value': total_current_value,
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_unrealized_pnl_ratio': total_unrealized_pnl_ratio,
                'available_capital': self.data_collector.get_balance("KRW"),
                'max_positions': self.max_positions,
                'capital_per_position': self.capital_per_position,
                'daily_trade_count': self.daily_trade_count,
                'daily_loss': self.daily_loss,
                'positions': positions_info,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"포트폴리오 요약 실패: {e}")
            return {'error': str(e)}
    
    def get_trade_statistics(self) -> Dict[str, any]:
        """거래 통계"""
        try:
            if not self.order_history:
                return {'total_trades': 0, 'message': '거래 기록 없음'}
            
            # 체결된 주문만 필터링
            filled_orders = [o for o in self.order_history if o.status == "FILLED"]
            buy_orders = [o for o in filled_orders if o.order_type == "BUY"]
            sell_orders = [o for o in filled_orders if o.order_type == "SELL"]
            
            # 완성된 거래 쌍 찾기 (매수-매도)
            completed_trades = len(sell_orders)  # 매도가 완료된 거래 수
            
            # 거래 결과 로드
            trade_results = self._load_trade_results()
            
            if trade_results:
                profitable_trades = len([t for t in trade_results if t['profit_ratio'] > 0])
                total_profit = sum(t['profit_ratio'] for t in trade_results)
                avg_profit = total_profit / len(trade_results) if trade_results else 0
                win_rate = profitable_trades / len(trade_results) if trade_results else 0
                
                # 최고/최악 거래
                best_trade = max(trade_results, key=lambda x: x['profit_ratio']) if trade_results else None
                worst_trade = min(trade_results, key=lambda x: x['profit_ratio']) if trade_results else None
                
                # 평균 보유 시간
                avg_holding_time = sum(t['duration_hours'] for t in trade_results) / len(trade_results) if trade_results else 0
            else:
                profitable_trades = 0
                total_profit = 0
                avg_profit = 0
                win_rate = 0
                best_trade = None
                worst_trade = None
                avg_holding_time = 0
            
            return {
                'total_orders': len(filled_orders),
                'buy_orders': len(buy_orders),
                'sell_orders': len(sell_orders),
                'completed_trades': completed_trades,
                'profitable_trades': profitable_trades,
                'win_rate': win_rate,
                'total_profit_ratio': total_profit,
                'avg_profit_ratio': avg_profit,
                'avg_holding_hours': avg_holding_time,
                'best_trade': {
                    'ticker': best_trade['ticker'],
                    'profit_ratio': best_trade['profit_ratio'],
                    'profit_amount': best_trade['profit_amount']
                } if best_trade else None,
                'worst_trade': {
                    'ticker': worst_trade['ticker'],
                    'profit_ratio': worst_trade['profit_ratio'],
                    'profit_amount': worst_trade['profit_amount']
                } if worst_trade else None,
                'daily_trade_count': self.daily_trade_count,
                'daily_loss': self.daily_loss
            }
            
        except Exception as e:
            self.logger.error(f"거래 통계 계산 실패: {e}")
            return {'error': str(e)}
    
    def _load_trade_results(self) -> List[Dict]:
        """거래 결과 로드"""
        try:
            results_file = "data/trades/trade_results.json"
            
            if not os.path.exists(results_file):
                return []
            
            with open(results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('trades', [])
            
        except Exception as e:
            self.logger.error(f"거래 결과 로드 실패: {e}")
            return []
    def emergency_close_all_positions(self) -> bool:
        """모든 포지션 긴급 청산"""
        try:
            self.logger.warning("🚨 모든 포지션 긴급 청산 시작")
            
            if not self.positions:
                self.logger.info("청산할 포지션 없음")
                return True
            
            success_count = 0
            total_count = len(self.positions)
            
            # 모든 포지션 청산
            positions_to_close = list(self.positions.values()).copy()
            
            for position in positions_to_close:
                try:
                    if self._close_position(position, "EMERGENCY_CLOSE", "긴급 청산"):
                        success_count += 1
                        time.sleep(1)  # API 제한 고려
                except Exception as e:
                    self.logger.error(f"포지션 긴급청산 실패 {position.ticker}: {e}")
            
            self.logger.warning(f"긴급 청산 완료: {success_count}/{total_count}")
            
            return success_count == total_count
            
        except Exception as e:
            self.logger.error(f"긴급 청산 실패: {e}")
            return False
    
    def cancel_all_pending_orders(self) -> bool:
        """모든 대기 중인 주문 취소"""
        try:
            if not self.active_orders:
                return True
            
            cancelled_count = 0
            
            for order_id, order in list(self.active_orders.items()):
                try:
                    if order.upbit_uuid:
                        result = self.upbit.cancel_order(order.upbit_uuid)
                        if result:
                            order.status = "CANCELLED"
                            cancelled_count += 1
                            self.logger.info(f"주문 취소: {order.ticker}")
                        
                        del self.active_orders[order_id]
                        
                except Exception as e:
                    self.logger.error(f"주문 취소 실패 {order.ticker}: {e}")
            
            self.logger.info(f"주문 취소 완료: {cancelled_count}개")
            return True
            
        except Exception as e:
            self.logger.error(f"주문 취소 실패: {e}")
            return False
    
    def reset_daily_limits(self):
        """일일 제한 리셋"""
        try:
            self.daily_trade_count = 0
            self.daily_loss = 0.0
            self.last_trade_time.clear()
            self.logger.info("일일 거래 제한 리셋 완료")
            
        except Exception as e:
            self.logger.error(f"일일 제한 리셋 실패: {e}")
    
    def get_position_by_ticker(self, ticker: str) -> Optional[Position]:
        """티커로 포지션 조회"""
        return self._find_position_by_ticker(ticker)
    
    def get_order_history(self, limit: int = 50) -> List[Dict]:
        """주문 기록 조회"""
        try:
            recent_orders = self.order_history[-limit:] if self.order_history else []
            
            order_list = []
            for order in recent_orders:
                order_list.append({
                    'order_id': order.order_id,
                    'ticker': order.ticker,
                    'order_type': order.order_type,
                    'price': order.price,
                    'quantity': order.quantity,
                    'total_amount': order.total_amount,
                    'status': order.status,
                    'created_at': order.created_at.isoformat(),
                    'filled_at': order.filled_at.isoformat() if order.filled_at else None
                })
            
            return order_list
            
        except Exception as e:
            self.logger.error(f"주문 기록 조회 실패: {e}")
            return []
    def health_check(self) -> Dict[str, any]:
        """매매 시스템 상태 확인"""
        try:
            # API 연결 상태
            api_status = "OK" if self.upbit else "DISCONNECTED"
            
            # 잔고 확인
            try:
                krw_balance = self.data_collector.get_balance("KRW")
                balance_status = "OK" if krw_balance >= 0 else "ERROR"
            except:
                krw_balance = 0
                balance_status = "ERROR"
            
            # 포지션 상태
            positions_status = "OK"
            if len(self.positions) >= self.max_positions:
                positions_status = "FULL"
            elif any(p.unrealized_pnl_ratio < -0.15 for p in self.positions.values()):
                positions_status = "HIGH_LOSS"
            
            # 일일 제한 상태
            limits_status = "OK"
            if self.daily_trade_count >= 15:
                limits_status = "NEAR_LIMIT"
            elif self.daily_loss < -0.05:
                limits_status = "HIGH_DAILY_LOSS"
            
            return {
                'timestamp': datetime.now().isoformat(),
                'api_status': api_status,
                'balance_status': balance_status,
                'positions_status': positions_status,
                'limits_status': limits_status,
                'krw_balance': krw_balance,
                'active_positions': len(self.positions),
                'max_positions': self.max_positions,
                'daily_trade_count': self.daily_trade_count,
                'daily_loss': self.daily_loss,
                'pending_orders': len(self.active_orders)
            }
            
        except Exception as e:
            self.logger.error(f"헬스체크 실패: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'ERROR',
                'error': str(e)
            }
    
    def force_sync_balances(self):
        """잔고 강제 동기화"""
        try:
            self.logger.info("잔고 동기화 시작")
            
            # 업비트에서 실제 잔고 조회
            actual_balances = self.data_collector.get_all_balances()
            
            # 포지션과 실제 잔고 비교
            for position_id, position in list(self.positions.items()):
                ticker = position.ticker
                currency = ticker.replace('KRW-', '')
                
                actual_balance = actual_balances.get(currency, 0)
                
                # 실제 잔고가 없으면 포지션 제거
                if actual_balance <= 0.000001:  # 소수점 오차 고려
                    self.logger.warning(f"실제 잔고 없음 - 포지션 제거: {ticker}")
                    self._remove_position(position_id)
                else:
                    # 수량 차이가 있으면 수정
                    if abs(position.quantity - actual_balance) > 0.000001:
                        self.logger.info(f"수량 불일치 수정: {ticker} "
                                       f"{position.quantity:.6f} -> {actual_balance:.6f}")
                        position.quantity = actual_balance
                        position.current_value = position.current_price * actual_balance
            
            # 포지션에 없는 코인 잔고가 있으면 알림
            for currency, balance in actual_balances.items():
                if currency == 'KRW':
                    continue
                
                ticker = f'KRW-{currency}'
                if not any(p.ticker == ticker for p in self.positions.values()) and balance > 0.000001:
                    self.logger.warning(f"포지션에 없는 코인 잔고 발견: {ticker} {balance:.6f}")
            
            self.logger.info("잔고 동기화 완료")
            
        except Exception as e:
            self.logger.error(f"잔고 동기화 실패: {e}")
    
    def __del__(self):
        """소멸자 - 정리 작업"""
        try:
            if hasattr(self, 'positions') and self.positions:
                self._save_positions()
        except:
            pass                      
"""
데이터 수집 모듈 (1/2)
업비트 API를 통한 실시간 데이터 수집
"""

import pyupbit
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import asyncio
from dataclasses import dataclass

from config.settings import settings
from utils.logger import Logger

@dataclass
class MarketData:
    """시장 데이터 클래스"""
    ticker: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str

@dataclass
class OrderbookData:
    """호가 데이터 클래스"""
    ticker: str
    timestamp: datetime
    bid_price: float      # 매수 호가
    ask_price: float      # 매도 호가
    bid_size: float       # 매수 잔량
    ask_size: float       # 매도 잔량
    spread: float         # 스프레드

class DataCollector:
    """데이터 수집기 클래스"""
    
    def __init__(self):
        self.logger = Logger()
        self.settings = settings
        
        # API 제한 관리
        self.last_request_time = {}
        self.request_interval = 0.1  # 100ms 간격
        
        # 데이터 캐시
        self.data_cache = {}
        self.cache_duration = 30  # 30초간 캐시 유지
        
        # 업비트 객체
        self.upbit_public = None
        self.upbit_private = None
        
        self._initialize_upbit()
        
        self.logger.info("데이터 수집기 초기화 완료")
    
    def _initialize_upbit(self):
        """업비트 API 초기화"""
        try:
            # 공개 API (시세 조회용)
            self.upbit_public = pyupbit
            
            # 개인 API (거래용) - API 키가 있을 때만
            if self.settings.upbit_access_key and self.settings.upbit_secret_key:
                self.upbit_private = pyupbit.Upbit(
                    self.settings.upbit_access_key,
                    self.settings.upbit_secret_key
                )
                self.logger.info("업비트 개인 API 연결 완료")
            else:
                self.logger.warning("업비트 API 키가 없어 공개 API만 사용")
                
        except Exception as e:
            self.logger.error(f"업비트 API 초기화 실패: {e}")
            raise
    
    def _rate_limit_check(self, endpoint: str):
        """API 호출 제한 확인"""
        current_time = time.time()
        last_time = self.last_request_time.get(endpoint, 0)
        
        if current_time - last_time < self.request_interval:
            sleep_time = self.request_interval - (current_time - last_time)
            time.sleep(sleep_time)
        
        self.last_request_time[endpoint] = time.time()
    
    def _get_cache_key(self, ticker: str, timeframe: str, count: int) -> str:
        """캐시 키 생성"""
        return f"{ticker}_{timeframe}_{count}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 검사"""
        if cache_key not in self.data_cache:
            return False
        
        cache_time = self.data_cache[cache_key]['timestamp']
        return (datetime.now() - cache_time).seconds < self.cache_duration
    
    def get_ohlcv(self, ticker: str, timeframe: str = "minute1", count: int = 200) -> Optional[pd.DataFrame]:
        """OHLCV 데이터 조회"""
        try:
            cache_key = self._get_cache_key(ticker, timeframe, count)
            
            # 캐시 확인
            if self._is_cache_valid(cache_key):
                return self.data_cache[cache_key]['data'].copy()
            
            # API 호출 제한 확인
            self._rate_limit_check(f"ohlcv_{ticker}")
            
            # 데이터 조회
            df = pyupbit.get_ohlcv(ticker, interval=timeframe, count=count)
            
            if df is None or len(df) == 0:
                self.logger.warning(f"OHLCV 데이터 없음: {ticker}")
                return None
            
            # 데이터 정제
            df = self._clean_ohlcv_data(df, ticker, timeframe)
            
            # 캐시 저장
            self.data_cache[cache_key] = {
                'data': df.copy(),
                'timestamp': datetime.now()
            }
            
            return df
            
        except Exception as e:
            self.logger.error(f"OHLCV 조회 실패 {ticker}: {e}")
            return None
    
    def _clean_ohlcv_data(self, df: pd.DataFrame, ticker: str, timeframe: str) -> pd.DataFrame:
        """OHLCV 데이터 정제"""
        try:
            # 결측값 처리
            df = df.dropna()
            
            # 이상값 처리
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            
            df['volume'] = df['volume'].astype(float)
            
            # 추가 컬럼
            df['ticker'] = ticker
            df['timeframe'] = timeframe
            df['timestamp'] = df.index
            
            # 변화율 계산
            df['price_change'] = df['close'].pct_change()
            df['volume_change'] = df['volume'].pct_change()
            
            return df
            
        except Exception as e:
            self.logger.error(f"데이터 정제 실패: {e}")
            return df
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """현재가 조회"""
        try:
            self._rate_limit_check(f"price_{ticker}")
            
            price = pyupbit.get_current_price(ticker)
            return float(price) if price else None
            
        except Exception as e:
            self.logger.error(f"현재가 조회 실패 {ticker}: {e}")
            return None
    
    def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """여러 코인 현재가 일괄 조회"""
        try:
            self._rate_limit_check("prices_bulk")
            
            prices = pyupbit.get_current_price(tickers)
            
            if isinstance(prices, dict):
                return {k: float(v) for k, v in prices.items() if v}
            else:
                # 단일 티커인 경우
                return {tickers[0]: float(prices)} if prices else {}
                
        except Exception as e:
            self.logger.error(f"현재가 일괄 조회 실패: {e}")
            return {}
        def get_orderbook(self, ticker: str) -> Optional[OrderbookData]:
             """호가 정보 조회"""
        try:
            self._rate_limit_check(f"orderbook_{ticker}")
            
            orderbook = pyupbit.get_orderbook(ticker)
            
            if not orderbook or len(orderbook) == 0:
                return None
            
            # 첫 번째 호가 데이터 추출
            first_orderbook = orderbook[0]
            orderbook_units = first_orderbook.get('orderbook_units', [])
            
            if not orderbook_units:
                return None
            
            best_bid = orderbook_units[0]
            best_ask = orderbook_units[0]
            
            return OrderbookData(
                ticker=ticker,
                timestamp=datetime.now(),
                bid_price=float(best_bid.get('bid_price', 0)),
                ask_price=float(best_ask.get('ask_price', 0)),
                bid_size=float(best_bid.get('bid_size', 0)),
                ask_size=float(best_ask.get('ask_size', 0)),
                spread=float(best_ask.get('ask_price', 0)) - float(best_bid.get('bid_price', 0))
            )
            
        except Exception as e:
            self.logger.error(f"호가 조회 실패 {ticker}: {e}")
            return None
    
    def get_multi_timeframe_data(self, ticker: str, timeframes: List[str] = None, count: int = 200) -> Dict[str, pd.DataFrame]:
        """다중 시간봉 데이터 조회"""
        if timeframes is None:
            timeframes = self.settings.analysis.timeframes
        
        data = {}
        
        for timeframe in timeframes:
            df = self.get_ohlcv(ticker, timeframe, count)
            if df is not None:
                data[timeframe] = df
            else:
                self.logger.warning(f"데이터 조회 실패: {ticker} {timeframe}")
        
        return data
    
    def get_market_summary(self) -> Dict[str, any]:
        """시장 전체 요약 정보"""
        try:
            summary = {
                'timestamp': datetime.now(),
                'total_coins': len(self.settings.analysis.target_coins),
                'price_data': {},
                'volume_data': {},
                'market_trend': 'NEUTRAL'
            }
            
            # 전체 코인 현재가 조회
            prices = self.get_current_prices(self.settings.analysis.target_coins)
            summary['price_data'] = prices
            
            # 거래량 정보
            total_volume = 0
            rising_count = 0
            
            for ticker in self.settings.analysis.target_coins:
                df = self.get_ohlcv(ticker, "minute60", 24)  # 24시간 데이터
                if df is not None and len(df) > 1:
                    volume = df['volume'].sum()
                    total_volume += volume
                    
                    # 상승/하락 카운트
                    if df['close'].iloc[-1] > df['close'].iloc[0]:
                        rising_count += 1
            
            summary['total_volume'] = total_volume
            summary['rising_ratio'] = rising_count / len(self.settings.analysis.target_coins)
            
            # 시장 트렌드 판단
            if summary['rising_ratio'] > 0.6:
                summary['market_trend'] = 'BULLISH'
            elif summary['rising_ratio'] < 0.4:
                summary['market_trend'] = 'BEARISH'
            
            return summary
            
        except Exception as e:
            self.logger.error(f"시장 요약 정보 조회 실패: {e}")
            return {'timestamp': datetime.now(), 'error': str(e)}
    
    def get_balance(self, ticker: str = "KRW") -> float:
        """잔고 조회 (개인 API 필요)"""
        try:
            if not self.upbit_private:
                self.logger.warning("개인 API가 설정되지 않음")
                return 0.0
            
            self._rate_limit_check(f"balance_{ticker}")
            
            balance = self.upbit_private.get_balance(ticker)
            return float(balance) if balance else 0.0
            
        except Exception as e:
            self.logger.error(f"잔고 조회 실패 {ticker}: {e}")
            return 0.0
    
    def get_all_balances(self) -> Dict[str, float]:
        """전체 잔고 조회"""
        try:
            if not self.upbit_private:
                return {}
            
            self._rate_limit_check("balances_all")
            
            balances = self.upbit_private.get_balances()
            
            result = {}
            for balance in balances:
                currency = balance.get('currency', '')
                balance_amount = float(balance.get('balance', 0))
                
                if balance_amount > 0:
                    result[currency] = balance_amount
            
            return result
            
        except Exception as e:
            self.logger.error(f"전체 잔고 조회 실패: {e}")
            return {}
    
    def clear_cache(self):
        """캐시 초기화"""
        self.data_cache.clear()
        self.logger.info("데이터 캐시 초기화 완료")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """캐시 통계"""
        return {
            'total_entries': len(self.data_cache),
            'memory_usage_mb': len(str(self.data_cache)) / 1024 / 1024,
            'oldest_entry': min([v['timestamp'] for v in self.data_cache.values()]) if self.data_cache else None
        }
    
    def health_check(self) -> Dict[str, any]:
        """API 연결 상태 확인"""
        try:
            # 공개 API 테스트
            test_price = self.get_current_price("KRW-BTC")
            public_api_status = "OK" if test_price else "FAIL"
            
            # 개인 API 테스트
            private_api_status = "NOT_CONFIGURED"
            if self.upbit_private:
                try:
                    balance = self.get_balance("KRW")
                    private_api_status = "OK" if balance >= 0 else "FAIL"
                except:
                    private_api_status = "FAIL"
            
            return {
                'timestamp': datetime.now(),
                'public_api': public_api_status,
                'private_api': private_api_status,
                'cache_entries': len(self.data_cache),
                'last_request_count': len(self.last_request_time)
            }
            
        except Exception as e:
            self.logger.error(f"헬스체크 실패: {e}")
            return {
                'timestamp': datetime.now(),
                'status': 'ERROR',
                'error': str(e)
            }
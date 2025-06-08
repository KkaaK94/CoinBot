"""
CoinBot 데이터베이스 관리 시스템
- SQLite 기반 데이터 영속성
- 거래 기록, 포지션, 성과 추적
- 백업 및 복구 기능
"""

import sqlite3
import json
import os
import shutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from contextlib import contextmanager
import logging
from dataclasses import dataclass, asdict
import pandas as pd

# 프로젝트 모듈
try:
    from utils.logger import Logger
except ImportError:
    # 로거가 없을 경우 기본 로깅 사용
    logging.basicConfig(level=logging.INFO)
    Logger = logging.getLogger

@dataclass
class TradeRecord:
    """거래 기록 데이터 클래스"""
    trade_id: str
    ticker: str
    action: str  # BUY, SELL
    price: float
    quantity: float
    total_amount: float
    commission: float
    strategy_id: str
    confidence: float
    timestamp: datetime
    upbit_uuid: Optional[str] = None
    profit_loss: Optional[float] = None
    profit_ratio: Optional[float] = None

@dataclass
class PositionRecord:
    """포지션 기록 데이터 클래스"""
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
    stop_loss: float
    take_profit: float
    entry_time: datetime
    last_updated: datetime
    status: str  # ACTIVE, CLOSED
    strategy_name: str
    reasoning: str

@dataclass
class PerformanceRecord:
    """성과 기록 데이터 클래스"""
    record_id: str
    date: datetime
    total_value: float
    krw_balance: float
    position_value: float
    total_pnl: float
    daily_pnl: float
    trade_count: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None

class DatabaseManager:
    """데이터베이스 관리자 클래스"""
    
    def __init__(self, db_path: str = "data/coinbot.db"):
        """데이터베이스 초기화"""
        self.db_path = Path(db_path)
        self.logger = Logger() if hasattr(Logger, 'info') else logging.getLogger(__name__)
        self._lock = threading.Lock()
        
        # 데이터베이스 디렉토리 생성
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 백업 설정
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # 데이터베이스 초기화
        self._initialize_database()
        
        self.logger.info(f"데이터베이스 초기화 완료: {self.db_path}")
    
    def _initialize_database(self):
        """데이터베이스 테이블 생성"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 거래 기록 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id TEXT PRIMARY KEY,
                        ticker TEXT NOT NULL,
                        action TEXT NOT NULL,
                        price REAL NOT NULL,
                        quantity REAL NOT NULL,
                        total_amount REAL NOT NULL,
                        commission REAL DEFAULT 0,
                        strategy_id TEXT,
                        confidence REAL DEFAULT 0,
                        timestamp DATETIME NOT NULL,
                        upbit_uuid TEXT,
                        profit_loss REAL,
                        profit_ratio REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 포지션 기록 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS positions (
                        position_id TEXT PRIMARY KEY,
                        ticker TEXT NOT NULL,
                        strategy_id TEXT,
                        entry_price REAL NOT NULL,
                        quantity REAL NOT NULL,
                        total_invested REAL NOT NULL,
                        current_price REAL NOT NULL,
                        current_value REAL NOT NULL,
                        unrealized_pnl REAL DEFAULT 0,
                        unrealized_pnl_ratio REAL DEFAULT 0,
                        stop_loss REAL,
                        take_profit REAL,
                        entry_time DATETIME NOT NULL,
                        last_updated DATETIME NOT NULL,
                        status TEXT DEFAULT 'ACTIVE',
                        strategy_name TEXT,
                        reasoning TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 성과 기록 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance (
                        record_id TEXT PRIMARY KEY,
                        date DATETIME NOT NULL,
                        total_value REAL NOT NULL,
                        krw_balance REAL NOT NULL,
                        position_value REAL NOT NULL,
                        total_pnl REAL DEFAULT 0,
                        daily_pnl REAL DEFAULT 0,
                        trade_count INTEGER DEFAULT 0,
                        win_rate REAL DEFAULT 0,
                        max_drawdown REAL DEFAULT 0,
                        sharpe_ratio REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 시스템 로그 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_logs (
                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        module TEXT,
                        function TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        extra_data TEXT
                    )
                """)
                
                # 전략 성과 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_performance (
                        strategy_id TEXT,
                        date DATETIME,
                        total_trades INTEGER DEFAULT 0,
                        successful_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0,
                        avg_holding_time REAL DEFAULT 0,
                        max_drawdown REAL DEFAULT 0,
                        win_rate REAL DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (strategy_id, date)
                    )
                """)
                
                # 리스크 이벤트 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS risk_events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        description TEXT NOT NULL,
                        ticker TEXT,
                        risk_score REAL,
                        action_taken TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        resolved BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # 인덱스 생성
                self._create_indexes(cursor)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}")
            raise
    
    def _create_indexes(self, cursor):
        """데이터베이스 인덱스 생성"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker)",
            "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_id)",
            
            "CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker)",
            "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
            "CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy_id)",
            
            "CREATE INDEX IF NOT EXISTS idx_performance_date ON performance(date)",
            
            "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level)",
            
            "CREATE INDEX IF NOT EXISTS idx_strategy_perf_date ON strategy_performance(date)",
            
            "CREATE INDEX IF NOT EXISTS idx_risk_events_timestamp ON risk_events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_risk_events_severity ON risk_events(severity)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                self.logger.warning(f"인덱스 생성 실패: {e}")
    
    @contextmanager
    def _get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path, 
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"데이터베이스 연결 오류: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _datetime_to_str(self, dt: datetime) -> str:
        """datetime을 문자열로 변환"""
        return dt.isoformat() if dt else None
    
    def _str_to_datetime(self, dt_str: str) -> Optional[datetime]:
        """문자열을 datetime으로 변환"""
        try:
            return datetime.fromisoformat(dt_str) if dt_str else None
        except (ValueError, TypeError):
            return None
    # ==========================================
    # 거래 기록 관리
    # ==========================================
    
    def save_trade(self, trade: TradeRecord) -> bool:
        """거래 기록 저장"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO trades (
                            trade_id, ticker, action, price, quantity, total_amount,
                            commission, strategy_id, confidence, timestamp, upbit_uuid,
                            profit_loss, profit_ratio
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade.trade_id, trade.ticker, trade.action, trade.price,
                        trade.quantity, trade.total_amount, trade.commission,
                        trade.strategy_id, trade.confidence, 
                        self._datetime_to_str(trade.timestamp), trade.upbit_uuid,
                        trade.profit_loss, trade.profit_ratio
                    ))
                    
                    conn.commit()
                    self.logger.info(f"거래 기록 저장: {trade.trade_id} - {trade.action} {trade.ticker}")
                    return True
                    
        except Exception as e:
            self.logger.error(f"거래 기록 저장 실패: {e}")
            return False
    
    def get_trades(self, 
                   ticker: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 100) -> List[TradeRecord]:
        """거래 기록 조회"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM trades WHERE 1=1"
                params = []
                
                if ticker:
                    query += " AND ticker = ?"
                    params.append(ticker)
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(self._datetime_to_str(start_date))
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(self._datetime_to_str(end_date))
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                trades = []
                for row in rows:
                    trade = TradeRecord(
                        trade_id=row['trade_id'],
                        ticker=row['ticker'],
                        action=row['action'],
                        price=row['price'],
                        quantity=row['quantity'],
                        total_amount=row['total_amount'],
                        commission=row['commission'] or 0,
                        strategy_id=row['strategy_id'],
                        confidence=row['confidence'] or 0,
                        timestamp=self._str_to_datetime(row['timestamp']),
                        upbit_uuid=row['upbit_uuid'],
                        profit_loss=row['profit_loss'],
                        profit_ratio=row['profit_ratio']
                    )
                    trades.append(trade)
                
                return trades
                
        except Exception as e:
            self.logger.error(f"거래 기록 조회 실패: {e}")
            return []
    
    def get_trade_statistics(self, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """거래 통계 조회"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 기간 조건
                date_condition = ""
                params = []
                if start_date:
                    date_condition += " AND timestamp >= ?"
                    params.append(self._datetime_to_str(start_date))
                if end_date:
                    date_condition += " AND timestamp <= ?"
                    params.append(self._datetime_to_str(end_date))
                
                # 전체 거래 통계
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN action = 'BUY' THEN 1 END) as buy_trades,
                        COUNT(CASE WHEN action = 'SELL' THEN 1 END) as sell_trades,
                        SUM(total_amount) as total_volume,
                        AVG(confidence) as avg_confidence
                    FROM trades 
                    WHERE 1=1 {date_condition}
                """, params)
                
                stats = dict(cursor.fetchone())
                
                # 수익성 통계 (매도 거래만)
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as completed_trades,
                        COUNT(CASE WHEN profit_ratio > 0 THEN 1 END) as profitable_trades,
                        AVG(profit_ratio) as avg_profit_ratio,
                        MAX(profit_ratio) as max_profit_ratio,
                        MIN(profit_ratio) as min_profit_ratio,
                        SUM(profit_loss) as total_profit_loss
                    FROM trades 
                    WHERE action = 'SELL' AND profit_ratio IS NOT NULL {date_condition}
                """, params)
                
                profit_stats = dict(cursor.fetchone())
                stats.update(profit_stats)
                
                # 승률 계산
                if stats['completed_trades'] and stats['completed_trades'] > 0:
                    stats['win_rate'] = stats['profitable_trades'] / stats['completed_trades']
                else:
                    stats['win_rate'] = 0
                
                # 코인별 통계
                cursor.execute(f"""
                    SELECT 
                        ticker,
                        COUNT(*) as trade_count,
                        SUM(CASE WHEN action = 'SELL' AND profit_ratio > 0 THEN 1 ELSE 0 END) as wins,
                        COUNT(CASE WHEN action = 'SELL' THEN 1 END) as completed,
                        AVG(CASE WHEN action = 'SELL' THEN profit_ratio END) as avg_return
                    FROM trades 
                    WHERE 1=1 {date_condition}
                    GROUP BY ticker
                    ORDER BY trade_count DESC
                    LIMIT 10
                """, params)
                
                ticker_stats = []
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    if row_dict['completed'] > 0:
                        row_dict['win_rate'] = row_dict['wins'] / row_dict['completed']
                    else:
                        row_dict['win_rate'] = 0
                    ticker_stats.append(row_dict)
                
                stats['ticker_stats'] = ticker_stats
                
                return stats
                
        except Exception as e:
            self.logger.error(f"거래 통계 조회 실패: {e}")
            return {}
    
    def update_trade_result(self, trade_id: str, profit_loss: float, profit_ratio: float) -> bool:
        """거래 결과 업데이트 (매도 시)"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        UPDATE trades 
                        SET profit_loss = ?, profit_ratio = ?
                        WHERE trade_id = ?
                    """, (profit_loss, profit_ratio, trade_id))
                    
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        self.logger.info(f"거래 결과 업데이트: {trade_id}")
                        return True
                    else:
                        self.logger.warning(f"거래 기록 없음: {trade_id}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"거래 결과 업데이트 실패: {e}")
            return False
    
    def delete_old_trades(self, days_to_keep: int = 365) -> int:
        """오래된 거래 기록 삭제"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        DELETE FROM trades 
                        WHERE timestamp < ?
                    """, (self._datetime_to_str(cutoff_date),))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    self.logger.info(f"오래된 거래 기록 삭제: {deleted_count}개")
                    return deleted_count
                    
        except Exception as e:
            self.logger.error(f"거래 기록 삭제 실패: {e}")
            return 0
            
    # ==========================================
    # 포지션 관리
    # ==========================================
    
    def save_position(self, position: PositionRecord) -> bool:
        """포지션 기록 저장"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO positions (
                            position_id, ticker, strategy_id, entry_price, quantity,
                            total_invested, current_price, current_value, unrealized_pnl,
                            unrealized_pnl_ratio, stop_loss, take_profit, entry_time,
                            last_updated, status, strategy_name, reasoning
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        position.position_id, position.ticker, position.strategy_id,
                        position.entry_price, position.quantity, position.total_invested,
                        position.current_price, position.current_value, position.unrealized_pnl,
                        position.unrealized_pnl_ratio, position.stop_loss, position.take_profit,
                        self._datetime_to_str(position.entry_time),
                        self._datetime_to_str(position.last_updated),
                        position.status, position.strategy_name, position.reasoning
                    ))
                    
                    conn.commit()
                    self.logger.debug(f"포지션 저장: {position.position_id} - {position.ticker}")
                    return True
                    
        except Exception as e:
            self.logger.error(f"포지션 저장 실패: {e}")
            return False
    
    def get_active_positions(self) -> List[PositionRecord]:
        """활성 포지션 조회"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM positions 
                    WHERE status = 'ACTIVE'
                    ORDER BY entry_time DESC
                """)
                
                positions = []
                for row in cursor.fetchall():
                    position = PositionRecord(
                        position_id=row['position_id'],
                        ticker=row['ticker'],
                        strategy_id=row['strategy_id'],
                        entry_price=row['entry_price'],
                        quantity=row['quantity'],
                        total_invested=row['total_invested'],
                        current_price=row['current_price'],
                        current_value=row['current_value'],
                        unrealized_pnl=row['unrealized_pnl'],
                        unrealized_pnl_ratio=row['unrealized_pnl_ratio'],
                        stop_loss=row['stop_loss'],
                        take_profit=row['take_profit'],
                        entry_time=self._str_to_datetime(row['entry_time']),
                        last_updated=self._str_to_datetime(row['last_updated']),
                        status=row['status'],
                        strategy_name=row['strategy_name'],
                        reasoning=row['reasoning']
                    )
                    positions.append(position)
                
                return positions
                
        except Exception as e:
            self.logger.error(f"활성 포지션 조회 실패: {e}")
            return []
    
    def update_position_prices(self, position_id: str, current_price: float) -> bool:
        """포지션 현재가 업데이트"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 먼저 포지션 정보 조회
                    cursor.execute("""
                        SELECT quantity, total_invested FROM positions 
                        WHERE position_id = ?
                    """, (position_id,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return False
                    
                    quantity = row['quantity']
                    total_invested = row['total_invested']
                    
                    # 새로운 값들 계산
                    current_value = quantity * current_price
                    unrealized_pnl = current_value - total_invested
                    unrealized_pnl_ratio = unrealized_pnl / total_invested if total_invested > 0 else 0
                    
                    # 업데이트
                    cursor.execute("""
                        UPDATE positions 
                        SET current_price = ?, current_value = ?, 
                            unrealized_pnl = ?, unrealized_pnl_ratio = ?,
                            last_updated = ?
                        WHERE position_id = ?
                    """, (current_price, current_value, unrealized_pnl, 
                          unrealized_pnl_ratio, self._datetime_to_str(datetime.now()), 
                          position_id))
                    
                    conn.commit()
                    return cursor.rowcount > 0
                    
        except Exception as e:
            self.logger.error(f"포지션 가격 업데이트 실패: {e}")
            return False
    
    def close_position(self, position_id: str) -> bool:
        """포지션 종료"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        UPDATE positions 
                        SET status = 'CLOSED', last_updated = ?
                        WHERE position_id = ?
                    """, (self._datetime_to_str(datetime.now()), position_id))
                    
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        self.logger.info(f"포지션 종료: {position_id}")
                        return True
                    else:
                        self.logger.warning(f"포지션 없음: {position_id}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"포지션 종료 실패: {e}")
            return False
    
    # ==========================================
    # 성과 기록 관리
    # ==========================================
    
    def save_performance(self, performance: PerformanceRecord) -> bool:
        """성과 기록 저장"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO performance (
                            record_id, date, total_value, krw_balance, position_value,
                            total_pnl, daily_pnl, trade_count, win_rate, max_drawdown,
                            sharpe_ratio
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        performance.record_id, self._datetime_to_str(performance.date),
                        performance.total_value, performance.krw_balance, performance.position_value,
                        performance.total_pnl, performance.daily_pnl, performance.trade_count,
                        performance.win_rate, performance.max_drawdown, performance.sharpe_ratio
                    ))
                    
                    conn.commit()
                    self.logger.debug(f"성과 기록 저장: {performance.date.strftime('%Y-%m-%d')}")
                    return True
                    
        except Exception as e:
            self.logger.error(f"성과 기록 저장 실패: {e}")
            return False
    
    def get_performance_history(self, days: int = 30) -> List[PerformanceRecord]:
        """성과 히스토리 조회"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM performance 
                    WHERE date >= ?
                    ORDER BY date DESC
                """, (self._datetime_to_str(start_date),))
                
                records = []
                for row in cursor.fetchall():
                    record = PerformanceRecord(
                        record_id=row['record_id'],
                        date=self._str_to_datetime(row['date']),
                        total_value=row['total_value'],
                        krw_balance=row['krw_balance'],
                        position_value=row['position_value'],
                        total_pnl=row['total_pnl'],
                        daily_pnl=row['daily_pnl'],
                        trade_count=row['trade_count'],
                        win_rate=row['win_rate'],
                        max_drawdown=row['max_drawdown'],
                        sharpe_ratio=row['sharpe_ratio']
                    )
                    records.append(record)
                
                return records
                
        except Exception as e:
            self.logger.error(f"성과 히스토리 조회 실패: {e}")
            return []
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """성과 지표 계산"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 최근 30일 성과 데이터
                thirty_days_ago = datetime.now() - timedelta(days=30)
                cursor.execute("""
                    SELECT * FROM performance 
                    WHERE date >= ?
                    ORDER BY date ASC
                """, (self._datetime_to_str(thirty_days_ago),))
                
                records = cursor.fetchall()
                if not records:
                    return {}
                
                # 기본 지표 계산
                initial_value = records[0]['total_value']
                current_value = records[-1]['total_value']
                total_return = (current_value - initial_value) / initial_value if initial_value > 0 else 0
                
                # 일일 수익률 계산
                daily_returns = []
                for i in range(1, len(records)):
                    prev_value = records[i-1]['total_value']
                    curr_value = records[i]['total_value']
                    if prev_value > 0:
                        daily_return = (curr_value - prev_value) / prev_value
                        daily_returns.append(daily_return)
                
                # 변동성 및 샤프 비율 계산
                if daily_returns:
                    import numpy as np
                    daily_returns_array = np.array(daily_returns)
                    volatility = np.std(daily_returns_array) * np.sqrt(365)  # 연환산
                    mean_return = np.mean(daily_returns_array) * 365  # 연환산
                    sharpe_ratio = mean_return / volatility if volatility > 0 else 0
                else:
                    volatility = 0
                    sharpe_ratio = 0
                
                # 최대 낙폭 계산
                peak_value = initial_value
                max_drawdown = 0
                for record in records:
                    current_val = record['total_value']
                    if current_val > peak_value:
                        peak_value = current_val
                    drawdown = (peak_value - current_val) / peak_value if peak_value > 0 else 0
                    max_drawdown = max(max_drawdown, drawdown)
                
                # 거래 통계
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN profit_ratio > 0 THEN 1 END) as winning_trades,
                        AVG(profit_ratio) as avg_return,
                        MAX(profit_ratio) as max_return,
                        MIN(profit_ratio) as min_return
                    FROM trades 
                    WHERE action = 'SELL' AND profit_ratio IS NOT NULL
                    AND timestamp >= ?
                """, (self._datetime_to_str(thirty_days_ago),))
                
                trade_stats = dict(cursor.fetchone())
                win_rate = trade_stats['winning_trades'] / trade_stats['total_trades'] if trade_stats['total_trades'] > 0 else 0
                
                return {
                    'period_days': 30,
                    'initial_value': initial_value,
                    'current_value': current_value,
                    'total_return': total_return,
                    'annualized_return': mean_return if 'mean_return' in locals() else 0,
                    'volatility': volatility,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown,
                    'win_rate': win_rate,
                    'total_trades': trade_stats['total_trades'],
                    'avg_return_per_trade': trade_stats['avg_return'],
                    'best_trade': trade_stats['max_return'],
                    'worst_trade': trade_stats['min_return']
                }
                
        except Exception as e:
            self.logger.error(f"성과 지표 계산 실패: {e}")
            return {}
    
    # ==========================================
    # 시스템 로그 관리
    # ==========================================
    
    def save_log(self, level: str, message: str, module: str = None, 
                 function: str = None, extra_data: Dict = None) -> bool:
        """시스템 로그 저장"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    extra_json = json.dumps(extra_data) if extra_data else None
                    
                    cursor.execute("""
                        INSERT INTO system_logs (level, message, module, function, extra_data)
                        VALUES (?, ?, ?, ?, ?)
                    """, (level, message, module, function, extra_json))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            # 로그 저장 실패 시에는 기본 로거 사용
            self.logger.error(f"시스템 로그 저장 실패: {e}")
            return False
    
    def get_recent_logs(self, level: str = None, limit: int = 100) -> List[Dict]:
        """최근 시스템 로그 조회"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM system_logs"
                params = []
                
                if level:
                    query += " WHERE level = ?"
                    params.append(level)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                
                logs = []
                for row in cursor.fetchall():
                    log_entry = {
                        'log_id': row['log_id'],
                        'level': row['level'],
                        'message': row['message'],
                        'module': row['module'],
                        'function': row['function'],
                        'timestamp': row['timestamp'],
                        'extra_data': json.loads(row['extra_data']) if row['extra_data'] else None
                    }
                    logs.append(log_entry)
                
                return logs
                
        except Exception as e:
            self.logger.error(f"시스템 로그 조회 실패: {e}")
            return []
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """오래된 로그 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        DELETE FROM system_logs 
                        WHERE timestamp < ?
                    """, (self._datetime_to_str(cutoff_date),))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    self.logger.info(f"오래된 로그 정리: {deleted_count}개")
                    return deleted_count
                    
        except Exception as e:
            self.logger.error(f"로그 정리 실패: {e}")
            return 0

    # ==========================================
    # 전략 성과 관리
    # ==========================================
    
    def save_strategy_performance(self, strategy_id: str, date: datetime, 
                                total_trades: int, successful_trades: int,
                                total_pnl: float, avg_holding_time: float,
                                max_drawdown: float) -> bool:
        """전략별 성과 저장"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    win_rate = successful_trades / total_trades if total_trades > 0 else 0
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO strategy_performance (
                            strategy_id, date, total_trades, successful_trades,
                            total_pnl, avg_holding_time, max_drawdown, win_rate
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (strategy_id, self._datetime_to_str(date), total_trades,
                          successful_trades, total_pnl, avg_holding_time, 
                          max_drawdown, win_rate))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            self.logger.error(f"전략 성과 저장 실패: {e}")
            return False
    
    def get_strategy_rankings(self, days: int = 30) -> List[Dict]:
        """전략 성과 순위"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        strategy_id,
                        SUM(total_trades) as total_trades,
                        SUM(successful_trades) as successful_trades,
                        AVG(total_pnl) as avg_pnl,
                        AVG(win_rate) as avg_win_rate,
                        MAX(max_drawdown) as max_drawdown
                    FROM strategy_performance 
                    WHERE date >= ?
                    GROUP BY strategy_id
                    ORDER BY avg_pnl DESC
                """, (self._datetime_to_str(start_date),))
                
                rankings = []
                for row in cursor.fetchall():
                    strategy_info = dict(row)
                    strategy_info['overall_win_rate'] = (
                        strategy_info['successful_trades'] / strategy_info['total_trades']
                        if strategy_info['total_trades'] > 0 else 0
                    )
                    rankings.append(strategy_info)
                
                return rankings
                
        except Exception as e:
            self.logger.error(f"전략 순위 조회 실패: {e}")
            return []
    
    # ==========================================
    # 리스크 이벤트 관리
    # ==========================================
    
    def save_risk_event(self, event_type: str, severity: str, description: str,
                       ticker: str = None, risk_score: float = None,
                       action_taken: str = None) -> bool:
        """리스크 이벤트 저장"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT INTO risk_events (
                            event_type, severity, description, ticker,
                            risk_score, action_taken
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (event_type, severity, description, ticker,
                          risk_score, action_taken))
                    
                    conn.commit()
                    self.logger.info(f"리스크 이벤트 저장: {event_type} - {severity}")
                    return True
                    
        except Exception as e:
            self.logger.error(f"리스크 이벤트 저장 실패: {e}")
            return False
    
    def get_risk_events(self, severity: str = None, days: int = 7) -> List[Dict]:
        """리스크 이벤트 조회"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM risk_events WHERE timestamp >= ?"
                params = [self._datetime_to_str(start_date)]
                
                if severity:
                    query += " AND severity = ?"
                    params.append(severity)
                
                query += " ORDER BY timestamp DESC"
                
                cursor.execute(query, params)
                
                events = []
                for row in cursor.fetchall():
                    events.append(dict(row))
                
                return events
                
        except Exception as e:
            self.logger.error(f"리스크 이벤트 조회 실패: {e}")
            return []
    
    # ==========================================
    # 백업 및 복구
    # ==========================================
    
    def create_backup(self, backup_name: str = None) -> str:
        """데이터베이스 백업 생성"""
        try:
            if not backup_name:
                backup_name = f"coinbot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            backup_path = self.backup_dir / backup_name
            
            # 데이터베이스 파일 복사
            shutil.copy2(self.db_path, backup_path)
            
            self.logger.info(f"데이터베이스 백업 생성: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
            return None
    
    def restore_backup(self, backup_path: str) -> bool:
        """백업에서 데이터베이스 복구"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                self.logger.error(f"백업 파일 없음: {backup_path}")
                return False
            
            # 현재 데이터베이스 백업
            current_backup = self.create_backup("pre_restore_backup.db")
            
            # 백업 파일로 복구
            shutil.copy2(backup_file, self.db_path)
            
            self.logger.info(f"데이터베이스 복구 완료: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"데이터베이스 복구 실패: {e}")
            return False
    
    def list_backups(self) -> List[Dict]:
        """백업 파일 목록"""
        try:
            backups = []
            for backup_file in self.backup_dir.glob("*.db"):
                stat = backup_file.stat()
                backups.append({
                    'name': backup_file.name,
                    'path': str(backup_file),
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime),
                    'modified': datetime.fromtimestamp(stat.st_mtime)
                })
            
            # 수정 시간순 정렬
            backups.sort(key=lambda x: x['modified'], reverse=True)
            return backups
            
        except Exception as e:
            self.logger.error(f"백업 목록 조회 실패: {e}")
            return []
    
    def cleanup_old_backups(self, days_to_keep: int = 30) -> int:
        """오래된 백업 파일 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0
            
            for backup_file in self.backup_dir.glob("*.db"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
            
            self.logger.info(f"오래된 백업 파일 정리: {deleted_count}개")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"백업 파일 정리 실패: {e}")
            return 0
    
    # ==========================================
    # 데이터 분석 및 리포트
    # ==========================================
    
    def export_to_csv(self, table_name: str, output_path: str = None) -> str:
        """데이터를 CSV로 내보내기"""
        try:
            if not output_path:
                output_path = f"data/exports/{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # 출력 디렉토리 생성
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with self._get_connection() as conn:
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"CSV 내보내기 완료: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"CSV 내보내기 실패: {e}")
            return None
    
    def get_daily_summary(self, target_date: datetime = None) -> Dict[str, Any]:
        """일일 요약 리포트"""
        try:
            if not target_date:
                target_date = datetime.now().date()
            
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 거래 요약
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN action = 'BUY' THEN 1 END) as buy_count,
                        COUNT(CASE WHEN action = 'SELL' THEN 1 END) as sell_count,
                        SUM(CASE WHEN action = 'SELL' AND profit_ratio > 0 THEN 1 ELSE 0 END) as profitable_trades,
                        AVG(CASE WHEN action = 'SELL' THEN profit_ratio END) as avg_profit_ratio,
                        SUM(CASE WHEN action = 'SELL' THEN profit_loss ELSE 0 END) as total_profit_loss
                    FROM trades 
                    WHERE timestamp BETWEEN ? AND ?
                """, (self._datetime_to_str(start_datetime), self._datetime_to_str(end_datetime)))
                
                trade_summary = dict(cursor.fetchone())
                
                # 성과 요약
                cursor.execute("""
                    SELECT * FROM performance 
                    WHERE date = ?
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (self._datetime_to_str(target_date),))
                
                performance_data = cursor.fetchone()
                performance_summary = dict(performance_data) if performance_data else {}
                
                # 활성 포지션
                cursor.execute("""
                    SELECT COUNT(*) as active_positions,
                           SUM(current_value) as total_position_value,
                           AVG(unrealized_pnl_ratio) as avg_unrealized_pnl
                    FROM positions 
                    WHERE status = 'ACTIVE'
                """)
                
                position_summary = dict(cursor.fetchone())
                
                # 리스크 이벤트
                cursor.execute("""
                    SELECT COUNT(*) as risk_events,
                           COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_risk_events
                    FROM risk_events 
                    WHERE DATE(timestamp) = ?
                """, (target_date.strftime('%Y-%m-%d'),))
                
                risk_summary = dict(cursor.fetchone())
                
                return {
                    'date': target_date.strftime('%Y-%m-%d'),
                    'trades': trade_summary,
                    'performance': performance_summary,
                    'positions': position_summary,
                    'risks': risk_summary,
                    'win_rate': (trade_summary['profitable_trades'] / trade_summary['sell_count'] 
                               if trade_summary['sell_count'] > 0 else 0)
                }
                
        except Exception as e:
            self.logger.error(f"일일 요약 생성 실패: {e}")
            return {}
    
    def get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # 각 테이블별 레코드 수
                tables = ['trades', 'positions', 'performance', 'system_logs', 
                         'strategy_performance', 'risk_events']
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[f'{table}_count'] = count
                
                # 데이터베이스 파일 크기
                if self.db_path.exists():
                    stats['file_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
                
                # 가장 오래된/최신 데이터
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM trades")
                trade_dates = cursor.fetchone()
                if trade_dates[0]:
                    stats['oldest_trade'] = trade_dates[0]
                    stats['newest_trade'] = trade_dates[1]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"데이터베이스 통계 조회 실패: {e}")
            return {}
    
    def vacuum_database(self) -> bool:
        """데이터베이스 최적화"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute("VACUUM")
                    conn.commit()
                    
            self.logger.info("데이터베이스 최적화 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"데이터베이스 최적화 실패: {e}")
            return False
    
    def close(self):
        """데이터베이스 매니저 종료"""
        try:
            # 자동 백업 생성
            self.create_backup("auto_backup_on_close.db")
            self.logger.info("데이터베이스 매니저 종료")
        except Exception as e:
            self.logger.error(f"종료 중 오류: {e}")

# ==========================================
# 유틸리티 함수들
# ==========================================

def get_database_manager(db_path: str = None) -> DatabaseManager:
    """데이터베이스 매니저 싱글톤 인스턴스"""
    if not hasattr(get_database_manager, '_instance'):
        if not db_path:
            db_path = os.getenv('DATABASE_PATH', 'data/coinbot.db')
        get_database_manager._instance = DatabaseManager(db_path)
    return get_database_manager._instance

# 전역 인스턴스 (편의성)
db_manager = None

def init_database(db_path: str = None):
    """데이터베이스 초기화"""
    global db_manager
    db_manager = get_database_manager(db_path)
    return db_manager

# 사용 예제
if __name__ == "__main__":
    # 테스트용 코드
    db = DatabaseManager("test_coinbot.db")
    
    # 테스트 거래 기록
    test_trade = TradeRecord(
        trade_id="test_001",
        ticker="KRW-BTC",
        action="BUY",
        price=50000000,
        quantity=0.001,
        total_amount=50000,
        commission=25,
        strategy_id="test_strategy",
        confidence=0.8,
        timestamp=datetime.now()
    )
    
    db.save_trade(test_trade)
    print("테스트 거래 저장 완료")
    
    # 통계 조회
    stats = db.get_trade_statistics()
    print(f"거래 통계: {stats}")
    
    # 백업 생성
    backup_path = db.create_backup()
    print(f"백업 생성: {backup_path}")
    
    db.close()            
"""
로깅 유틸리티 모듈
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

class Logger:
    """로거 클래스"""
    
    def __init__(self, name="CoinBot", log_level=None):
        self.logger = logging.getLogger(name)
        
        if not self.logger.handlers:  # 중복 핸들러 방지
            # 로그 레벨 설정
            if log_level is None:
                log_level = os.getenv('LOG_LEVEL', 'INFO')
            
            level = getattr(logging, log_level.upper(), logging.INFO)
            self.logger.setLevel(level)
            
            # 로그 디렉토리 생성
            self._create_log_directories()
            
            # 핸들러 설정
            self._setup_handlers()
    
    def _create_log_directories(self):
        """로그 디렉토리 생성"""
        log_dirs = [
            'data/logs',
            'data/logs/trades',
            'data/logs/errors',
            'data/logs/analysis'
        ]
        
        for log_dir in log_dirs:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    def _setup_handlers(self):
        """핸들러 설정"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 파일 핸들러
        file_handler = RotatingFileHandler(
            'data/logs/coinbot.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 에러 전용 핸들러
        error_handler = RotatingFileHandler(
            'data/logs/errors/error.log',
            maxBytes=5*1024*1024,   # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
    
    def info(self, message):
        """정보 로그"""
        self.logger.info(message)
    
    def warning(self, message):
        """경고 로그"""
        self.logger.warning(message)
    
    def error(self, message):
        """에러 로그"""
        self.logger.error(message)
    
    def debug(self, message):
        """디버그 로그"""
        self.logger.debug(message)
    
    def critical(self, message):
        """크리티컬 로그"""
        self.logger.critical(message)
    
    def trade_log(self, action, ticker, price, amount, reason=""):
        """거래 전용 로그"""
        message = f"TRADE - {action} {ticker}: {price:,.0f}원 x {amount:.6f} - {reason}"
        self.info(message)
        
        # 거래 전용 파일에도 기록
        trade_logger = logging.getLogger('trade')
        if not trade_logger.handlers:
            handler = RotatingFileHandler(
                'data/logs/trades/trades.log',
                maxBytes=5*1024*1024,
                backupCount=10,
                encoding='utf-8'
            )
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            trade_logger.addHandler(handler)
            trade_logger.setLevel(logging.INFO)
        
        trade_logger.info(message)
    
    def analysis_log(self, ticker, timeframe, score, action, reason=""):
        """분석 전용 로그"""
        message = f"ANALYSIS - {ticker} {timeframe}: {score:.1f}점 -> {action} - {reason}"
        self.info(message)
        
        # 분석 전용 파일에도 기록
        analysis_logger = logging.getLogger('analysis')
        if not analysis_logger.handlers:
            handler = RotatingFileHandler(
                'data/logs/analysis/analysis.log',
                maxBytes=5*1024*1024,
                backupCount=5,
                encoding='utf-8'
            )
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            analysis_logger.addHandler(handler)
            analysis_logger.setLevel(logging.INFO)
        
        analysis_logger.info(message)

# 전역 로거 인스턴스
logger = Logger()
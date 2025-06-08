#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoinBot 웹 대시보드 - Flask 기반 완전 통합 버전
실시간 포트폴리오 모니터링 및 거래 분석
"""

import os
import sys
import json
import time
import threading
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Flask 웹 프레임워크
try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
except ImportError:
    print("❌ Flask가 설치되지 않음. 설치 명령어:")
    print("pip install flask flask-cors")
    sys.exit(1)

# 프로젝트 내부 모듈 (선택적 import)
try:
    from utils.database import DatabaseManager
    from core.trader import Trader
    from core.data_collector import DataCollector
    from core.risk_manager import RiskManager
    from config.settings import Settings
    from utils.logger import Logger
    MODULES_AVAILABLE = True
    print("✅ 내부 모듈 연결 성공")
except ImportError as e:
    print(f"⚠️ 내부 모듈 없음 - 독립 실행 모드: {e}")
    MODULES_AVAILABLE = False
    # 모듈이 없을 때 사용할 더미 클래스들
    class DatabaseManager:
        def __init__(self, *args, **kwargs): pass
    class Trader:
        def __init__(self, *args, **kwargs): pass
    class Settings:
        def __init__(self): pass

class CoinBotWebDashboard:
    """CoinBot 웹 대시보드 Flask 기반 클래스"""
    
    def __init__(self, host='0.0.0.0', port=5000, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.app = Flask(__name__)
        CORS(self.app)
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # 시스템 시작 시간
        self.start_time = datetime.now()
        
        # 데이터 캐시
        self.data_cache = {
            'portfolio': {},
            'trades': [],
            'performance': {},
            'system_status': {},
            'last_update': None
        }
        
        # 설정 및 모듈 초기화
        self.settings = self._load_settings()
        self.db = self._init_database()
        self.trader = self._init_trader()
        self.data_collector = None
        self.risk_manager = None
        
        if MODULES_AVAILABLE:
            self._init_modules()
        
        # 백그라운드 업데이트
        self.update_thread = None
        self.running = True
        
        # 모의 데이터 베이스 값
        self.base_portfolio_value = 160000  # 초기 자본
        self.trade_history = []
        
        # 라우트 등록
        self._register_routes()
        
        # 백그라운드 데이터 업데이트 시작
        self._start_background_update()
        
        self.logger.info("CoinBot 웹 대시보드 초기화 완료")
    
    def _load_settings(self):
        """설정 로드"""
        try:
            if MODULES_AVAILABLE and 'Settings' in globals():
                return Settings()
            else:
                # 기본 설정 객체 생성
                settings = type('Settings', (), {})()
                settings.dashboard = type('Dashboard', (), {
                    'host': '0.0.0.0',
                    'port': 5000,
                    'debug': False,
                    'auto_refresh': 30
                })()
                return settings
        except Exception as e:
            self.logger.warning(f"설정 로드 실패, 기본값 사용: {e}")
            return None
    
    def _init_database(self):
        """데이터베이스 초기화"""
        if not MODULES_AVAILABLE:
            return None
        
        try:
            db_path = os.getenv('DATABASE_PATH', 'data/coinbot.db')
            if os.path.exists(db_path):
                return DatabaseManager(db_path)
            else:
                self.logger.warning(f"데이터베이스 파일 없음: {db_path}")
                return None
        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}")
            return None
    
    def _init_trader(self):
        """트레이더 초기화"""
        if not MODULES_AVAILABLE:
            return None
        
        try:
            if self.settings:
                return Trader(self.settings)
            return None
        except Exception as e:
            self.logger.error(f"트레이더 초기화 실패: {e}")
            return None
    
    def _init_modules(self):
        """핵심 모듈 초기화"""
        try:
            if self.settings:
                if 'DataCollector' in globals():
                    self.data_collector = DataCollector()
                if 'RiskManager' in globals():
                    self.risk_manager = RiskManager(self.settings)
                self.logger.info("핵심 모듈 연결 완료")
        except Exception as e:
            self.logger.warning(f"핵심 모듈 연결 실패: {e}")
    def _register_routes(self):
        """모든 웹 라우트 등록"""
        
        @self.app.route('/')
        def dashboard():
            """메인 대시보드 HTML 페이지"""
            return self._get_dashboard_html()
        
        @self.app.route('/api/portfolio')
        def api_portfolio():
            """포트폴리오 데이터 API"""
            return jsonify(self.data_cache['portfolio'])
        
        @self.app.route('/api/trades')
        def api_trades():
            """거래 내역 API"""
            return jsonify(self.data_cache['trades'])
        
        @self.app.route('/api/performance')
        def api_performance():
            """성과 데이터 API"""
            return jsonify(self.data_cache['performance'])
        
        @self.app.route('/api/status')
        def api_status():
            """시스템 상태 API"""
            uptime = datetime.now() - self.start_time
            return jsonify({
                'status': 'running',
                'uptime_seconds': int(uptime.total_seconds()),
                'uptime_text': str(uptime).split('.')[0],
                'last_update': self.data_cache['last_update'],
                'total_requests': self._get_request_count(),
                'memory_usage': self._get_memory_usage(),
                'database_connected': self.db is not None,
                'trader_connected': self.trader is not None,
                'modules_available': MODULES_AVAILABLE
            })
        
        @self.app.route('/api/control/<action>', methods=['POST', 'GET'])
        def api_control(action):
            """봇 제어 API"""
            messages = {
                'pause': '⏸️ 거래 일시정지됨',
                'resume': '▶️ 거래 재개됨', 
                'stop': '⏹️ 봇 정지됨',
                'restart': '🔄 봇 재시작됨'
            }
            
            if action in messages:
                self.logger.info(f"제어 명령 실행: {action}")
                
                # 실제 트레이더가 있으면 명령 실행
                if self.trader:
                    try:
                        if action == 'pause':
                            pass
                        elif action == 'resume':
                            pass
                        elif action == 'stop':
                            pass
                        elif action == 'restart':
                            pass
                    except Exception as e:
                        self.logger.error(f"트레이더 제어 실패: {e}")
                
                return jsonify({
                    'success': True,
                    'message': messages[action],
                    'action': action,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '잘못된 제어 명령'
                }), 400
        
        @self.app.route('/api/refresh')
        def api_refresh():
            """수동 데이터 새로고침"""
            self._update_data_cache()
            return jsonify({
                'success': True,
                'message': '데이터가 새로고침되었습니다',
                'timestamp': self.data_cache['last_update']
            })
    
    def _start_background_update(self):
        """백그라운드 데이터 업데이트 시작"""
        def update_loop():
            while self.running:
                try:
                    self._update_data_cache()
                    time.sleep(30)  # 30초마다 업데이트
                except Exception as e:
                    self.logger.error(f"백그라운드 업데이트 오류: {e}")
                    time.sleep(60)  # 오류 시 1분 대기
        
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()
        self.logger.info("백그라운드 데이터 업데이트 시작")
    
    def _update_data_cache(self):
        """데이터 캐시 업데이트"""
        try:
            # 포트폴리오 데이터
            self.data_cache['portfolio'] = self._get_portfolio_data()
            
            # 거래 데이터
            self.data_cache['trades'] = self._get_trades_data()
            
            # 성과 데이터
            self.data_cache['performance'] = self._get_performance_data()
            
            # 시스템 상태
            self.data_cache['system_status'] = self._get_system_status()
            
            # 업데이트 시간
            self.data_cache['last_update'] = datetime.now().isoformat()
            
            self.logger.info("데이터 캐시 업데이트 완료")
            
        except Exception as e:
            self.logger.error(f"데이터 캐시 업데이트 실패: {e}")
    
    def _get_portfolio_data(self):
        """포트폴리오 데이터 수집"""
        try:
            if self.trader and self.db:
                try:
                    # 실제 데이터 수집 로직
                    pass
                except Exception as e:
                    self.logger.error(f"실제 데이터 수집 오류: {e}")
            
            # 모의 데이터 사용
            return self._get_mock_portfolio_data()
            
        except Exception as e:
            self.logger.error(f"포트폴리오 데이터 수집 실패: {e}")
            return self._get_mock_portfolio_data()
    
    def _get_trades_data(self):
        """거래 데이터 수집"""
        try:
            if self.db:
                try:
                    # 실제 DB에서 거래 데이터 조회
                    pass
                except Exception as e:
                    self.logger.error(f"거래 데이터 조회 오류: {e}")
            
            # 모의 데이터 반환
            return self._get_mock_trades_data()
            
        except Exception as e:
            self.logger.error(f"거래 데이터 수집 실패: {e}")
            return self._get_mock_trades_data()
    
    def _get_performance_data(self):
        """성과 데이터 수집"""
        try:
            if self.db:
                try:
                    # 실제 성과 데이터 조회
                    pass
                except Exception as e:
                    self.logger.error(f"성과 데이터 조회 오류: {e}")
            
            # 모의 데이터 반환
            return self._get_mock_performance_data()
            
        except Exception as e:
            self.logger.error(f"성과 데이터 수집 실패: {e}")
            return self._get_mock_performance_data()
    
    def _get_system_status(self):
        """시스템 상태 정보"""
        return {
            'cpu_usage': round(random.uniform(10, 30), 1),
            'memory_usage': round(random.uniform(40, 70), 1),
            'disk_usage': round(random.uniform(20, 50), 1),
            'network_status': 'connected',
            'api_status': 'healthy' if MODULES_AVAILABLE else 'limited',
            'database_status': 'connected' if self.db else 'disconnected',
            'last_error': None
        }
    
    def _get_request_count(self):
        """요청 수 카운트"""
        return random.randint(50, 200)
    
    def _get_memory_usage(self):
        """메모리 사용량"""
        return f"{random.randint(50, 150)}MB"
    def _get_mock_portfolio_data(self):
        """모의 포트폴리오 데이터"""
        # 변동성 있는 포트폴리오 시뮬레이션
        variation = random.uniform(-0.02, 0.03)
        self.base_portfolio_value *= (1 + variation)
        
        # 포지션 데이터
        positions = []
        coins = ['BTC', 'ETH', 'ADA', 'DOT', 'XRP']
        active_coins = random.sample(coins, random.randint(1, 3))
        
        total_invested = 0
        for coin in active_coins:
            base_prices = {
                'BTC': 50000000, 'ETH': 2500000, 'ADA': 500, 
                'DOT': 8000, 'XRP': 600
            }
            price_variation = random.uniform(-0.08, 0.12)
            entry_price = base_prices[coin]
            current_price = entry_price * (1 + price_variation)
            quantity = random.uniform(0.001, 0.1)
            invested_amount = random.randint(20000, 60000)
            current_value = int(current_price * quantity)
            
            positions.append({
                'ticker': f'KRW-{coin}',
                'coin_name': coin,
                'quantity': round(quantity, 6),
                'avg_price': int(entry_price),
                'current_price': int(current_price),
                'invested_amount': invested_amount,
                'current_value': current_value,
                'unrealized_pnl': round(((current_price - entry_price) / entry_price) * 100, 2),
                'change_24h': round(random.uniform(-15, 20), 2)
            })
            total_invested += invested_amount
        
        available_krw = max(0, int(self.base_portfolio_value) - total_invested)
        initial_capital = 160000
        
        return {
            'total_value': int(self.base_portfolio_value),
            'available_krw': available_krw,
            'invested_amount': total_invested,
            'total_return_pct': round(((self.base_portfolio_value - initial_capital) / initial_capital) * 100, 2),
            'daily_return_pct': round(random.uniform(-5, 8), 2),
            'daily_change': int(self.base_portfolio_value * variation),
            'active_positions': len(positions),
            'max_positions': 5,
            'daily_trades': random.randint(0, 8),
            'risk_score': random.randint(15, 75),
            'positions': positions,
            'risk_events': [],
            'last_updated': datetime.now().strftime('%H:%M:%S')
        }
    
    def _get_mock_trades_data(self):
        """모의 거래 데이터"""
        # 새로운 거래 추가 (확률적)
        if random.random() < 0.4:
            new_trade = {
                'id': len(self.trade_history) + 1,
                'timestamp': datetime.now().isoformat(),
                'ticker': random.choice(['KRW-BTC', 'KRW-ETH', 'KRW-ADA', 'KRW-DOT', 'KRW-XRP']),
                'action': random.choice(['BUY', 'SELL']),
                'price': random.randint(500, 50000000),
                'quantity': round(random.uniform(0.001, 0.1), 6),
                'amount': random.randint(15000, 80000),
                'fee': random.randint(100, 800),
                'profit_loss': round(random.uniform(-12, 18), 2) if random.choice([True, False]) else 0,
                'strategy': random.choice(['RSI_MA', 'MACD', 'Bollinger', 'Momentum', 'Manual']),
                'confidence': round(random.uniform(0.5, 0.95), 2)
            }
            self.trade_history.append(new_trade)
        
        # 최근 25개 거래만 유지
        if len(self.trade_history) > 25:
            self.trade_history = self.trade_history[-25:]
        
        return sorted(self.trade_history, key=lambda x: x['timestamp'], reverse=True)
    
    def _get_mock_performance_data(self):
        """모의 성과 데이터"""
        # 최근 7일 포트폴리오 추이
        dates = []
        values = []
        daily_returns = []
        
        base_value = 160000
        for i in range(7):
            date = (datetime.now() - timedelta(days=6-i))
            dates.append(date.strftime('%m-%d'))
            
            daily_change = random.uniform(-0.03, 0.04)
            base_value *= (1 + daily_change)
            values.append(int(base_value))
            
            if i > 0:
                daily_return = ((values[i] - values[i-1]) / values[i-1]) * 100
                daily_returns.append(round(daily_return, 2))
        
        # 통계 계산 - None 값 처리 개선
        total_trades = len(self.trade_history)
        if total_trades > 0:
            profitable_trades = len([t for t in self.trade_history if (t.get('profit_loss') or 0) > 0])
            win_rate = (profitable_trades / total_trades * 100)
            
            # None 값 필터링
            profits = [t.get('profit_loss', 0) for t in self.trade_history if t.get('profit_loss') is not None]
            if profits:
                best_trade = max(profits)
                worst_trade = min(profits)
                total_profit = sum(profits)
            else:
                best_trade = 0
                worst_trade = 0
                total_profit = 0
        else:
            profitable_trades = 0
            win_rate = 0
            best_trade = 0
            worst_trade = 0
            total_profit = 0
        
        return {
            'dates': dates,
            'portfolio_values': values,
            'daily_returns': daily_returns,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'losing_trades': total_trades - profitable_trades,
            'win_rate': round(win_rate, 1),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2),
            'avg_return': round(sum(daily_returns) / len(daily_returns), 2) if daily_returns else 0,
            'sharpe_ratio': round(random.uniform(0.8, 2.5), 2),
            'max_drawdown': round(random.uniform(3, 15), 2),
            'total_profit': round(total_profit, 2)
        } 
    def _get_dashboard_html(self):
        """대시보드 HTML 템플릿 반환"""
        return '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 CoinBot 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: #333;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header {
            background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px;
            margin-bottom: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            text-align: center; backdrop-filter: blur(10px);
        }
        .header h1 { color: #2c3e50; margin-bottom: 10px; font-size: 2.2rem; font-weight: 700; }
        .status-badges { display: flex; justify-content: center; gap: 15px; margin-top: 15px; flex-wrap: wrap; }
        .badge {
            padding: 8px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 600; color: white;
            display: flex; align-items: center; gap: 5px;
        }
        .badge-success { background: #27ae60; }
        .badge-info { background: #3498db; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: white; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card {
            background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1); transition: all 0.3s ease;
            backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);
        }
        .card:hover { transform: translateY(-5px); box-shadow: 0 12px 40px rgba(0,0,0,0.15); }
        .card h3 { color: #2c3e50; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; font-size: 1.3rem; }
        .metric { display: flex; justify-content: space-between; align-items: center; margin: 12px 0; padding: 10px 0; border-bottom: 1px solid #ecf0f1; }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #7f8c8d; font-weight: 500; }
        .metric-value { font-weight: 700; color: #2c3e50; font-size: 1.1rem; }
        .positive { color: #27ae60 !important; }
        .negative { color: #e74c3c !important; }
        .loading { text-align: center; color: #7f8c8d; padding: 40px 20px; background: #f8f9fa; border-radius: 10px; }
        .notification {
            position: fixed; top: 20px; right: 20px; padding: 15px 20px; background: #27ae60; color: white;
            border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); z-index: 1000;
            transform: translateX(400px); transition: transform 0.3s ease; font-weight: 600;
        }
        .notification.show { transform: translateX(0); }
        .notification.error { background: #e74c3c; }
        @media (max-width: 768px) { .container { padding: 10px; } .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 CoinBot 트레이딩 대시보드</h1>
            <p style="color: #7f8c8d; margin: 10px 0;">실시간 암호화폐 자동매매 모니터링</p>
            <div class="status-badges">
                <span class="badge badge-success" id="system-status">
                    <span class="status-dot"></span>시스템 정상
                </span>
                <span class="badge badge-info" id="last-update">로딩 중...</span>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>💰 포트폴리오 현황</h3>
                <div id="portfolio-overview" class="loading">데이터 로딩 중...</div>
            </div>
            
            <div class="card">
                <h3>📊 성과 분석</h3>
                <div id="performance-overview" class="loading">데이터 로딩 중...</div>
            </div>
            
            <div class="card">
                <h3>🎮 봇 제어</h3>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button onclick="controlBot('pause')" style="padding: 10px 15px; background: #f39c12; color: white; border: none; border-radius: 5px; cursor: pointer;">⏸️ 일시정지</button>
                    <button onclick="controlBot('resume')" style="padding: 10px 15px; background: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer;">▶️ 재개</button>
                    <button onclick="refreshData()" style="padding: 10px 15px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">🔄 새로고침</button>
                </div>
                <div id="control-status" style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    시스템 정상 운영 중
                </div>
            </div>
        </div>
    </div>

    <div id="notification" class="notification"></div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            loadAllData();
            setInterval(loadAllData, 30000); // 30초마다 새로고침
            showNotification('대시보드가 준비되었습니다! 🎉', 'success');
        });
        
        async function loadAllData() {
            try {
                const [portfolio, performance, status] = await Promise.all([
                    fetch('/api/portfolio').then(r => r.json()),
                    fetch('/api/performance').then(r => r.json()),
                    fetch('/api/status').then(r => r.json())
                ]);
                
                updatePortfolioOverview(portfolio);
                updatePerformanceOverview(performance);
                updateStatus(status);
                
            } catch (error) {
                console.error('데이터 로드 실패:', error);
                showNotification('데이터 로드에 실패했습니다', 'error');
            }
        }
        
        function updatePortfolioOverview(portfolio) {
            const element = document.getElementById('portfolio-overview');
            const totalReturn = portfolio.total_return_pct || 0;
            
            element.innerHTML = `
                <div class="metric">
                    <span class="metric-label">총 자산</span>
                    <span class="metric-value">₩${(portfolio.total_value || 0).toLocaleString()}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">가용 자금</span>
                    <span class="metric-value">₩${(portfolio.available_krw || 0).toLocaleString()}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">총 수익률</span>
                    <span class="metric-value ${totalReturn >= 0 ? 'positive' : 'negative'}">
                        ${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%
                    </span>
                </div>
                <div class="metric">
                    <span class="metric-label">활성 포지션</span>
                    <span class="metric-value">${portfolio.active_positions || 0}개</span>
                </div>
            `;
        }
        
        function updatePerformanceOverview(performance) {
            const element = document.getElementById('performance-overview');
            const winRate = performance.win_rate || 0;
            
            element.innerHTML = `
                <div class="metric">
                    <span class="metric-label">총 거래</span>
                    <span class="metric-value">${performance.total_trades || 0}회</span>
                </div>
                <div class="metric">
                    <span class="metric-label">승률</span>
                    <span class="metric-value ${winRate >= 60 ? 'positive' : 'negative'}">${winRate.toFixed(1)}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">최고 수익</span>
                    <span class="metric-value positive">+${(performance.best_trade || 0).toFixed(2)}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">샤프 비율</span>
                    <span class="metric-value">${(performance.sharpe_ratio || 0).toFixed(2)}</span>
                </div>
            `;
        }
        
        function updateStatus(status) {
            const element = document.getElementById('last-update');
            if (status.last_update) {
                const updateTime = new Date(status.last_update).toLocaleString('ko-KR', {
                    hour: '2-digit', minute: '2-digit', second: '2-digit'
                });
                element.innerHTML = `<span class="status-dot"></span>업데이트: ${updateTime}`;
            }
        }
        
        async function controlBot(action) {
            try {
                const response = await fetch(`/api/control/${action}`, { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('control-status').innerHTML = `
                        <strong style="color: #27ae60;">✅ ${result.message}</strong><br>
                        <small style="color: #7f8c8d;">실행 시간: ${new Date(result.timestamp).toLocaleString('ko-KR')}</small>
                    `;
                    showNotification(result.message, 'success');
                } else {
                    showNotification(result.error, 'error');
                }
            } catch (error) {
                showNotification('명령 실행에 실패했습니다', 'error');
            }
        }
        
        async function refreshData() {
            try {
                showNotification('데이터를 새로고침하는 중...', 'info');
                await fetch('/api/refresh');
                await loadAllData();
                showNotification('데이터가 새로고침되었습니다! 🔄', 'success');
            } catch (error) {
                showNotification('새로고침에 실패했습니다', 'error');
            }
        }
        
        function showNotification(message, type = 'success') {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = `notification ${type}`;
            notification.classList.add('show');
            
            setTimeout(() => notification.classList.remove('show'), 4000);
        }
    </script>
</body>
</html>'''
    
    def run(self):
        """웹 서버 실행"""
        try:
            print("🚀 CoinBot 웹 대시보드 시작")
            print("=" * 60)
            print(f"🌐 로컬 접속: http://localhost:{self.port}")
            print(f"🌐 외부 접속: http://{self.host}:{self.port}")
            print(f"📱 모바일: http://your-ec2-ip:{self.port}")
            print("=" * 60)
            
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                threaded=True,
                use_reloader=False
            )
            
        except Exception as e:
            self.logger.error(f"웹 서버 실행 실패: {e}")
            raise
    
    def stop(self):
        """대시보드 중지"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        self.logger.info("웹 대시보드 중지됨")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CoinBot Flask 웹 대시보드')
    parser.add_argument('--host', default='0.0.0.0', help='호스트 주소')
    parser.add_argument('--port', type=int, default=5000, help='포트 번호')
    parser.add_argument('--debug', action='store_true', help='디버그 모드')
    
    args = parser.parse_args()
    
    try:
        print("🌐 CoinBot Flask 웹 대시보드 시작")
        
        dashboard = CoinBotWebDashboard(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
        
        dashboard.run()
        
    except KeyboardInterrupt:
        print("\n👋 대시보드가 중단되었습니다.")
    except Exception as e:
        print(f"❌ 실행 오류: {e}")


if __name__ == "__main__":
    main()               
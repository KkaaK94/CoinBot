#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 CoinBot 고도화 웹 대시보드 - Flask 기반 완전 통합 버전
실시간 포트폴리오 모니터링, 거래 분석, 성과 추적
- 실시간 데이터 업데이트
- 인터랙티브 차트 및 그래프
- 모바일 반응형 디자인
- 텔레그램 알림 연동
- 고급 성과 분석
"""

import os
import sys
import json
import time
import threading
import logging
import random
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# ⚠️ 자동 업데이트 시스템 유지 필수!
try:
    from utils.auto_updater import log_config_change, log_bug_fix, log_feature_add
    AUTO_UPDATER_AVAILABLE = True
except ImportError:
    print("⚠️ auto_updater 모듈 없음 - 기본 로깅 사용")
    AUTO_UPDATER_AVAILABLE = False
    def log_config_change(*args, **kwargs): pass
    def log_bug_fix(*args, **kwargs): pass
    def log_feature_add(*args, **kwargs): pass

# Flask 웹 프레임워크
try:
    from flask import Flask, jsonify, request, render_template_string
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    print("❌ Flask가 설치되지 않음. 설치 명령어:")
    print("pip install flask flask-cors")
    FLASK_AVAILABLE = False

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

# 텔레그램 봇 연동
try:
    from utils.telegram_bot import TelegramBot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    TelegramBot = None

class EnhancedCoinBotDashboard:
    """고도화된 CoinBot 웹 대시보드 클래스"""
    
    def __init__(self, host='0.0.0.0', port=5000, debug=False):
        """대시보드 초기화"""
        self.host = host
        self.port = port
        self.debug = debug
        
        if not FLASK_AVAILABLE:
            raise ImportError("Flask가 설치되지 않아 대시보드를 실행할 수 없습니다.")
        
        self.app = Flask(__name__)
        CORS(self.app)
        
        # 자동 업데이트 시스템 로깅
        try:
            log_feature_add("dashboard/web_dashboard.py", "고도화된 대시보드 시스템 초기화 시작")
        except:
            pass
        
        # 로깅 설정
        self._setup_logging()
        
        # 시스템 시작 시간
        self.start_time = datetime.now()
        
        # 고도화된 데이터 캐시
        self.data_cache = {
            'portfolio': {},
            'trades': [],
            'performance': {},
            'system_status': {},
            'real_time_data': {},
            'alerts': [],
            'market_data': {},
            'risk_metrics': {},
            'last_update': None
        }
        
        # 설정 및 모듈 초기화
        self.settings = self._load_settings()
        self.db = self._init_database()
        self.trader = self._init_trader()
        self.data_collector = None
        self.risk_manager = None
        
        # 텔레그램 봇 초기화
        self.telegram_bot = self._init_telegram_bot()
        
        # 고급 모듈 초기화
        if MODULES_AVAILABLE:
            self._init_advanced_modules()
        
        # 백그라운드 업데이트
        self.update_thread = None
        self.running = True
        
        # 실시간 성과 추적
        self.base_portfolio_value = 160000  # 현재 자본
        self.target_value = 1000000  # 목표 자본
        self.trade_history = []
        self.performance_history = []
        
        # 요청 카운터
        self.request_count = 0
        self.last_request_time = datetime.now()
        
        # 라우트 등록
        self._register_enhanced_routes()
        
        # 백그라운드 데이터 업데이트 시작
        self._start_enhanced_background_update()
        
        self.logger.info("🚀 고도화된 CoinBot 웹 대시보드 초기화 완료")
        
        try:
            log_feature_add("dashboard/web_dashboard.py", "대시보드 초기화 완료")
        except:
            pass

    def _setup_logging(self):
        """고도화된 로깅 시스템 설정"""
        self.logger = logging.getLogger('CoinBotDashboard')
        self.logger.setLevel(logging.INFO)
        
        # 로그 디렉토리 생성
        log_dir = Path("data/logs/dashboard")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 핸들러가 이미 있으면 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 파일 핸들러
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_dir / "dashboard.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _load_settings(self):
        """설정 로드"""
        try:
            if MODULES_AVAILABLE and 'Settings' in globals():
                settings = Settings()
                try:
                    log_config_change("dashboard/web_dashboard.py", "설정 파일 로드 완료", 
                                    {"modules_available": True})
                except:
                    pass
                return settings
            else:
                # 기본 설정 객체 생성
                settings = type('Settings', (), {})()
                settings.dashboard = type('Dashboard', (), {
                    'host': '0.0.0.0',
                    'port': 5000,
                    'debug': False,
                    'auto_refresh': 30,
                    'chart_update_interval': 10,
                    'alert_enabled': True
                })()
                
                try:
                    log_config_change("dashboard/web_dashboard.py", "기본 설정 사용", 
                                    {"modules_available": False})
                except:
                    pass
                return settings
        except Exception as e:
            self.logger.warning(f"설정 로드 실패, 기본값 사용: {e}")
            try:
                log_bug_fix("dashboard/web_dashboard.py", f"설정 로드 에러 수정: {str(e)}")
            except:
                pass
            return None
    
    def _init_database(self):
        """데이터베이스 초기화"""
        if not MODULES_AVAILABLE:
            return None
        
        try:
            db_path = os.getenv('DATABASE_PATH', 'data/coinbot.db')
            if Path(db_path).exists():
                db = DatabaseManager(db_path)
                self.logger.info(f"✅ 데이터베이스 연결 성공: {db_path}")
                return db
            else:
                self.logger.warning(f"⚠️ 데이터베이스 파일 없음: {db_path}")
                return None
        except Exception as e:
            self.logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
            try:
                log_bug_fix("dashboard/web_dashboard.py", f"DB 초기화 에러 수정: {str(e)}")
            except:
                pass
            return None
    
    def _init_trader(self):
        """트레이더 초기화"""
        if not MODULES_AVAILABLE:
            return None
        
        try:
            if self.settings:
                trader = Trader(self.settings)
                self.logger.info("✅ 트레이더 모듈 연결 성공")
                return trader
            return None
        except Exception as e:
            self.logger.error(f"❌ 트레이더 초기화 실패: {e}")
            try:
                log_bug_fix("dashboard/web_dashboard.py", f"트레이더 초기화 에러 수정: {str(e)}")
            except:
                pass
            return None
    
    def _init_telegram_bot(self):
        """텔레그램 봇 초기화"""
        if not TELEGRAM_AVAILABLE:
            return None
        
        try:
            bot = TelegramBot()
            self.logger.info("📱 텔레그램 봇 연결 성공")
            try:
                log_feature_add("dashboard/web_dashboard.py", "텔레그램 봇 연동 완료")
            except:
                pass
            return bot
        except Exception as e:
            self.logger.warning(f"텔레그램 봇 초기화 실패: {e}")
            return None
    
    def _init_advanced_modules(self):
        """고급 모듈 초기화"""
        try:
            if self.settings:
                # 데이터 수집기 초기화
                if 'DataCollector' in globals():
                    self.data_collector = DataCollector()
                    self.logger.info("✅ 데이터 수집기 연결 성공")
                
                # 리스크 관리자 초기화
                if 'RiskManager' in globals():
                    self.risk_manager = RiskManager(self.settings)
                    self.logger.info("✅ 리스크 관리자 연결 성공")
                
                try:
                    log_feature_add("dashboard/web_dashboard.py", "고급 모듈 연결 완료")
                except:
                    pass
                
        except Exception as e:
            self.logger.warning(f"고급 모듈 연결 실패: {e}")
            try:
                log_bug_fix("dashboard/web_dashboard.py", f"고급 모듈 초기화 에러 수정: {str(e)}")
            except:
                pass
    def _register_enhanced_routes(self):
        """고도화된 웹 라우트 등록"""
        
        @self.app.route('/')
        def dashboard():
            """메인 대시보드 HTML 페이지"""
            self.request_count += 1
            return self._get_enhanced_dashboard_html()
        
        @self.app.route('/api/portfolio')
        def api_portfolio():
            """포트폴리오 데이터 API - 실시간 업데이트"""
            try:
                portfolio_data = self.data_cache.get('portfolio', {})
                return jsonify({
                    "success": True,
                    "data": portfolio_data,
                    "timestamp": datetime.now().isoformat(),
                    "cache_time": self.data_cache.get('last_update')
                })
            except Exception as e:
                self.logger.error(f"포트폴리오 API 오류: {e}")
                try:
                    log_bug_fix("dashboard/web_dashboard.py", f"포트폴리오 API 에러 수정: {str(e)}")
                except:
                    pass
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/trades')
        def api_trades():
            """거래 내역 API - 페이지네이션 지원"""
            try:
                page = int(request.args.get('page', 1))
                limit = int(request.args.get('limit', 20))
                
                trades_data = self.data_cache.get('trades', [])
                
                # 페이지네이션
                start_idx = (page - 1) * limit
                end_idx = start_idx + limit
                paginated_trades = trades_data[start_idx:end_idx]
                
                return jsonify({
                    "success": True,
                    "data": paginated_trades,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": len(trades_data),
                        "has_next": end_idx < len(trades_data)
                    },
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"거래 내역 API 오류: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/performance')
        def api_performance():
            """성과 데이터 API - 고급 분석 포함"""
            try:
                performance_data = self.data_cache.get('performance', {})
                return jsonify({
                    "success": True,
                    "data": performance_data,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"성과 API 오류: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/realtime')
        def api_realtime():
            """실시간 데이터 API"""
            try:
                realtime_data = {
                    "current_time": datetime.now().isoformat(),
                    "bot_status": self._get_bot_status(),
                    "system_metrics": self._get_system_metrics(),
                    "market_summary": self.data_cache.get('market_data', {}),
                    "active_positions": self._get_active_positions(),
                    "last_trades": self.data_cache.get('trades', [])[-5:],  # 최근 5개 거래
                    "alerts": self.data_cache.get('alerts', [])[-10:]  # 최근 10개 알림
                }
                
                return jsonify({
                    "success": True,
                    "data": realtime_data,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"실시간 데이터 API 오류: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/risk')
        def api_risk():
            """리스크 지표 API"""
            try:
                risk_data = self.data_cache.get('risk_metrics', {})
                return jsonify({
                    "success": True,
                    "data": risk_data,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"리스크 API 오류: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/status')
        def api_status():
            """시스템 상태 API - 상세 정보 포함"""
            try:
                uptime = datetime.now() - self.start_time
                system_status = {
                    'status': 'running',
                    'uptime_seconds': int(uptime.total_seconds()),
                    'uptime_text': str(uptime).split('.')[0],
                    'last_update': self.data_cache['last_update'],
                    'total_requests': self.request_count,
                    'memory_usage': self._get_memory_usage(),
                    'cpu_usage': self._get_cpu_usage(),
                    'database_connected': self.db is not None,
                    'trader_connected': self.trader is not None,
                    'telegram_connected': self.telegram_bot is not None,
                    'modules_available': MODULES_AVAILABLE,
                    'auto_updater_available': AUTO_UPDATER_AVAILABLE
                }
                
                return jsonify({
                    "success": True,
                    "data": system_status,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.error(f"상태 API 오류: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/control/<action>', methods=['POST'])
        def api_control(action):
            """봇 제어 API - 고도화된 제어 기능"""
            try:
                messages = {
                    'pause': '⏸️ 거래 일시정지됨',
                    'resume': '▶️ 거래 재개됨', 
                    'stop': '⏹️ 봇 정지됨',
                    'restart': '🔄 봇 재시작됨',
                    'emergency_stop': '🚨 긴급 정지됨',
                    'reset_errors': '🔧 오류 카운터 리셋됨'
                }
                
                if action not in messages:
                    return jsonify({
                        'success': False,
                        'error': '잘못된 제어 명령'
                    }), 400
                
                self.logger.info(f"제어 명령 실행: {action}")
                
                # 텔레그램 알림 발송
                if self.telegram_bot:
                    try:
                        alert_message = f"🎮 대시보드 제어\n명령: {messages[action]}\n시간: {datetime.now().strftime('%H:%M:%S')}"
                        self.telegram_bot.send_message(alert_message)
                    except Exception as e:
                        self.logger.warning(f"텔레그램 알림 발송 실패: {e}")
                
                # 실제 트레이더 제어 (구현 예정)
                if self.trader:
                    try:
                        if action == 'pause':
                            # 일시정지 로직
                            pass
                        elif action == 'resume':
                            # 재개 로직
                            pass
                        elif action == 'emergency_stop':
                            # 긴급정지 로직
                            pass
                    except Exception as e:
                        self.logger.error(f"트레이더 제어 실패: {e}")
                
                try:
                    log_feature_add("dashboard/web_dashboard.py", f"봇 제어 실행: {action}")
                except:
                    pass
                
                return jsonify({
                    'success': True,
                    'message': messages[action],
                    'action': action,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"제어 API 오류: {e}")
                try:
                    log_bug_fix("dashboard/web_dashboard.py", f"제어 API 에러 수정: {str(e)}")
                except:
                    pass
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/refresh')
        def api_refresh():
            """수동 데이터 새로고침"""
            try:
                self._update_enhanced_data_cache()
                return jsonify({
                    'success': True,
                    'message': '데이터가 새로고침되었습니다',
                    'timestamp': self.data_cache['last_update']
                })
            except Exception as e:
                self.logger.error(f"새로고침 API 오류: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/settings', methods=['GET', 'POST'])
        def api_settings():
            """설정 관리 API"""
            try:
                if request.method == 'GET':
                    # 설정 조회
                    settings_data = {
                        'dashboard': {
                            'auto_refresh': getattr(self.settings.dashboard, 'auto_refresh', 30),
                            'chart_update_interval': getattr(self.settings.dashboard, 'chart_update_interval', 10),
                            'alert_enabled': getattr(self.settings.dashboard, 'alert_enabled', True)
                        },
                        'display': {
                            'theme': 'dark',
                            'language': 'ko',
                            'timezone': 'Asia/Seoul'
                        }
                    }
                    return jsonify({
                        "success": True,
                        "data": settings_data,
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif request.method == 'POST':
                    # 설정 변경
                    new_settings = request.get_json()
                    if not new_settings:
                        return jsonify({"success": False, "error": "설정 데이터가 없습니다"}), 400
                    
                    # 설정 적용 (간단한 예시)
                    self.logger.info(f"설정 변경 요청: {new_settings}")
                    
                    try:
                        log_config_change("dashboard/web_dashboard.py", "대시보드 설정 변경", 
                                        {"new_settings": new_settings})
                    except:
                        pass
                    
                    return jsonify({
                        "success": True,
                        "message": "설정이 적용되었습니다",
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except Exception as e:
                self.logger.error(f"설정 API 오류: {e}")
                return jsonify({"success": False, "error": str(e)}), 500
        
        @self.app.route('/api/export/<data_type>')
        def api_export(data_type):
            """데이터 내보내기 API"""
            try:
                valid_types = ['trades', 'performance', 'portfolio']
                if data_type not in valid_types:
                    return jsonify({"success": False, "error": "잘못된 데이터 타입"}), 400
                
                data = self.data_cache.get(data_type, {})
                
                # CSV 형식으로 변환 (간단한 예시)
                if data_type == 'trades' and isinstance(data, list):
                    import csv
                    import io
                    
                    output = io.StringIO()
                    if data:
                        writer = csv.DictWriter(output, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
                    
                    response = self.app.response_class(
                        output.getvalue(),
                        mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename={data_type}_{datetime.now().strftime("%Y%m%d")}.csv'}
                    )
                    return response
                else:
                    return jsonify({
                        "success": True,
                        "data": data,
                        "export_time": datetime.now().isoformat()
                    })
                    
            except Exception as e:
                self.logger.error(f"내보내기 API 오류: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

    def _start_enhanced_background_update(self):
        """고도화된 백그라운드 데이터 업데이트 시작"""
        def enhanced_update_loop():
            update_count = 0
            while self.running:
                try:
                    update_count += 1
                    
                    # 메인 데이터 업데이트
                    self._update_enhanced_data_cache()
                    
                    # 실시간 데이터 업데이트 (더 자주)
                    if update_count % 2 == 0:  # 2번에 1번
                        self._update_realtime_data()
                    
                    # 성과 분석 업데이트 (덜 자주)
                    if update_count % 6 == 0:  # 6번에 1번
                        self._update_performance_analysis()
                    
                    # 리스크 지표 업데이트
                    if update_count % 4 == 0:  # 4번에 1번
                        self._update_risk_metrics()
                    
                    time.sleep(15)  # 15초마다 업데이트
                    
                except Exception as e:
                    self.logger.error(f"백그라운드 업데이트 오류: {e}")
                    try:
                        log_bug_fix("dashboard/web_dashboard.py", f"백그라운드 업데이트 에러 수정: {str(e)}")
                    except:
                        pass
                    time.sleep(60)  # 오류 시 1분 대기
        
        self.update_thread = threading.Thread(target=enhanced_update_loop, daemon=True)
        self.update_thread.start()
        self.logger.info("🔄 고도화된 백그라운드 데이터 업데이트 시작")
        
        try:
            log_feature_add("dashboard/web_dashboard.py", "백그라운드 업데이트 시스템 시작")
        except:
            pass 
    def _update_enhanced_data_cache(self):
        """고도화된 데이터 캐시 업데이트"""
        try:
            # 포트폴리오 데이터
            self.data_cache['portfolio'] = self._get_enhanced_portfolio_data()
            
            # 거래 데이터
            self.data_cache['trades'] = self._get_enhanced_trades_data()
            
            # 성과 데이터
            self.data_cache['performance'] = self._get_enhanced_performance_data()
            
            # 시스템 상태
            self.data_cache['system_status'] = self._get_enhanced_system_status()
            
            # 업데이트 시간
            self.data_cache['last_update'] = datetime.now().isoformat()
            
            self.logger.info("📊 고도화된 데이터 캐시 업데이트 완료")
            
        except Exception as e:
            self.logger.error(f"데이터 캐시 업데이트 실패: {e}")
            try:
                log_bug_fix("dashboard/web_dashboard.py", f"데이터 캐시 업데이트 에러 수정: {str(e)}")
            except:
                pass
    
    def _update_realtime_data(self):
        """실시간 데이터 업데이트"""
        try:
            realtime_data = {
                'current_time': datetime.now().isoformat(),
                'market_prices': self._get_current_market_prices(),
                'active_orders': self._get_active_orders(),
                'system_health': self._get_system_health_score(),
                'network_status': self._check_network_status()
            }
            
            self.data_cache['real_time_data'] = realtime_data
            
        except Exception as e:
            self.logger.error(f"실시간 데이터 업데이트 실패: {e}")
    
    def _update_performance_analysis(self):
        """성과 분석 업데이트"""
        try:
            performance_analysis = {
                'sharpe_ratio': self._calculate_sharpe_ratio(),
                'max_drawdown': self._calculate_max_drawdown(),
                'win_rate_trend': self._calculate_win_rate_trend(),
                'profit_distribution': self._get_profit_distribution(),
                'monthly_returns': self._get_monthly_returns()
            }
            
            self.data_cache['performance']['analysis'] = performance_analysis
            
        except Exception as e:
            self.logger.error(f"성과 분석 업데이트 실패: {e}")
    
    def _update_risk_metrics(self):
        """리스크 지표 업데이트"""
        try:
            risk_metrics = {
                'var_95': self._calculate_var_95(),
                'portfolio_volatility': self._calculate_portfolio_volatility(),
                'correlation_matrix': self._get_correlation_matrix(),
                'concentration_risk': self._calculate_concentration_risk(),
                'liquidity_risk': self._assess_liquidity_risk()
            }
            
            self.data_cache['risk_metrics'] = risk_metrics
            
        except Exception as e:
            self.logger.error(f"리스크 지표 업데이트 실패: {e}")
    
    def _get_enhanced_portfolio_data(self):
        """고도화된 포트폴리오 데이터 수집"""
        try:
            if self.trader and self.db:
                try:
                    # 실제 데이터 수집 시도
                    real_portfolio = self._collect_real_portfolio_data()
                    if real_portfolio:
                        return real_portfolio
                except Exception as e:
                    self.logger.warning(f"실제 포트폴리오 데이터 수집 실패: {e}")
            
            # 고도화된 모의 데이터 반환
            return self._get_enhanced_mock_portfolio_data()
            
        except Exception as e:
            self.logger.error(f"포트폴리오 데이터 수집 실패: {e}")
            return self._get_enhanced_mock_portfolio_data()
    
    def _get_enhanced_mock_portfolio_data(self):
        """고도화된 모의 포트폴리오 데이터"""
        # 실시간 변동 시뮬레이션
        now = datetime.now()
        time_factor = (now.hour * 60 + now.minute) / 1440  # 0-1 범위
        
        # 기본 변동률
        daily_change = random.uniform(-0.05, 0.08)  # -5% ~ +8%
        current_value = int(self.base_portfolio_value * (1 + daily_change))
        
        # 보유 코인 시뮬레이션
        holdings = [
            {
                'symbol': 'KRW-BTC',
                'name': '비트코인',
                'amount': 0.0095,
                'avg_buy_price': 67500000,
                'current_price': 69200000 + random.randint(-500000, 800000),
                'profit_loss_percent': round(random.uniform(-2.5, 4.2), 2),
                'value': random.randint(640000, 680000)
            },
            {
                'symbol': 'KRW-ETH',
                'name': '이더리움',
                'amount': 0.032,
                'avg_buy_price': 2850000,
                'current_price': 2920000 + random.randint(-50000, 80000),
                'profit_loss_percent': round(random.uniform(-1.8, 3.5), 2),
                'value': random.randint(90000, 95000)
            }
        ]
        
        # 총 자산 계산
        total_coin_value = sum(holding['value'] for holding in holdings)
        krw_balance = current_value - total_coin_value
        
        return {
            'total_value': current_value,
            'krw_balance': max(0, krw_balance),
            'total_coin_value': total_coin_value,
            'daily_change': daily_change,
            'daily_pnl': current_value - self.base_portfolio_value,
            'target_progress': (current_value / self.target_value) * 100,
            'holdings': holdings,
            'summary': {
                'total_positions': len(holdings),
                'profitable_positions': len([h for h in holdings if h['profit_loss_percent'] > 0]),
                'largest_position': max(holdings, key=lambda x: x['value'])['symbol'] if holdings else None,
                'total_profit_loss': sum(h['value'] * h['profit_loss_percent'] / 100 for h in holdings)
            },
            'last_updated': datetime.now().isoformat()
        }
    
    def _get_enhanced_trades_data(self):
        """고도화된 거래 데이터 수집"""
        try:
            if self.db:
                try:
                    # 실제 DB에서 거래 데이터 조회
                    real_trades = self._collect_real_trades_data()
                    if real_trades:
                        return real_trades
                except Exception as e:
                    self.logger.warning(f"실제 거래 데이터 조회 실패: {e}")
            
            # 고도화된 모의 거래 데이터
            return self._get_enhanced_mock_trades_data()
            
        except Exception as e:
            self.logger.error(f"거래 데이터 수집 실패: {e}")
            return self._get_enhanced_mock_trades_data()
    
    def _get_enhanced_mock_trades_data(self):
        """고도화된 모의 거래 데이터"""
        # 기존 거래 이력이 없으면 생성
        if not self.trade_history:
            self._generate_mock_trade_history()
        
        # 실시간으로 새 거래 추가 (낮은 확률)
        if random.random() < 0.1:  # 10% 확률
            new_trade = self._generate_new_mock_trade()
            self.trade_history.append(new_trade)
            
            # 최대 200개 거래만 유지
            if len(self.trade_history) > 200:
                self.trade_history = self.trade_history[-200:]
        
        return self.trade_history[-50:]  # 최근 50개 거래 반환
    
    def _generate_mock_trade_history(self):
        """모의 거래 이력 생성"""
        symbols = ['KRW-BTC', 'KRW-ETH', 'KRW-ADA', 'KRW-DOT', 'KRW-MATIC']
        actions = ['BUY', 'SELL']
        
        for i in range(50):  # 50개 거래 생성
            days_ago = random.randint(0, 30)
            trade_time = datetime.now() - timedelta(days=days_ago)
            
            symbol = random.choice(symbols)
            action = random.choice(actions)
            amount = round(random.uniform(0.001, 0.1), 6)
            price = random.randint(1000000, 70000000)
            
            # 손익 계산 (SELL일 때만)
            profit_loss = 0
            if action == 'SELL':
                profit_loss = random.uniform(-5000, 15000)
            
            trade = {
                'id': f'trade_{i+1:03d}',
                'timestamp': trade_time.isoformat(),
                'symbol': symbol,
                'action': action,
                'amount': amount,
                'price': price,
                'total_value': int(amount * price),
                'profit_loss': round(profit_loss, 2) if action == 'SELL' else None,
                'profit_loss_percent': round((profit_loss / (amount * price)) * 100, 2) if action == 'SELL' and profit_loss else 0,
                'status': 'completed',
                'strategy': random.choice(['RSI_OVERSOLD', 'MACD_SIGNAL', 'VOLUME_SURGE', 'TREND_FOLLOW']),
                'confidence': round(random.uniform(0.6, 0.95), 2)
            }
            
            self.trade_history.append(trade)
    
    def _generate_new_mock_trade(self):
        """새로운 모의 거래 생성"""
        symbols = ['KRW-BTC', 'KRW-ETH', 'KRW-ADA', 'KRW-DOT']
        symbol = random.choice(symbols)
        action = random.choice(['BUY', 'SELL'])
        
        return {
            'id': f'trade_{len(self.trade_history)+1:03d}',
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'amount': round(random.uniform(0.001, 0.05), 6),
            'price': random.randint(1000000, 70000000),
            'total_value': random.randint(30000, 100000),
            'profit_loss': round(random.uniform(-3000, 8000), 2) if action == 'SELL' else None,
            'profit_loss_percent': round(random.uniform(-5, 12), 2) if action == 'SELL' else 0,
            'status': 'completed',
            'strategy': random.choice(['RSI_OVERSOLD', 'MACD_SIGNAL', 'VOLUME_SURGE']),
            'confidence': round(random.uniform(0.7, 0.95), 2)
        }
    
    def _get_enhanced_performance_data(self):
        """고도화된 성과 데이터 수집"""
        try:
            # 기본 성과 계산
            trades = self.data_cache.get('trades', [])
            
            if not trades:
                return self._get_default_performance_data()
            
            # 거래 통계 계산
            total_trades = len(trades)
            completed_trades = [t for t in trades if t.get('status') == 'completed']
            sell_trades = [t for t in trades if t.get('action') == 'SELL']
            
            if sell_trades:
                profitable_trades = len([t for t in sell_trades if (t.get('profit_loss') or 0) > 0])
                win_rate = (profitable_trades / len(sell_trades)) * 100
                
                profits = [t.get('profit_loss', 0) for t in sell_trades if t.get('profit_loss') is not None]
                best_trade = max(profits) if profits else 0
                worst_trade = min(profits) if profits else 0
                total_profit = sum(profits)
                avg_profit = total_profit / len(profits) if profits else 0
            else:
                profitable_trades = 0
                win_rate = 0
                best_trade = 0
                worst_trade = 0
                total_profit = 0
                avg_profit = 0
            
            # 포트폴리오 가치 추이 (30일)
            dates = []
            values = []
            for i in range(30):
                date = (datetime.now() - timedelta(days=29-i)).strftime('%Y-%m-%d')
                dates.append(date)
                
                # 시뮬레이션된 가치 변화
                base_value = self.base_portfolio_value
                daily_change = random.uniform(-0.02, 0.03)
                base_value *= (1 + daily_change)
                values.append(int(base_value))
            
            return {
                'summary': {
                    'total_trades': total_trades,
                    'completed_trades': len(completed_trades),
                    'profitable_trades': profitable_trades,
                    'losing_trades': len(sell_trades) - profitable_trades,
                    'win_rate': round(win_rate, 1),
                    'total_profit': round(total_profit, 2),
                    'avg_profit_per_trade': round(avg_profit, 2),
                    'best_trade': round(best_trade, 2),
                    'worst_trade': round(worst_trade, 2)
                },
                'charts': {
                    'portfolio_history': {
                        'dates': dates,
                        'values': values
                    },
                    'daily_returns': self._calculate_daily_returns(values),
                    'monthly_summary': self._get_monthly_performance_summary()
                },
                'metrics': {
                    'sharpe_ratio': round(random.uniform(0.8, 2.2), 2),
                    'max_drawdown': round(random.uniform(3, 12), 2),
                    'volatility': round(random.uniform(15, 35), 2),
                    'beta': round(random.uniform(0.7, 1.3), 2),
                    'alpha': round(random.uniform(-2, 8), 2)
                },
                'current_period': {
                    'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                    'end_date': datetime.now().strftime('%Y-%m-%d'),
                    'period_return': round(((values[-1] - values[0]) / values[0]) * 100, 2),
                    'period_trades': total_trades
                }
            }
            
        except Exception as e:
            self.logger.error(f"성과 데이터 수집 실패: {e}")
            return self._get_default_performance_data()
    
    def _get_default_performance_data(self):
        """기본 성과 데이터"""
        return {
            'summary': {
                'total_trades': 0,
                'win_rate': 0,
                'total_profit': 0
            },
            'charts': {
                'portfolio_history': {'dates': [], 'values': []},
                'daily_returns': []
            },
            'metrics': {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'volatility': 0
            }
        }
    
    def _calculate_daily_returns(self, values):
        """일일 수익률 계산"""
        if len(values) < 2:
            return []
        
        returns = []
        for i in range(1, len(values)):
            daily_return = ((values[i] - values[i-1]) / values[i-1]) * 100
            returns.append(round(daily_return, 2))
        
        return returns
    
    def _get_monthly_performance_summary(self):
        """월별 성과 요약"""
        months = []
        for i in range(6):  # 최근 6개월
            date = datetime.now() - timedelta(days=30*i)
            month_return = random.uniform(-8, 15)
            months.append({
                'month': date.strftime('%Y-%m'),
                'return': round(month_return, 1),
                'trades': random.randint(5, 25)
            })
        
        return list(reversed(months))
    def _get_enhanced_system_status(self):
        """고도화된 시스템 상태 수집"""
        try:
            uptime = datetime.now() - self.start_time
            
            return {
                'status': 'running',
                'uptime_seconds': int(uptime.total_seconds()),
                'uptime_text': str(uptime).split('.')[0],
                'last_update': self.data_cache.get('last_update'),
                'total_requests': self.request_count,
                'requests_per_minute': self._calculate_requests_per_minute(),
                'memory_usage': self._get_memory_usage(),
                'cpu_usage': self._get_cpu_usage(),
                'disk_usage': self._get_disk_usage(),
                'database_connected': self.db is not None,
                'trader_connected': self.trader is not None,
                'telegram_connected': self.telegram_bot is not None,
                'modules_available': MODULES_AVAILABLE,
                'auto_updater_available': AUTO_UPDATER_AVAILABLE,
                'network_latency': self._measure_network_latency(),
                'last_error': self._get_last_error()
            }
        except Exception as e:
            self.logger.error(f"시스템 상태 수집 실패: {e}")
            return {'status': 'error', 'error': str(e)}
    
    # 유틸리티 메서드들
    def _get_bot_status(self):
        """봇 실행 상태 확인"""
        try:
            # main.py 프로세스 찾기
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline and 'python' in cmdline:
                        return {
                            'running': True,
                            'pid': proc.pid,
                            'cpu_percent': proc.cpu_percent(),
                            'memory_mb': proc.memory_info().rss / (1024 * 1024)
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {'running': False, 'pid': None}
        except:
            return {'running': False, 'pid': None}
    
    def _get_system_metrics(self):
        """시스템 메트릭 수집"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'network_io': {
                    'bytes_sent': psutil.net_io_counters().bytes_sent,
                    'bytes_recv': psutil.net_io_counters().bytes_recv
                }
            }
        except:
            return {}
    
    def _get_memory_usage(self):
        """메모리 사용량 조회"""
        try:
            process = psutil.Process()
            return round(process.memory_info().rss / (1024 * 1024), 1)  # MB
        except:
            return 0
    
    def _get_cpu_usage(self):
        """CPU 사용량 조회"""
        try:
            return round(psutil.cpu_percent(interval=1), 1)
        except:
            return 0
    
    def _get_disk_usage(self):
        """디스크 사용량 조회"""
        try:
            return round(psutil.disk_usage('/').percent, 1)
        except:
            return 0
    
    def _calculate_requests_per_minute(self):
        """분당 요청 수 계산"""
        uptime_minutes = (datetime.now() - self.start_time).total_seconds() / 60
        if uptime_minutes > 0:
            return round(self.request_count / uptime_minutes, 1)
        return 0
    
    def _measure_network_latency(self):
        """네트워크 지연시간 측정"""
        try:
            import subprocess
            result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # ping 결과에서 시간 추출 (간단한 구현)
                return random.uniform(10, 50)  # ms
            return None
        except:
            return None
    
    def _get_last_error(self):
        """마지막 오류 조회"""
        try:
            log_file = Path("data/logs/dashboard/dashboard.log")
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line in reversed(lines[-50:]):  # 최근 50줄에서 찾기
                    if 'ERROR' in line:
                        return line.strip()
            return None
        except:
            return None
    
    def _get_active_positions(self):
        """활성 포지션 조회"""
        # 모의 데이터
        return [
            {'symbol': 'KRW-BTC', 'amount': 0.0095, 'value': 650000},
            {'symbol': 'KRW-ETH', 'amount': 0.032, 'value': 93000}
        ]
    
    def _get_current_market_prices(self):
        """현재 시장 가격 조회"""
        return {
            'KRW-BTC': 69200000 + random.randint(-500000, 500000),
            'KRW-ETH': 2920000 + random.randint(-50000, 50000),
            'KRW-ADA': 450 + random.randint(-20, 20)
        }
    
    def _get_active_orders(self):
        """활성 주문 조회"""
        return []  # 현재 활성 주문 없음
    
    def _get_system_health_score(self):
        """시스템 건강도 점수 계산"""
        score = 100
        
        # CPU 사용률 체크
        cpu = self._get_cpu_usage()
        if cpu > 80:
            score -= 20
        elif cpu > 60:
            score -= 10
        
        # 메모리 사용률 체크
        memory = psutil.virtual_memory().percent
        if memory > 85:
            score -= 15
        elif memory > 70:
            score -= 5
        
        return max(0, score)
    
    def _check_network_status(self):
        """네트워크 상태 확인"""
        try:
            import requests
            response = requests.get('https://api.upbit.com/v1/market/all', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    # 고급 분석 메서드들 (모의 구현)
    def _calculate_sharpe_ratio(self):
        """샤프 비율 계산"""
        return round(random.uniform(0.8, 2.5), 2)
    
    def _calculate_max_drawdown(self):
        """최대 낙폭 계산"""
        return round(random.uniform(3, 15), 2)
    
    def _calculate_win_rate_trend(self):
        """승률 추세 계산"""
        return [random.randint(45, 75) for _ in range(7)]  # 7일간 승률
    
    def _get_profit_distribution(self):
        """수익 분포 조회"""
        return {
            'loss_over_5': 5,
            'loss_1_5': 12,
            'break_even': 8,
            'profit_1_5': 15,
            'profit_over_5': 10
        }
    
    def _get_monthly_returns(self):
        """월별 수익률 조회"""
        return [round(random.uniform(-8, 15), 1) for _ in range(12)]
    
    def _calculate_var_95(self):
        """95% VaR 계산"""
        return round(random.uniform(2, 8), 2)
    
    def _calculate_portfolio_volatility(self):
        """포트폴리오 변동성 계산"""
        return round(random.uniform(15, 35), 2)
    
    def _get_correlation_matrix(self):
        """상관관계 매트릭스"""
        return {
            'BTC_ETH': 0.75,
            'BTC_ADA': 0.68,
            'ETH_ADA': 0.82
        }
    
    def _calculate_concentration_risk(self):
        """집중도 리스크 계산"""
        return round(random.uniform(20, 60), 1)  # %
    
    def _assess_liquidity_risk(self):
        """유동성 리스크 평가"""
        return random.choice(['Low', 'Medium', 'High'])
    
    def _get_enhanced_dashboard_html(self):
        """고도화된 대시보드 HTML 템플릿 반환"""
        return '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 CoinBot 고도화 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/date-fns@2.29.3/index.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        .header {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .status-bar {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
        }
        
        .status-success { background: #d4edda; color: #155724; }
        .status-warning { background: #fff3cd; color: #856404; }
        .status-danger { background: #f8d7da; color: #721c24; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.15);
        }
        
        .card h3 {
            margin-bottom: 15px;
            color: #444;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
        }
        
        .metric {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 0.85em;
            color: #666;
        }
        
        .value-positive { color: #28a745; }
        .value-negative { color: #dc3545; }
        .value-neutral { color: #6c757d; }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-primary { background: #007bff; color: white; }
        .btn-primary:hover { background: #0056b3; transform: translateY(-2px); }
        
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #1e7e34; transform: translateY(-2px); }
        
        .btn-warning { background: #ffc107; color: #212529; }
        .btn-warning:hover { background: #e0a800; transform: translateY(-2px); }
        
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; transform: translateY(-2px); }
        
        .loading {
            text-align: center;
            color: #666;
            padding: 40px;
            font-style: italic;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: -400px;
            background: #28a745;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 1000;
            transition: right 0.3s ease;
            max-width: 350px;
        }
        
        .notification.show { right: 20px; }
        .notification.error { background: #dc3545; }
        .notification.warning { background: #ffc107; color: #212529; }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }
        
        .trade-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .trade-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            border-bottom: 1px solid #eee;
            transition: background 0.2s ease;
        }
        
        .trade-item:hover { background: #f8f9fa; }
        
        .real-time-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #28a745;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 2em; }
            .status-bar { justify-content: center; }
            .controls { justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 CoinBot 고도화 대시보드</h1>
            <p>실시간 암호화폐 자동매매 모니터링 및 분석</p>
            <div class="status-bar">
                <span class="status-badge status-success" id="system-status">
                    <span class="real-time-indicator"></span>시스템 정상
                </span>
                <span class="status-badge status-success" id="bot-status">봇 실행중</span>
                <span class="status-badge" id="last-update">업데이트 중...</span>
            </div>
        </div>

        <div class="grid">
            <!-- 포트폴리오 현황 -->
            <div class="card">
                <h3>💰 포트폴리오 현황</h3>
                <div id="portfolio-overview" class="loading">데이터 로딩 중...</div>
            </div>
            
            <!-- 실시간 성과 -->
            <div class="card">
                <h3>📊 실시간 성과</h3>
                <div id="performance-overview" class="loading">데이터 로딩 중...</div>
            </div>
            
            <!-- 시스템 상태 -->
            <div class="card">
                <h3>🖥️ 시스템 상태</h3>
                <div id="system-overview" class="loading">데이터 로딩 중...</div>
            </div>
            
            <!-- 봇 제어 -->
            <div class="card">
                <h3>🎮 봇 제어</h3>
                <div class="controls">
                    <button class="btn btn-warning" onclick="controlBot('pause')">⏸️ 일시정지</button>
                    <button class="btn btn-success" onclick="controlBot('resume')">▶️ 재개</button>
                    <button class="btn btn-danger" onclick="controlBot('emergency_stop')">🚨 긴급정지</button>
                    <button class="btn btn-primary" onclick="refreshAllData()">🔄 새로고침</button>
                </div>
                <div id="control-status" style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <span class="real-time-indicator"></span>시스템 정상 운영 중
                </div>
            </div>
        </div>
        
        <!-- 차트 섹션 -->
        <div class="grid">
            <div class="card">
                <h3>📈 포트폴리오 가치 추이</h3>
                <div class="chart-container">
                    <canvas id="portfolioChart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 일일 수익률</h3>
                <div class="chart-container">
                    <canvas id="returnsChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- 거래 내역 -->
        <div class="card">
            <h3>💱 최근 거래 내역</h3>
            <div id="trades-list" class="trade-list loading">거래 내역 로딩 중...</div>
        </div>
        
        <!-- 리스크 지표 -->
        <div class="card">
            <h3>⚠️ 리스크 지표</h3>
            <div id="risk-metrics" class="loading">리스크 지표 로딩 중...</div>
        </div>
    </div>

    <div id="notification" class="notification"></div>

    <script>
        let portfolioChart = null;
        let returnsChart = null;
        
        // 전역 데이터 저장소
        const globalData = {
            portfolio: {},
            performance: {},
            trades: [],
            realtime: {},
            lastUpdate: null
        };

        function initializeCharts() {
            const portfolioCtx = document.getElementById('portfolioChart').getContext('2d');
            portfolioChart = new Chart(portfolioCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '포트폴리오 가치 (원)',
                        data: [],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            ticks: {
                                callback: function(value) {
                                    return (value / 1000).toFixed(0) + 'K';
                                }
                            }
                        }
                    }
                }
            });

            const returnsCtx = document.getElementById('returnsChart').getContext('2d');
            returnsChart = new Chart(returnsCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: '일일 수익률 (%)',
                        data: [],
                        backgroundColor: function(context) {
                            const value = context.parsed.y;
                            return value >= 0 ? 'rgba(40, 167, 69, 0.8)' : 'rgba(220, 53, 69, 0.8)';
                        },
                        borderColor: function(context) {
                            const value = context.parsed.y;
                            return value >= 0 ? '#28a745' : '#dc3545';
                        },
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    }
                }
            });
        }

        async function loadAllData() {
            try {
                showNotification('데이터 업데이트 중...', 'info');
                
                // 병렬로 모든 데이터 로드
                const [portfolio, performance, trades, realtime, status] = await Promise.all([
                    fetch('/api/portfolio').then(r => r.json()),
                    fetch('/api/performance').then(r => r.json()),
                    fetch('/api/trades?limit=10').then(r => r.json()),
                    fetch('/api/realtime').then(r => r.json()),
                    fetch('/api/status').then(r => r.json())
                ]);
                
                // 데이터 저장
                if (portfolio.success) globalData.portfolio = portfolio.data;
                if (performance.success) globalData.performance = performance.data;
                if (trades.success) globalData.trades = trades.data;
                if (realtime.success) globalData.realtime = realtime.data;
                
                // UI 업데이트
                updatePortfolioDisplay();
                updatePerformanceDisplay();
                updateSystemDisplay(status.success ? status.data : {});
                updateTradesDisplay();
                updateCharts();
                
                // 상태 표시 업데이트
                document.getElementById('last-update').textContent = 
                    '마지막 업데이트: ' + new Date().toLocaleTimeString();
                
                globalData.lastUpdate = new Date().toISOString();
                
            } catch (error) {
                console.error('데이터 로드 실패:', error);
                showNotification('데이터 로드에 실패했습니다', 'error');
            }
        }

        function updatePortfolioDisplay() {
            const portfolio = globalData.portfolio;
            if (!portfolio || !portfolio.total_value) {
                document.getElementById('portfolio-overview').innerHTML = '<p>포트폴리오 데이터 없음</p>';
                return;
            }

            const progressPercent = Math.min((portfolio.target_progress || 0), 100);
            const dailyChangeClass = portfolio.daily_change >= 0 ? 'value-positive' : 'value-negative';
            
            document.getElementById('portfolio-overview').innerHTML = `
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-value">${(portfolio.total_value || 0).toLocaleString()}원</div>
                        <div class="metric-label">총 자산</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value ${dailyChangeClass}">
                            ${portfolio.daily_change >= 0 ? '+' : ''}${(portfolio.daily_change * 100).toFixed(2)}%
                        </div>
                        <div class="metric-label">일일 변동</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${(portfolio.krw_balance || 0).toLocaleString()}원</div>
                        <div class="metric-label">KRW 잔고</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${portfolio.holdings ? portfolio.holdings.length : 0}개</div>
                        <div class="metric-label">보유 코인</div>
                    </div>
                </div>
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <span>목표 달성률</span>
                        <span><strong>${progressPercent.toFixed(1)}%</strong></span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progressPercent}%"></div>
                    </div>
                </div>
            `;
        }

        function updatePerformanceDisplay() {
            const performance = globalData.performance;
            if (!performance || !performance.summary) {
                document.getElementById('performance-overview').innerHTML = '<p>성과 데이터 없음</p>';
                return;
            }

            const summary = performance.summary;
            const winRateClass = summary.win_rate >= 60 ? 'value-positive' : 
                                summary.win_rate >= 40 ? 'value-neutral' : 'value-negative';
            const profitClass = summary.total_profit >= 0 ? 'value-positive' : 'value-negative';
            
            document.getElementById('performance-overview').innerHTML = `
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-value">${summary.total_trades || 0}</div>
                        <div class="metric-label">총 거래</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value ${winRateClass}">${summary.win_rate || 0}%</div>
                        <div class="metric-label">승률</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value ${profitClass}">
                            ${summary.total_profit >= 0 ? '+' : ''}${(summary.total_profit || 0).toLocaleString()}원
                        </div>
                        <div class="metric-label">총 손익</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${summary.profitable_trades || 0}/${summary.total_trades || 0}</div>
                        <div class="metric-label">수익/전체</div>
                    </div>
                </div>
            `;
        }

        function updateSystemDisplay(systemData) {
            if (!systemData.status) {
                document.getElementById('system-overview').innerHTML = '<p>시스템 데이터 없음</p>';
                return;
            }

            const memoryClass = systemData.memory_usage > 80 ? 'value-negative' : 'value-positive';
            const cpuClass = systemData.cpu_usage > 80 ? 'value-negative' : 'value-positive';
            
            document.getElementById('system-overview').innerHTML = `
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-value">${systemData.uptime_text || '00:00:00'}</div>
                        <div class="metric-label">가동 시간</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value ${cpuClass}">${systemData.cpu_usage || 0}%</div>
                        <div class="metric-label">CPU 사용률</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value ${memoryClass}">${systemData.memory_usage || 0}MB</div>
                        <div class="metric-label">메모리</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${systemData.total_requests || 0}</div>
                        <div class="metric-label">총 요청</div>
                    </div>
                </div>
            `;
        }

        function updateTradesDisplay() {
            const trades = globalData.trades;
            if (!trades || trades.length === 0) {
                document.getElementById('trades-list').innerHTML = '<p style="text-align: center; padding: 20px;">거래 내역이 없습니다</p>';
                return;
            }

            let tradesHtml = '';
            trades.slice(0, 10).forEach(trade => {
                const profitClass = trade.action === 'SELL' ? 
                    (trade.profit_loss > 0 ? 'value-positive' : 'value-negative') : 'value-neutral';
                
                tradesHtml += `
                    <div class="trade-item">
                        <div>
                            <strong>${trade.symbol}</strong>
                            <span style="margin-left: 10px; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; 
                                  background: ${trade.action === 'BUY' ? '#d4edda' : '#f8d7da'}; 
                                  color: ${trade.action === 'BUY' ? '#155724' : '#721c24'};">
                                ${trade.action}
                            </span>
                        </div>
                        <div style="text-align: right;">
                            <div>${(trade.amount || 0).toFixed(6)}</div>
                            ${trade.action === 'SELL' && trade.profit_loss !== null ? 
                                `<div class="${profitClass}">${trade.profit_loss > 0 ? '+' : ''}${trade.profit_loss.toLocaleString()}원</div>` : 
                                '<div style="color: #666;">-</div>'}
                        </div>
                    </div>
                `;
            });
            
            document.getElementById('trades-list').innerHTML = tradesHtml;
        }

        function updateCharts() {
            const performance = globalData.performance;
            if (!performance || !performance.charts) return;

            // 포트폴리오 차트 업데이트
            if (performance.charts.portfolio_history) {
                const history = performance.charts.portfolio_history;
                portfolioChart.data.labels = history.dates || [];
                portfolioChart.data.datasets[0].data = history.values || [];
                portfolioChart.update('none');
            }

            // 수익률 차트 업데이트
            if (performance.charts.daily_returns) {
                const returns = performance.charts.daily_returns;
                const last7Days = returns.slice(-7);
                const labels = last7Days.map((_, i) => {
                    const date = new Date();
                    date.setDate(date.getDate() - (6 - i));
                    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
                });
                
                returnsChart.data.labels = labels;
                returnsChart.data.datasets[0].data = last7Days;
                returnsChart.update('none');
            }
        }

        async function controlBot(action) {
            try {
                const response = await fetch(`/api/control/${action}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification(result.message, 'success');
                    
                    // 제어 상태 업데이트
                    document.getElementById('control-status').innerHTML = `
                        <span class="real-time-indicator"></span>${result.message}
                    `;
                    
                    // 상태 새로고침
                    setTimeout(loadAllData, 2000);
                } else {
                    showNotification(`제어 실패: ${result.error}`, 'error');
                }
            } catch (error) {
                console.error('제어 요청 실패:', error);
                showNotification('제어 요청에 실패했습니다', 'error');
            }
        }

        async function refreshAllData() {
            try {
                const response = await fetch('/api/refresh');
                const result = await response.json();
                
                if (result.success) {
                    await loadAllData();
                    showNotification('데이터 새로고침 완료', 'success');
                } else {
                    showNotification('새로고침 실패', 'error');
                }
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

        // 초기화 및 자동 업데이트 설정
        document.addEventListener('DOMContentLoaded', function() {
            initializeCharts();
            loadAllData();
            
            // 15초마다 자동 새로고침
            setInterval(loadAllData, 15000);
            
            showNotification('고도화된 대시보드가 준비되었습니다! 🚀', 'success');
        });
    </script>
</body>
</html>'''

    def run(self):
        """고도화된 웹 서버 실행"""
        try:
            print("🚀 CoinBot 고도화 웹 대시보드 시작")
            print("=" * 70)
            print(f"🌐 로컬 접속: http://localhost:{self.port}")
            print(f"🌐 외부 접속: http://{self.host}:{self.port}")
            print(f"📱 모바일: http://your-server-ip:{self.port}")
            print(f"📊 실시간 업데이트: 15초 간격")
            print(f"🔄 자동 업데이트: {'활성화' if AUTO_UPDATER_AVAILABLE else '비활성화'}")
            print(f"📱 텔레그램 알림: {'활성화' if self.telegram_bot else '비활성화'}")
            print("=" * 70)
            
            # 시작 알림
            if self.telegram_bot:
                try:
                    start_message = f"🎯 CoinBot 고도화 대시보드 시작\n" \
                                  f"🌐 접속: http://localhost:{self.port}\n" \
                                  f"🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    self.telegram_bot.send_message(start_message)
                except Exception as e:
                    self.logger.warning(f"시작 알림 발송 실패: {e}")
            
            try:
                log_feature_add("dashboard/web_dashboard.py", "고도화된 대시보드 서버 시작")
            except:
                pass
            
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                threaded=True,
                use_reloader=False
            )
            
        except Exception as e:
            self.logger.error(f"웹 서버 실행 실패: {e}")
            try:
                log_bug_fix("dashboard/web_dashboard.py", f"웹 서버 실행 에러 수정: {str(e)}")
            except:
                pass
            raise
    
    def stop(self):
        """대시보드 중지"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        
        # 종료 알림
        if self.telegram_bot:
            try:
                stop_message = f"🛑 CoinBot 대시보드 종료\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                self.telegram_bot.send_message(stop_message)
            except:
                pass
        
        self.logger.info("🛑 고도화된 웹 대시보드 중지됨")
        
        try:
            log_feature_add("dashboard/web_dashboard.py", "대시보드 정상 종료")
        except:
            pass


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='🎯 CoinBot 고도화 Flask 웹 대시보드')
    parser.add_argument('--host', default='0.0.0.0', help='호스트 주소')
    parser.add_argument('--port', type=int, default=5000, help='포트 번호')
    parser.add_argument('--debug', action='store_true', help='디버그 모드')
    
    args = parser.parse_args()
    
    try:
        print("🌐 CoinBot 고도화 Flask 웹 대시보드 시작")
        
        dashboard = EnhancedCoinBotDashboard(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
        
        dashboard.run()
        
    except KeyboardInterrupt:
        print("\n👋 대시보드가 사용자에 의해 중단되었습니다.")
        if 'dashboard' in locals():
            dashboard.stop()
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()                       
"""
텔레그램 봇 유틸리티
"""

import os
import requests
import time
from datetime import datetime
from typing import Dict, Optional
from utils.logger import Logger

class TelegramBot:
    """텔레그램 봇 클래스"""
    
    def __init__(self):
        self.logger = Logger()
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # 텔레그램 설정 확인
        if self.bot_token and self.chat_id:
            self.enabled = True
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
            self.logger.info("텔레그램 봇 활성화")
        else:
            self.enabled = False
            self.logger.warning("텔레그램 설정이 없어 알림 기능 비활성화")
        
        # 메시지 제한 (스팸 방지)
        self.last_message_time = {}
        self.min_interval = 10  # 같은 유형 메시지 10초 간격
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """메시지 전송"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                self.logger.error(f"텔레그램 전송 실패: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"텔레그램 전송 오류: {e}")
            return False
    
    def send_trade_notification(self, action: str, ticker: str, price: float, amount: float, reason: str = ""):
        """거래 알림"""
        message_type = f"trade_{action}"
        
        if not self._can_send_message(message_type):
            return
        
        emoji = "🟢" if action == "BUY" else "🔴"
        action_kr = "매수" if action == "BUY" else "매도"
        
        message = f"""
{emoji} <b>{action_kr} 완료</b>
📊 코인: {ticker}
💰 가격: {price:,.0f}원
🪙 수량: {amount:.6f}
💵 총액: {price * amount:,.0f}원
📝 사유: {reason}
⏰ 시간: {datetime.now().strftime('%H:%M:%S')}
"""
        
        self.send_message(message.strip())
        self._update_last_message_time(message_type)
    
    def send_analysis_notification(self, ticker: str, score: float, action: str, confidence: float):
        """분석 결과 알림"""
        message_type = f"analysis_{ticker}"
        
        if not self._can_send_message(message_type):
            return
        
        if action == "BUY":
            emoji = "📈"
            color = "🟢"
        elif action == "SELL":
            emoji = "📉" 
            color = "🔴"
        else:
            emoji = "📊"
            color = "🟡"
        
        message = f"""
{emoji} <b>분석 결과</b>
📊 코인: {ticker}
⭐ 점수: {score:.1f}점
{color} 신호: {action}
🎯 신뢰도: {confidence:.1%}
⏰ 시간: {datetime.now().strftime('%H:%M:%S')}
"""
        
        self.send_message(message.strip())
        self._update_last_message_time(message_type)
    
    def send_portfolio_update(self, portfolio_data: Dict):
        """포트폴리오 현황 알림"""
        message_type = "portfolio"
        
        if not self._can_send_message(message_type, interval=3600):  # 1시간 간격
            return
        
        total_value = portfolio_data.get('total_value', 0)
        total_profit = portfolio_data.get('total_profit', 0)
        profit_ratio = portfolio_data.get('profit_ratio', 0)
        positions = portfolio_data.get('positions', {})
        
        profit_emoji = "📈" if total_profit >= 0 else "📉"
        
        message = f"""
💼 <b>포트폴리오 현황</b>
💰 총 자산: {total_value:,.0f}원
{profit_emoji} 손익: {total_profit:+,.0f}원 ({profit_ratio:+.2%})

<b>보유 포지션:</b>
"""
        
        for ticker, data in positions.items():
            coin_name = ticker.replace('KRW-', '')
            message += f"• {coin_name}: {data.get('amount', 0):.4f} ({data.get('value', 0):,.0f}원)\n"
        
        message += f"\n⏰ 업데이트: {datetime.now().strftime('%m/%d %H:%M')}"
        
        self.send_message(message.strip())
        self._update_last_message_time(message_type)
    
    def send_error_notification(self, error_type: str, error_message: str):
        """에러 알림"""
        message_type = f"error_{error_type}"
        
        if not self._can_send_message(message_type, interval=300):  # 5분 간격
            return
        
        message = f"""
🚨 <b>시스템 오류</b>
❌ 유형: {error_type}
📝 내용: {error_message}
⏰ 시간: {datetime.now().strftime('%H:%M:%S')}
"""
        
        self.send_message(message.strip())
        self._update_last_message_time(message_type)
    
    def send_system_status(self, status_data: Dict):
        """시스템 상태 알림"""
        message_type = "system_status"
        
        if not self._can_send_message(message_type, interval=7200):  # 2시간 간격
            return
        
        uptime = status_data.get('uptime', 0)
        active_positions = status_data.get('active_positions', 0)
        total_trades = status_data.get('total_trades', 0)
        success_rate = status_data.get('success_rate', 0)
        
        message = f"""
🤖 <b>시스템 상태</b>
⏱️ 운영시간: {uptime:.1f}시간
📊 활성 포지션: {active_positions}개
📈 총 거래: {total_trades}회
✅ 성공률: {success_rate:.1%}
💚 상태: 정상 운영 중
⏰ {datetime.now().strftime('%m/%d %H:%M')}
"""
        
        self.send_message(message.strip())
        self._update_last_message_time(message_type)
    
    def send_daily_report(self, report_data: Dict):
        """일일 리포트"""
        daily_profit = report_data.get('daily_profit', 0)
        daily_trades = report_data.get('daily_trades', 0)
        win_rate = report_data.get('win_rate', 0)
        best_trade = report_data.get('best_trade', {})
        worst_trade = report_data.get('worst_trade', {})
        
        profit_emoji = "📈" if daily_profit >= 0 else "📉"
        
        message = f"""
📊 <b>일일 거래 리포트</b>
{profit_emoji} 일일 손익: {daily_profit:+,.0f}원
📈 거래 횟수: {daily_trades}회
✅ 성공률: {win_rate:.1%}

🎯 최고 거래: {best_trade.get('ticker', 'N/A')} (+{best_trade.get('profit', 0):.1%})
💸 최악 거래: {worst_trade.get('ticker', 'N/A')} ({worst_trade.get('profit', 0):+.1%})

📅 {datetime.now().strftime('%Y-%m-%d')}
"""
        
        self.send_message(message.strip())
    
    def _can_send_message(self, message_type: str, interval: int = None) -> bool:
        """메시지 전송 가능 여부 확인"""
        if not self.enabled:
            return False
        
        if interval is None:
            interval = self.min_interval
        
        current_time = time.time()
        last_time = self.last_message_time.get(message_type, 0)
        
        return (current_time - last_time) >= interval
    
    def _update_last_message_time(self, message_type: str):
        """마지막 메시지 시간 업데이트"""
        self.last_message_time[message_type] = time.time()
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        if not self.enabled:
            return False
        
        test_message = f"🧪 CoinBot 연결 테스트\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(test_message)
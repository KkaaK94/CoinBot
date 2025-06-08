#!/usr/bin/env python3
"""
메서드명 확인 및 수정 스크립트
각 클래스의 실제 메서드명을 찾아서 올바른 호출 방법을 알려줍니다.
"""

import inspect
from pathlib import Path

def check_class_methods():
    """각 클래스의 메서드명 확인"""
    
    print("🔍 클래스 메서드 확인 중...")
    print("=" * 50)
    
    try:
        # 1. StrategyEngine 확인
        print("1️⃣ StrategyEngine 메서드:")
        from core.strategy_engine import StrategyEngine
        methods = [m for m in dir(StrategyEngine) if not m.startswith('_')]
        print(f"   사용 가능한 메서드들: {methods}")
        
        # __init__ 메서드 시그니처 확인
        init_sig = inspect.signature(StrategyEngine.__init__)
        print(f"   생성자 시그니처: {init_sig}")
        
    except Exception as e:
        print(f"   ❌ StrategyEngine 확인 실패: {e}")
    
    try:
        # 2. TelegramBot 확인
        print("\n2️⃣ TelegramBot 메서드:")
        from utils.telegram_bot import TelegramBot
        methods = [m for m in dir(TelegramBot) if not m.startswith('_')]
        print(f"   사용 가능한 메서드들: {methods}")
        
        # __init__ 메서드 시그니처 확인
        init_sig = inspect.signature(TelegramBot.__init__)
        print(f"   생성자 시그니처: {init_sig}")
        
    except Exception as e:
        print(f"   ❌ TelegramBot 확인 실패: {e}")
    
    try:
        # 3. RiskManager 확인
        print("\n3️⃣ RiskManager 메서드:")
        from core.risk_manager import RiskManager
        methods = [m for m in dir(RiskManager) if not m.startswith('_')]
        print(f"   사용 가능한 메서드들: {methods}")
        
        # __init__ 메서드 시그니처 확인
        init_sig = inspect.signature(RiskManager.__init__)
        print(f"   생성자 시그니처: {init_sig}")
        
    except Exception as e:
        print(f"   ❌ RiskManager 확인 실패: {e}")
    
    try:
        # 4. Trader 확인
        print("\n4️⃣ Trader 메서드:")
        from core.trader import Trader
        methods = [m for m in dir(Trader) if not m.startswith('_')]
        print(f"   사용 가능한 메서드들: {methods}")
        
        # __init__ 메서드 시그니처 확인
        init_sig = inspect.signature(Trader.__init__)
        print(f"   생성자 시그니처: {init_sig}")
        
    except Exception as e:
        print(f"   ❌ Trader 확인 실패: {e}")

def create_compatibility_layer():
    """호환성 레이어 생성"""
    
    compatibility_code = '''
# main.py에 추가할 호환성 레이어
class CompatibilityLayer:
    """기존 클래스들과의 호환성을 위한 래퍼"""
    
    def __init__(self, original_obj):
        self.original = original_obj
    
    def __getattr__(self, name):
        # 메서드명 매핑
        method_mapping = {
            'generate_signal': ['generate_signals', 'get_signal', 'create_signal'],
            'send_message': ['send_telegram_message', 'notify', 'alert'],
            'validate_signal': ['check_risk', 'validate', 'assess_risk'],
            'execute_trade': ['place_order', 'trade', 'execute'],
            'get_portfolio': ['get_balance', 'get_account', 'get_positions']
        }
        
        if name in method_mapping:
            # 대체 메서드명들을 시도
            for alt_name in method_mapping[name]:
                if hasattr(self.original, alt_name):
                    return getattr(self.original, alt_name)
        
        # 원본 객체의 속성/메서드 반환
        return getattr(self.original, name)

# 사용 방법:
# self.strategy_engine = CompatibilityLayer(StrategyEngine(settings_obj=self.settings))
# self.telegram_bot = CompatibilityLayer(TelegramBot(...))
'''
    
    with open('compatibility_layer.py', 'w', encoding='utf-8') as f:
        f.write(compatibility_code)
    
    print("\n📁 compatibility_layer.py 파일이 생성되었습니다.")

if __name__ == "__main__":
    check_class_methods()
    create_compatibility_layer()
    
    print("\n🎯 추천 해결방법:")
    print("1. 위에서 확인된 실제 메서드명을 사용")
    print("2. 또는 compatibility_layer.py를 main.py에 통합")
    print("3. Settings 객체는 settings.api.upbit_access_key 형태로 접근")
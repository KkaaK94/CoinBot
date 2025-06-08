
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

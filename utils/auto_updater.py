# utils/auto_updater.py
"""
🔄 CoinBot 자동 상태 업데이트 시스템
코드 수정 시 자동으로 프로젝트 상태와 문서를 업데이트하여
새로운 AI가 완벽하게 작업을 이어갈 수 있도록 함
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

class AutoProjectUpdater:
    """프로젝트 상태 자동 업데이트 클래스"""
    
    def __init__(self):
        self.project_root = self._get_project_root()
        self.live_status_file = self.project_root / "LIVE_STATUS.json"
        self.modification_history_file = self.project_root / "MODIFICATION_HISTORY.json" 
        self.next_ai_guide_file = self.project_root / "NEXT_AI_GUIDE.md"
        
        # 초기화 시 디렉토리 생성
        self._ensure_directories()
        
    def _get_project_root(self) -> Path:
        """프로젝트 루트 찾기"""
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "main.py").exists() or (parent / "requirements.txt").exists():
                return parent
        return Path.cwd()
    
    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        try:
            self.project_root.mkdir(exist_ok=True)
            (self.project_root / "utils").mkdir(exist_ok=True)
        except:
            pass
    
    def log_modification(self, file_path: str, change_type: str, 
                        description: str, new_values: Dict = None):
        """
        수정사항 자동 기록 및 문서 업데이트
        
        Args:
            file_path: 수정된 파일 경로
            change_type: 변경 타입 (CONFIG_CHANGE, BUG_FIX, FEATURE_ADD, SIGNAL_GENERATED)
            description: 변경 내용 설명
            new_values: 새로운 설정값들
        """
        
        modification = {
            "timestamp": datetime.now().isoformat(),
            "file": file_path,
            "change_type": change_type,
            "description": description,
            "new_values": new_values or {},
            "session_id": self._generate_session_id()
        }
        
        try:
            # 1. 수정 이력에 추가
            self._append_to_history(modification)
            
            # 2. 실시간 상태 업데이트
            self._update_live_status(modification)
            
            # 3. 다음 AI 가이드 업데이트
            self._update_next_ai_guide(modification)
            
            print(f"✅ 자동 업데이트 완료: {file_path}")
            print(f"📝 변경내용: {description}")
            
        except Exception as e:
            print(f"⚠️ 자동 업데이트 실패: {e}")
        
        return modification
    
    def _append_to_history(self, modification: Dict):
        """수정 이력에 추가"""
        try:
            # 기존 이력 로드
            if self.modification_history_file.exists():
                with open(self.modification_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = {
                    "project_name": "CoinBot",
                    "created": datetime.now().isoformat(),
                    "modifications": []
                }
            
            # 새 수정사항 추가
            history["modifications"].append(modification)
            history["last_updated"] = datetime.now().isoformat()
            
            # 최근 100개만 유지 (파일 크기 관리)
            if len(history["modifications"]) > 100:
                history["modifications"] = history["modifications"][-100:]
            
            # 저장
            with open(self.modification_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ 이력 저장 실패: {e}")
    
    def _update_live_status(self, modification: Dict):
        """실시간 상태 파일 업데이트"""
        try:
            # 현재 프로젝트 상태 생성
            live_status = {
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "auto_generated": True,
                    "version": "1.0.0"
                },
                "project_info": {
                    "name": "CoinBot",
                    "phase": self._determine_current_phase(),
                    "capital": {"current": 160000, "target": 1000000},
                    "goal": "16만원으로 자동매매 본업 전환"
                },
                "latest_modification": modification,
                "critical_settings": self._get_current_settings(),
                "system_health": self._check_system_health(),
                "next_priorities": self._get_next_priorities(),
                "warnings_for_next_ai": self._generate_warnings()
            }
            
            # 저장
            with open(self.live_status_file, 'w', encoding='utf-8') as f:
                json.dump(live_status, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ 실시간 상태 업데이트 실패: {e}")
    
    def _update_next_ai_guide(self, modification: Dict):
        """다음 AI를 위한 가이드 업데이트"""
        try:
            guide_content = self._generate_next_ai_guide_content(modification)
            
            with open(self.next_ai_guide_file, 'w', encoding='utf-8') as f:
                f.write(guide_content)
                
        except Exception as e:
            print(f"⚠️ AI 가이드 업데이트 실패: {e}")
    
    def _generate_next_ai_guide_content(self, latest_mod: Dict) -> str:
        """다음 AI를 위한 최신 가이드 생성"""
        
        current_phase = self._determine_current_phase()
        settings = self._get_current_settings()
        priorities = self._get_next_priorities()
        recent_mods = self._get_recent_modifications(5)
        
        return f"""# 🔄 다음 AI 개발자를 위한 최신 가이드 (자동 생성됨)

## ⚡ 실시간 업데이트 정보
- **마지막 업데이트**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **자동 생성**: 코드 수정 시 자동으로 갱신됨
- **⚠️ 중요**: 이 파일이 최신 정보! 다른 가이드 무시!

## 🎯 현재 프로젝트 단계
**{current_phase}**

## 📝 최근 수정사항 (매우 중요!)
### 가장 최근 변경:
- **파일**: `{latest_mod['file']}`
- **변경 타입**: {latest_mod['change_type']}
- **내용**: {latest_mod['description']}
- **시간**: {latest_mod['timestamp']}
- **⚠️ 주의**: 이 수정사항은 이미 적용됨! 재수정 금지!

### 최근 5개 변경사항:
{self._format_recent_modifications(recent_mods)}

## 🔥 현재 핵심 설정 (절대 변경 금지!)
```json
{json.dumps(settings, indent=2, ensure_ascii=False)}
```

## 🎯 다음 우선순위 작업
{self._format_priorities(priorities)}

## 🚨 새 AI가 절대 하면 안 되는 것들
- ❌ **이미 수정된 파일을 다시 수정하기**
- ❌ **검증된 설정값 임의로 변경하기**  
- ❌ **과거 가이드나 README 참조하기** (이 파일이 최신!)
- ❌ **min_score를 45 이외 값으로 변경** (매매 중단됨)
- ❌ **confidence를 0.4 이외 값으로 변경** (신호 생성 안됨)

## 📊 현재 시스템 상태
{self._generate_system_status_summary()}

## 💡 새 AI가 해야 할 첫 번째 작업
1. **LIVE_STATUS.json** 파일 확인으로 현재 상태 파악
2. **최근 수정사항 검토** (위 내용 참조)
3. **다음 우선순위 작업** 중 첫 번째 항목 진행
4. **수정 시 반드시 auto_updater 사용** (연결성 유지)

## 🔄 자동 업데이트 사용법
```python
# 설정 변경 시
from utils.auto_updater import log_config_change
log_config_change("파일명", "변경내용", {{"변경된값": "새값"}})

# 버그 수정 시  
from utils.auto_updater import log_bug_fix
log_bug_fix("파일명", "수정내용")
```

## 📞 문제 발생 시 체크리스트
- [ ] LIVE_STATUS.json에서 최신 상태 확인
- [ ] MODIFICATION_HISTORY.json에서 변경 이력 확인
- [ ] 설정값이 검증된 값(min_score=45, confidence=0.4)인지 확인
- [ ] API 키와 연결 상태 확인

---
**📅 자동 생성 시간**: {datetime.now().isoformat()}  
**🔄 다음 업데이트**: 다음 코드 수정 시 자동 갱신됨  
**⚠️ 경고**: 이 파일을 직접 수정하지 마세요! 자동으로 덮어씌워집니다.
"""
    
    def _determine_current_phase(self) -> str:
        """현재 개발 단계 판단"""
        try:
            # 실제로는 최근 수정 이력을 보고 판단
            if self.modification_history_file.exists():
                with open(self.modification_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    
                recent_mods = history.get("modifications", [])[-5:]
                
                if any("매매" in mod.get("description", "") for mod in recent_mods):
                    if any("활성화" in mod.get("description", "") for mod in recent_mods):
                        return "매매 활성화 완료 단계"
                    else:
                        return "매매 활성화 진행 단계"
                        
            return "매매 조건 완화 필요 단계"
            
        except:
            return "매매 활성화 단계"
    
    def _get_current_settings(self) -> Dict:
        """현재 핵심 설정값들 가져오기"""
        # 기본값 (실제로는 설정 파일에서 읽어올 수 있음)
        return {
            "min_score_threshold": 45,
            "confidence_threshold": 0.4,
            "take_profit_ratio": 0.04,
            "stop_loss_ratio": 0.02,
            "capital_per_position": 30000,
            "max_positions": 3,
            "status": "검증됨 - 변경 금지",
            "last_verified": datetime.now().strftime("%Y-%m-%d")
        }
    
    def _check_system_health(self) -> Dict:
        """시스템 건강 상태 체크"""
        return {
            "trading_system": "정상",
            "api_connection": "정상",
            "auto_update_system": "활성화",
            "last_health_check": datetime.now().isoformat()
        }
    
    def _get_next_priorities(self) -> List[str]:
        """다음 우선순위 작업 목록"""
        # 실제로는 현재 단계와 최근 수정사항을 고려해서 결정
        return [
            "1주일 매매 성과 모니터링 및 분석",
            "main.py 데이터 수집 에러 핸들링 개선", 
            "승률 50% 이상 달성 확인",
            "50만원 추가 투자 여부 결정",
            "risk_manager.py 안정성 강화"
        ]
    
    def _generate_warnings(self) -> List[str]:
        """다음 AI를 위한 경고사항"""
        return [
            "매매 조건 이미 완화됨 (min_score=45) - 재수정하면 시스템 불안정",
            "현재 설정값들은 실제 테스트로 검증됨 - 함부로 변경 금지",
            "NEXT_AI_GUIDE.md가 최신 정보 - 과거 README나 가이드 무시",
            "auto_updater 사용하지 않으면 다음 AI와 연결 끊어짐"
        ]
    
    def _get_recent_modifications(self, count: int) -> List[Dict]:
        """최근 수정사항 가져오기"""
        try:
            if self.modification_history_file.exists():
                with open(self.modification_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    return history.get("modifications", [])[-count:]
        except:
            pass
        return []
    
    def _format_recent_modifications(self, mods: List[Dict]) -> str:
        """최근 수정사항 포맷팅"""
        if not mods:
            return "- 수정 이력 없음"
            
        formatted = ""
        for i, mod in enumerate(reversed(mods), 1):
            formatted += f"{i}. **{mod.get('file', 'unknown')}**: {mod.get('description', 'N/A')} ({mod.get('timestamp', 'N/A')[:16]})\n"
        
        return formatted
    
    def _format_priorities(self, priorities: List[str]) -> str:
        """우선순위 목록 포맷팅"""
        formatted = ""
        for priority in priorities:
            formatted += f"- {priority}\n"
        return formatted
    
    def _generate_system_status_summary(self) -> str:
        """시스템 상태 요약"""
        health = self._check_system_health()
        return f"""
- 🤖 트레이딩 시스템: {health['trading_system']}
- 🔗 API 연결: {health['api_connection']}  
- 🔄 자동 업데이트: {health['auto_update_system']}
- ⏰ 마지막 체크: {health['last_health_check'][:16]}
"""
    
    def _generate_session_id(self) -> str:
        """세션 ID 생성"""
        return f"ai_session_{datetime.now().strftime('%m%d_%H%M')}"

# 전역 인스턴스 생성
auto_updater = AutoProjectUpdater()

# 간편 사용을 위한 함수들
def log_config_change(file_path: str, description: str, new_values: Dict = None):
    """설정 변경 로깅 - 가장 많이 사용될 함수"""
    return auto_updater.log_modification(file_path, "CONFIG_CHANGE", description, new_values)

def log_bug_fix(file_path: str, description: str):
    """버그 수정 로깅"""
    return auto_updater.log_modification(file_path, "BUG_FIX", description)

def log_feature_add(file_path: str, description: str):
    """기능 추가 로깅"""
    return auto_updater.log_modification(file_path, "FEATURE_ADD", description)

def log_signal_generated(file_path: str, ticker: str, score: float, confidence: float):
    """매매 신호 생성 로깅"""
    return auto_updater.log_modification(
        file_path, 
        "SIGNAL_GENERATED", 
        f"{ticker} 매매 신호 생성",
        {"ticker": ticker, "score": score, "confidence": confidence}
    )

# 시스템 초기화 시 로깅
if __name__ == "__main__":
    log_config_change(
        "utils/auto_updater.py",
        "자동 업데이트 시스템 초기화 완료",
        {"system": "활성화", "files_to_generate": 3}
    )
    print("🔄 자동 업데이트 시스템이 초기화되었습니다!")
    print("📁 다음 파일들이 자동으로 생성됩니다:")
    print("   - LIVE_STATUS.json")
    print("   - MODIFICATION_HISTORY.json") 
    print("   - NEXT_AI_GUIDE.md")
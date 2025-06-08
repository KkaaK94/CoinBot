#!/usr/bin/env python3
# scripts/test_auto_update.py
"""
🧪 자동 업데이트 시스템 테스트 스크립트
실제 설정 변경을 시뮬레이션하여 자동 문서화 기능 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 파이썬 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from utils.auto_updater import log_config_change, log_bug_fix, log_feature_add
    print("✅ auto_updater 모듈 import 성공!")
except ImportError as e:
    print(f"❌ auto_updater 모듈 import 실패: {e}")
    print("📁 utils/auto_updater.py 파일이 있는지 확인해주세요.")
    sys.exit(1)

def test_config_change():
    """설정 변경 테스트"""
    print("\n🔧 설정 변경 테스트 중...")
    
    log_config_change(
        "core/strategy_engine.py",
        "매매 활성화를 위한 조건 완화 (테스트)",
        {
            "min_score": {"old": 75, "new": 45},
            "confidence": {"old": 0.6, "new": 0.4},
            "reason": "24시간 매매 없음 문제 해결"
        }
    )
    
    print("✅ 설정 변경 로깅 완료!")

def test_bug_fix():
    """버그 수정 테스트"""
    print("\n🐛 버그 수정 테스트 중...")
    
    log_bug_fix(
        "main.py",
        "데이터 수집 실패 시 재시도 로직 추가 (테스트)"
    )
    
    print("✅ 버그 수정 로깅 완료!")

def test_feature_add():
    """기능 추가 테스트"""
    print("\n🚀 기능 추가 테스트 중...")
    
    log_feature_add(
        "utils/auto_updater.py",
        "자동 상태 업데이트 시스템 구축 완료 (테스트)"
    )
    
    print("✅ 기능 추가 로깅 완료!")

def check_generated_files():
    """생성된 파일들 확인"""
    print("\n📁 생성된 파일들 확인 중...")
    
    files_to_check = [
        "LIVE_STATUS.json",
        "MODIFICATION_HISTORY.json", 
        "NEXT_AI_GUIDE.md"
    ]
    
    for file_name in files_to_check:
        file_path = project_root / file_name
        if file_path.exists():
            print(f"✅ {file_name} - 생성됨 ({file_path.stat().st_size} bytes)")
        else:
            print(f"❌ {file_name} - 생성되지 않음")

def display_next_ai_guide_preview():
    """생성된 NEXT_AI_GUIDE.md 미리보기"""
    print("\n📖 NEXT_AI_GUIDE.md 미리보기:")
    print("=" * 60)
    
    guide_file = project_root / "NEXT_AI_GUIDE.md"
    if guide_file.exists():
        try:
            with open(guide_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 처음 20줄만 표시
                lines = content.split('\n')[:20]
                print('\n'.join(lines))
                if len(content.split('\n')) > 20:
                    print("\n... (더 많은 내용이 있습니다)")
        except Exception as e:
            print(f"❌ 파일 읽기 실패: {e}")
    else:
        print("❌ NEXT_AI_GUIDE.md 파일이 없습니다.")
    
    print("=" * 60)

def main():
    """메인 테스트 실행"""
    print("🧪 CoinBot 자동 업데이트 시스템 테스트")
    print("=" * 50)
    
    # 1. 설정 변경 테스트
    test_config_change()
    
    # 2. 버그 수정 테스트  
    test_bug_fix()
    
    # 3. 기능 추가 테스트
    test_feature_add()
    
    # 4. 생성된 파일들 확인
    check_generated_files()
    
    # 5. 가이드 미리보기
    display_next_ai_guide_preview()
    
    print("\n🎯 테스트 완료!")
    print("\n📋 다음 단계:")
    print("1. 생성된 3개 파일을 프로젝트에 커밋")
    print("2. 새 채팅에서 '새 채팅용 템플릿' 메시지 사용")
    print("3. 자동 업데이트 시스템 작동 확인")
    
    print("\n🔄 새 채팅에서 사용할 메시지:")
    print("-" * 40)
    print("NEXT_AI_GUIDE.md를 먼저 읽고 현재 CoinBot 프로젝트 상태를 파악해주세요.")
    print("자동 업데이트 시스템이 적용되어 있으니 과거 가이드는 무시하고")  
    print("NEXT_AI_GUIDE.md의 최신 정보만 참조해서 다음 작업을 진행해주세요.")
    print("-" * 40)

if __name__ == "__main__":
    main()
#!/bin/bash
# 의존성 패키지 설치 문제 해결 스크립트

echo "🔧 Python 패키지 의존성 문제 해결 중..."

# 1. pip 및 기본 도구 업그레이드
echo "📦 pip 및 기본 도구 업그레이드..."
pip install --upgrade pip setuptools wheel

# 2. 문제가 되는 setuptools 버전 고정
echo "🔧 setuptools 버전 고정..."
pip uninstall -y setuptools
pip install setuptools==69.5.1

# 3. 핵심 패키지부터 설치
echo "🎯 핵심 패키지 설치..."
pip install pyupbit==0.2.31
pip install pandas>=2.0.0
pip install numpy>=1.24.0
pip install flask>=2.3.0
pip install python-telegram-bot>=20.7
pip install psutil>=5.9.0
pip install python-dotenv>=1.0.0
pip install requests>=2.31.0

# 4. 추가 패키지 설치 (오류 무시)
echo "📊 추가 패키지 설치..."
pip install ta>=0.10.2 || echo "⚠️ ta 패키지 설치 실패 (선택사항)"
pip install scipy>=1.10.0 || echo "⚠️ scipy 패키지 설치 실패 (선택사항)"
pip install scikit-learn>=1.3.0 || echo "⚠️ scikit-learn 패키지 설치 실패 (선택사항)"
pip install plotly>=5.15.0 || echo "⚠️ plotly 패키지 설치 실패 (선택사항)"
pip install schedule>=1.2.0 || echo "⚠️ schedule 패키지 설치 실패 (선택사항)"

echo "✅ 핵심 패키지 설치 완료!"
echo "🎯 이제 봇을 실행할 수 있습니다."

# 설치된 패키지 확인
echo ""
echo "📋 설치된 주요 패키지:"
pip list | grep -E "(pyupbit|pandas|numpy|flask|telegram|psutil|dotenv|requests)"
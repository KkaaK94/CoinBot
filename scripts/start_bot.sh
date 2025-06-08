#!/bin/bash
# 트레이딩 봇 시작 도우미 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 스크립트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🎯 트레이딩 봇 시작 도우미${NC}"
echo "=============================="

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3이 설치되어 있지 않습니다${NC}"
    exit 1
fi

# 가상환경 활성화 (있는 경우)
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo -e "${YELLOW}📁 가상환경 활성화 중...${NC}"
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# 봇 실행 옵션 선택
echo ""
echo "실행 모드를 선택하세요:"
echo "1) 일반 모드 (실제 거래)"
echo "2) 안전 모드 (모의 거래)"
echo "3) 환경 검증만"
echo "4) 재시작 없이 한 번만 실행"
echo ""

read -p "선택 (1-4): " choice

case $choice in
    1)
        echo -e "${GREEN}🚀 일반 모드로 시작합니다...${NC}"
        python3 "$SCRIPT_DIR/start_bot.py"
        ;;
    2)
        echo -e "${YELLOW}🛡️ 안전 모드로 시작합니다...${NC}"
        python3 "$SCRIPT_DIR/start_bot.py" --safe-mode
        ;;
    3)
        echo -e "${BLUE}🔍 환경 검증을 수행합니다...${NC}"
        python3 "$SCRIPT_DIR/start_bot.py" --check-only
        ;;
    4)
        echo -e "${YELLOW}🔄 재시작 없이 실행합니다...${NC}"
        python3 "$SCRIPT_DIR/start_bot.py" --no-restart
        ;;
    *)
        echo -e "${RED}❌ 올바른 선택지를 입력하세요${NC}"
        exit 1
        ;;
esac
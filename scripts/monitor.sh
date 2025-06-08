#!/bin/bash

LOG_FILE="/home/ubuntu/upbit/CoinBot/data/logs/monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] 시스템 모니터링 시작" >> $LOG_FILE

# PM2 프로세스 확인
if ! pm2 status | grep -q "online"; then
    echo "[$DATE] PM2 프로세스 재시작" >> $LOG_FILE
    pm2 restart all
    
    # 텔레그램 알림 (선택사항)
    curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
         -d "chat_id=$TELEGRAM_CHAT_ID" \
         -d "text=🚨 CoinBot PM2 프로세스 재시작됨 - $DATE"
fi

# 디스크 용량 확인
DISK_USAGE=$(df -h /home/ubuntu | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
    echo "[$DATE] 디스크 용량 경고: ${DISK_USAGE}%" >> $LOG_FILE
fi

# 메모리 사용량 확인
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f"), $3/$2 * 100.0}')
if [ "$MEMORY_USAGE" -gt 85 ]; then
    echo "[$DATE] 메모리 사용량 경고: ${MEMORY_USAGE}%" >> $LOG_FILE
fi

echo "[$DATE] 모니터링 완료" >> $LOG_FILE

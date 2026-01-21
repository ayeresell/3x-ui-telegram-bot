#!/bin/bash

# VPN Bot Update Script
# Скрипт для обновления бота

set -e

echo "🔄 Обновление VPN Bot"
echo "====================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Pull latest changes if using git
if [ -d .git ]; then
    echo "📥 Получение последних изменений из Git..."
    git pull
    echo -e "${GREEN}✅ Изменения получены${NC}"
    echo ""
fi

# Backup database
if [ -f data/vpn_bot.db ]; then
    echo "💾 Создание резервной копии базы данных..."
    mkdir -p backups
    cp data/vpn_bot.db "backups/vpn_bot_$(date +%Y%m%d_%H%M%S).db"
    echo -e "${GREEN}✅ Резервная копия создана${NC}"
    echo ""
fi

# Stop bot
echo "🛑 Остановка бота..."
docker compose down
echo -e "${GREEN}✅ Бот остановлен${NC}"
echo ""

# Rebuild and start
echo "🔨 Пересборка и запуск..."
docker compose up -d --build

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Бот успешно обновлен и запущен!${NC}"
    echo ""
    echo "📝 Последние логи:"
    docker compose logs --tail=20
    echo ""
    echo -e "${GREEN}🎉 Обновление завершено!${NC}"
else
    echo ""
    echo -e "${RED}❌ Ошибка при обновлении!${NC}"
    echo "Проверьте логи: docker compose logs"
    exit 1
fi

#!/bin/bash

# VPN Bot Deployment Script
# Скрипт для быстрого развертывания бота на VPS

set -e  # Exit on error

echo "🚀 VPN Bot Deployment Script"
echo "=============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Файл .env не найден!${NC}"
    echo ""
    
    if [ -f env.example ]; then
        echo "Создаю .env из env.example..."
        cp env.example .env
        echo -e "${GREEN}✅ Файл .env создан${NC}"
        echo ""
        echo -e "${YELLOW}⚠️  ВАЖНО: Отредактируйте файл .env перед запуском!${NC}"
        echo ""
        echo "Необходимо заполнить:"
        echo "  - BOT_TOKEN (получите у @BotFather)"
        echo "  - ADMIN_TG_ID (ваш Telegram ID)"
        echo "  - XUI_BASE_URL (адрес панели 3x-ui)"
        echo "  - XUI_USERNAME (логин от панели)"
        echo "  - XUI_PASSWORD (пароль от панели)"
        echo ""
        echo "Отредактируйте файл командой: nano .env"
        echo "После редактирования запустите скрипт снова."
        exit 1
    else
        echo -e "${RED}❌ Файл env.example не найден!${NC}"
        exit 1
    fi
fi

echo "📋 Проверка конфигурации..."

# Check required variables
required_vars=("BOT_TOKEN" "ADMIN_TG_ID" "XUI_BASE_URL" "XUI_USERNAME" "XUI_PASSWORD")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=your" .env || grep -q "^${var}=123" .env; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}❌ Не заполнены обязательные переменные в .env:${NC}"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Отредактируйте файл .env и заполните эти переменные."
    exit 1
fi

echo -e "${GREEN}✅ Конфигурация проверена${NC}"
echo ""

# Check if Docker is installed
echo "🐳 Проверка Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не установлен!${NC}"
    echo ""
    echo "Установите Docker:"
    echo "  Ubuntu/Debian: sudo apt install docker.io docker-compose-plugin"
    echo "  CentOS/RHEL: sudo yum install docker-ce docker-compose-plugin"
    exit 1
fi

if ! command -v docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose не установлен!${NC}"
    echo ""
    echo "Установите Docker Compose:"
    echo "  sudo apt install docker-compose-plugin"
    exit 1
fi

echo -e "${GREEN}✅ Docker установлен${NC}"
echo ""

# Create necessary directories
echo "📁 Создание директорий..."
mkdir -p data logs
echo -e "${GREEN}✅ Директории созданы${NC}"
echo ""

# Stop existing container if running
echo "🛑 Остановка существующих контейнеров..."
docker compose down 2>/dev/null || true
echo -e "${GREEN}✅ Контейнеры остановлены${NC}"
echo ""

# Build and start
echo "🔨 Сборка и запуск бота..."
docker compose up -d --build

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Бот успешно запущен!${NC}"
    echo ""
    echo "📊 Полезные команды:"
    echo "  Просмотр логов:      docker compose logs -f"
    echo "  Остановка бота:      docker compose down"
    echo "  Перезапуск бота:     docker compose restart"
    echo "  Статус контейнера:   docker compose ps"
    echo ""
    echo "🔍 Проверка статуса..."
    sleep 3
    docker compose ps
    echo ""
    echo "📝 Последние логи:"
    docker compose logs --tail=20
    echo ""
    echo -e "${GREEN}🎉 Развертывание завершено!${NC}"
    echo ""
    echo "Откройте бота в Telegram и отправьте /start"
else
    echo ""
    echo -e "${RED}❌ Ошибка при запуске бота!${NC}"
    echo ""
    echo "Проверьте логи: docker compose logs"
    exit 1
fi

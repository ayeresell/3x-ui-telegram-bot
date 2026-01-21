#!/bin/bash
# Скрипт для проверки сетевой доступности из контейнера

echo "=========================================="
echo "Тест сетевой доступности из контейнера"
echo "=========================================="
echo ""

# Загрузить переменные из .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Проверяем доступность из контейнера vpn_bot..."
echo ""

# Извлечь хост и порт из URL
HOST=$(echo $XUI_BASE_URL | sed -E 's|https?://([^:/]+).*|\1|')
PORT=$(echo $XUI_BASE_URL | sed -E 's|https?://[^:]+:([0-9]+).*|\1|')
PATH_PART=$(echo $XUI_BASE_URL | sed -E 's|https?://[^/]+(/.*)|\1|')

echo "Хост: $HOST"
echo "Порт: $PORT"
echo "Путь: $PATH_PART"
echo ""

echo "1. Проверка DNS из контейнера..."
echo "-------------------------------------------"
docker exec vpn_bot nslookup $HOST 2>&1 || echo "nslookup не доступен"
echo ""

echo "2. Проверка ping из контейнера..."
echo "-------------------------------------------"
docker exec vpn_bot ping -c 3 $HOST 2>&1 || echo "ping не доступен"
echo ""

echo "3. Проверка доступности порта из контейнера..."
echo "-------------------------------------------"
docker exec vpn_bot timeout 5 bash -c "cat < /dev/null > /dev/tcp/$HOST/$PORT" 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Порт $PORT доступен!"
else
    echo "❌ Порт $PORT недоступен из контейнера"
fi
echo ""

echo "4. Проверка curl из контейнера..."
echo "-------------------------------------------"
docker exec vpn_bot curl -k -v --connect-timeout 5 "$XUI_BASE_URL/login" 2>&1 | head -20
echo ""

echo "5. Проверка альтернативных адресов..."
echo "-------------------------------------------"

echo "Пробуем 172.17.0.1 (Docker bridge IP):"
docker exec vpn_bot curl -k -v --connect-timeout 5 "http://172.17.0.1:$PORT$PATH_PART/login" 2>&1 | head -10
echo ""

echo "Пробуем localhost:"
docker exec vpn_bot curl -k -v --connect-timeout 5 "http://localhost:$PORT$PATH_PART/login" 2>&1 | head -10
echo ""

echo "=========================================="
echo "Тест завершен"
echo "=========================================="
echo ""
echo "Рекомендации:"
echo "1. Если 172.17.0.1 работает - используйте его в XUI_BASE_URL"
echo "2. Если localhost работает - панель на том же сервере, используйте localhost"
echo "3. Если ничего не работает - проверьте файрвол и настройки панели"

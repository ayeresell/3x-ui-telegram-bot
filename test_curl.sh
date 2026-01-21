#!/bin/bash
# Скрипт для проверки подключения к 3x-ui через curl

echo "==================================================="
echo "Тест подключения к 3x-ui через curl"
echo "==================================================="
echo ""

# Загрузить переменные из .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "URL панели: $XUI_BASE_URL"
echo "Username: $XUI_USERNAME"
echo ""

echo "1. Проверка доступности панели..."
echo "---------------------------------------------------"
curl -k -v "$XUI_BASE_URL/login" 2>&1 | head -20
echo ""

echo "2. Попытка логина..."
echo "---------------------------------------------------"
curl -k -v -X POST "$XUI_BASE_URL/login" \
  -d "username=$XUI_USERNAME" \
  -d "password=$XUI_PASSWORD" \
  -c cookies.txt \
  2>&1 | grep -E "(HTTP|Set-Cookie|Location)"
echo ""

echo "3. Проверка cookies..."
echo "---------------------------------------------------"
if [ -f cookies.txt ]; then
    cat cookies.txt
    echo ""
    
    echo "4. Попытка получить список инбаундов..."
    echo "---------------------------------------------------"
    curl -k -v -X GET "$XUI_BASE_URL/panel/api/inbounds/list" \
      -b cookies.txt \
      2>&1 | head -30
    
    rm cookies.txt
else
    echo "Cookies не были сохранены - логин не удался"
fi

echo ""
echo "==================================================="
echo "Тест завершен"
echo "==================================================="

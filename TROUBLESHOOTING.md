# Устранение неполадок VPN Bot

## Ошибка: "All connection attempts failed"

Эта ошибка означает, что бот не может подключиться к панели 3x-ui.

### Шаг 1: Проверьте конфигурацию

На сервере откройте файл `.env` и проверьте настройки:

```bash
nano .env
```

Убедитесь, что заполнены:
- `XUI_BASE_URL` - URL панели (например: `https://your-server.com:2053` или `http://localhost:2053`)
- `XUI_USERNAME` - логин от панели (обычно `admin`)
- `XUI_PASSWORD` - пароль от панели
- `XUI_VERIFY_SSL` - должно быть `false` для самоподписанных сертификатов

### Шаг 2: Проверьте доступность панели

```bash
# Проверьте, работает ли панель
curl -k https://your-server.com:2053/login

# Или для HTTP
curl http://localhost:2053/login
```

Если команда выдает ошибку, значит панель недоступна.

### Шаг 3: Запустите тест подключения

```bash
# Вариант A: Python тест (внутри контейнера)
docker exec -it vpn_bot python test_xui_connection.py

# Вариант B: Curl тест (на хосте)
chmod +x test_curl.sh
./test_curl.sh
```

Тест покажет детальную информацию о проблеме.

### Шаг 4: Проверьте логи

```bash
# Смотрите логи бота
docker compose logs -f vpn_bot

# Или файл логов
tail -f logs/bot.log
```

## Типичные проблемы и решения

### 1. Неверный URL панели

**Проблема:** `XUI_BASE_URL` указан неправильно

**Решение:**
- Проверьте порт (обычно 2053 или другой, который вы настроили)
- Используйте `http://` для незащищенного соединения или `https://` для защищенного
- Если бот и панель в одной сети Docker, используйте имя контейнера
- Если панель на том же сервере, можно использовать `http://localhost:PORT`

Примеры правильных URL:
```bash
XUI_BASE_URL=http://localhost:2053
XUI_BASE_URL=https://your-domain.com:2053
XUI_BASE_URL=http://3x-ui:2053  # если в одной Docker сети
```

### 2. Проблемы с SSL сертификатом

**Проблема:** Ошибки SSL при подключении к HTTPS

**Решение:** Добавьте в `.env`:
```bash
XUI_VERIFY_SSL=false
```

### 3. Неверные учетные данные

**Проблема:** Логин или пароль неправильные

**Решение:**
1. Проверьте, что можете войти в панель через браузер
2. Убедитесь, что в `.env` нет лишних пробелов:
   ```bash
   XUI_USERNAME=admin
   XUI_PASSWORD=your_password
   ```
   НЕ так: `XUI_USERNAME = admin` (пробелы вокруг `=`)

### 4. Панель 3x-ui не запущена

**Проблема:** Панель не работает

**Решение:**
```bash
# Проверьте статус
systemctl status x-ui

# Или для Docker версии
docker ps | grep x-ui

# Запустите панель
systemctl start x-ui
```

### 5. Файрвол блокирует подключение

**Проблема:** Порт панели закрыт

**Решение:**
```bash
# Откройте порт (замените 2053 на ваш)
ufw allow 2053

# Или для firewalld
firewall-cmd --permanent --add-port=2053/tcp
firewall-cmd --reload
```

### 6. Панель доступна только локально

**Проблема:** Панель слушает только на 127.0.0.1

**Решение:**
Если бот в Docker, а панель на хосте, используйте:
```bash
# В Linux - используйте IP хоста из Docker
XUI_BASE_URL=http://172.17.0.1:PORT/path

# Или используйте host.docker.internal (в некоторых версиях Docker)
XUI_BASE_URL=http://host.docker.internal:PORT/path

# Или добавьте бот в сеть хоста
docker compose down
# Отредактируйте docker-compose.yml, добавьте:
# network_mode: "host"
docker compose up -d
```

### 7. Панель на том же сервере, но недоступна из Docker

**Проблема:** Docker контейнер не может достучаться до портов хоста

**Решение 1 - Использовать IP хоста:**
```bash
# Узнайте IP хоста
ip addr show docker0

# Используйте этот IP (обычно 172.17.0.1)
XUI_BASE_URL=http://172.17.0.1:PORT/path
```

**Решение 2 - Добавить extra_hosts в docker-compose.yml:**
```yaml
services:
  bot:
    build: .
    container_name: vpn_bot
    env_file:
      - .env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

Затем в .env:
```bash
XUI_BASE_URL=http://host.docker.internal:PORT/path
```

## Дополнительная диагностика

### Проверка из контейнера

```bash
# Войдите в контейнер
docker exec -it vpn_bot bash

# Проверьте DNS
nslookup your-domain.com

# Проверьте доступность
curl -v -k https://your-domain.com:2053/login

# Проверьте переменные окружения
env | grep XUI
```

### Включение отладочных логов

В `.env` измените:
```bash
LOG_LEVEL=DEBUG
```

Перезапустите бота:
```bash
docker compose restart
```

## Все еще не работает?

1. Убедитесь, что панель 3x-ui работает и доступна
2. Проверьте, что можете войти в панель через браузер
3. Запустите `test_xui_connection.py` для детальной диагностики
4. Проверьте логи: `docker compose logs -f`
5. Проверьте файл `.env` на опечатки

## Полезные команды

```bash
# Перезапуск бота
docker compose restart

# Пересборка с нуля
docker compose down
docker compose up -d --build

# Просмотр логов
docker compose logs -f

# Проверка статуса
docker compose ps

# Вход в контейнер
docker exec -it vpn_bot bash
```

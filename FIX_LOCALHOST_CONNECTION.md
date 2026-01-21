# Исправление подключения к локальной панели 3x-ui

## Ваша ситуация

Панель 3x-ui работает на том же сервере, что и бот, и доступна только через localhost (127.0.0.1).
Ваш домен резолвится в `127.0.0.1`.

## Что было сделано

1. **Изменен docker-compose.yml** - добавлен `network_mode: "host"` вместо bridge network
2. **Уже есть поддержка XUI_VERIFY_SSL** для самоподписанных сертификатов
3. **Уже есть детальное логирование** в `services/xui_client.py`

## Инструкция для сервера

### Шаг 1: Обновите код

```bash
cd /opt/vpn-bot
git pull
```

### Шаг 2: Проверьте и обновите .env

```bash
nano .env
```

**ВАЖНО!** Измените URL на localhost:

```bash
# БЫЛО (не работает из Docker):
XUI_BASE_URL=https://your-domain.com:PORT/path
# или
XUI_BASE_URL=https://172.17.0.1:PORT/path

# ДОЛЖНО БЫТЬ:
XUI_BASE_URL=https://localhost:PORT/path
# или
XUI_BASE_URL=https://127.0.0.1:PORT/path

# Логин и пароль от панели
XUI_USERNAME=your_username
XUI_PASSWORD=your_password

# Отключить проверку SSL для самоподписанных сертификатов
XUI_VERIFY_SSL=false
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

### Шаг 3: Перезапустите бота

```bash
docker compose down
docker compose up -d --build
```

### Шаг 4: Смотрите логи

```bash
docker compose logs -f
```

Теперь в логах будет видно:
- `Base URL: https://localhost:PORT/path`
- `Login URL: https://localhost:PORT/path/login`
- `Username: your_username`
- `SSL Verify: False`
- Детальную информацию о подключении

### Шаг 5: Попробуйте /settings в боте

Если все настроено правильно, должно работать!

## Почему это работает?

### Проблема была в том:

1. **Ваш домен резолвится в 127.0.0.1**
   ```bash
   curl показал: IPv4: 127.0.0.1
   ```

2. **Из Docker контейнера 127.0.0.1 - это сам контейнер, а не хост**
   - С хоста: `your-domain` → `127.0.0.1` → работает ✅
   - Из Docker: `your-domain` → `127.0.0.1` → контейнер, а не хост ❌

3. **172.17.0.1 тоже не работал** - таймаут, потому что панель слушает только на localhost

### Решение:

`network_mode: "host"` - контейнер использует сеть хоста напрямую:
- `localhost` в контейнере = `localhost` на хосте ✅
- `127.0.0.1` в контейнере = `127.0.0.1` на хосте ✅

## Проверка доступности панели

Если все еще не работает, проверьте:

```bash
# 1. Панель доступна с хоста
curl -k https://localhost:PORT/path/login

# 2. Панель работает
systemctl status x-ui

# 3. Проверьте из контейнера (после запуска с network_mode: host)
docker exec -it vpn_bot curl -k https://localhost:PORT/path/login
```

Все три команды должны вернуть HTML страницу логина.

## Возможные проблемы

### Проблема 1: SSL Certificate Error

**Симптом:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Решение:** Убедитесь, что в .env установлено:
```bash
XUI_VERIFY_SSL=false
```

### Проблема 2: Connection Refused

**Симптом:** `Connection refused`

**Решение:** 
- Проверьте, что панель запущена: `systemctl status x-ui`
- Проверьте правильность порта (54544)
- Проверьте, что панель слушает на localhost: `netstat -tlnp | grep 54544`

### Проблема 3: Timeout

**Симптом:** `Connection timeout`

**Решение:**
- Убедитесь, что `network_mode: "host"` в docker-compose.yml
- Перезапустите: `docker compose down && docker compose up -d --build`

### Проблема 4: Authentication Failed (Status 200, но "No cookies received")

**Симптом:** Статус 200, но "No cookies received from 3x-ui panel"

**Решение:**
- Проверьте логин и пароль
- Посмотрите в логах "Response body" - там будет причина
- Попробуйте войти в панель через браузер с теми же учетными данными

### Проблема 5: Wrong username/password

**Симптом:** В логах "Response body" показывает ошибку аутентификации

**Решение:**
- Проверьте логин и пароль в .env
- Убедитесь, что нет лишних пробелов
- Попробуйте войти через браузер

## Что изменилось в коде

### docker-compose.yml
```yaml
# БЫЛО:
networks:
  - vpn_network

networks:
  vpn_network:
    driver: bridge

# СТАЛО:
network_mode: "host"
```

## Контакты для отладки

Если проблема сохраняется, пришлите:
1. Вывод `docker compose logs -f` после попытки /settings
2. Вывод `curl -k https://localhost:PORT/path/login`
3. Содержимое .env (без паролей)
4. Вывод `systemctl status x-ui`

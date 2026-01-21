#!/usr/bin/env python3
"""Скрипт для проверки подключения к 3x-ui панели."""

import asyncio
import sys
from services.xui_client import XUIClient, XUIClientError
from core.config import settings
from core.logger import log


async def test_connection():
    """Тестирование подключения к 3x-ui."""
    print("=" * 60)
    print("Тест подключения к 3x-ui панели")
    print("=" * 60)
    print()
    
    print(f"📡 URL панели: {settings.XUI_BASE_URL}")
    print(f"👤 Имя пользователя: {settings.XUI_USERNAME}")
    print(f"🔐 Пароль: {'*' * len(settings.XUI_PASSWORD)}")
    print(f"🔒 Проверка SSL: {settings.XUI_VERIFY_SSL}")
    print()
    
    try:
        print("🔄 Попытка подключения...")
        print()
        
        async with XUIClient() as xui:
            print("✅ Успешная авторизация!")
            print()
            
            print("📋 Получение списка инбаундов...")
            inbounds = await xui.get_inbound_list()
            
            if inbounds:
                print(f"✅ Найдено инбаундов: {len(inbounds)}")
                print()
                print("Список инбаундов:")
                for inbound in inbounds:
                    inbound_id = inbound.get("id")
                    remark = inbound.get("remark", "Без названия")
                    protocol = inbound.get("protocol", "Unknown")
                    port = inbound.get("port", 0)
                    enable = inbound.get("enable", False)
                    status = "🟢 Включен" if enable else "🔴 Выключен"
                    print(f"  • ID: {inbound_id} | {remark} | {protocol}:{port} | {status}")
                print()
                print("=" * 60)
                print("✅ Тест успешно завершен!")
                print("=" * 60)
                return True
            else:
                print("⚠️  Инбаунды не найдены (список пуст)")
                return True
    
    except XUIClientError as e:
        print()
        print("=" * 60)
        print("❌ Ошибка подключения к 3x-ui")
        print("=" * 60)
        print()
        print(f"Описание ошибки: {e}")
        print()
        print("Возможные причины:")
        print("  1. Неверный URL панели (проверьте XUI_BASE_URL)")
        print("  2. Неверные логин/пароль (проверьте XUI_USERNAME и XUI_PASSWORD)")
        print("  3. Панель недоступна (проверьте, работает ли 3x-ui)")
        print("  4. Проблемы с сетью или файрволом")
        print("  5. Проблемы с SSL сертификатом (попробуйте XUI_VERIFY_SSL=false)")
        print()
        print("Рекомендации:")
        print("  • Проверьте, что панель доступна в браузере")
        print("  • Убедитесь, что логин/пароль правильные")
        print("  • Проверьте файл .env на сервере")
        print()
        return False
    
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Неожиданная ошибка")
        print("=" * 60)
        print()
        print(f"Тип ошибки: {type(e).__name__}")
        print(f"Описание: {e}")
        print()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)

"""User keyboards for the bot."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_request_access_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for requesting access."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Запросить доступ")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard for approved users."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мой профиль")],
            [KeyboardButton(text="🔗 Подключиться")],
            [KeyboardButton(text="📖 Инструкции")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Cancel keyboard for FSM states."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return keyboard

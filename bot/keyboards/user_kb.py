"""User keyboards for the bot."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove


def get_request_access_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for requesting access."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Запросить доступ", callback_data="request_access")]
        ]
    )
    return keyboard


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard for approved users."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="user_profile")],
            [InlineKeyboardButton(text="🔗 Подключиться", callback_data="user_connection")],
            [InlineKeyboardButton(text="📖 Инструкции", callback_data="user_instructions")]
        ]
    )
    return keyboard


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel keyboard for FSM states."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_request")]
        ]
    )
    return keyboard


def remove_keyboard() -> ReplyKeyboardRemove:
    """Remove reply keyboard."""
    return ReplyKeyboardRemove()

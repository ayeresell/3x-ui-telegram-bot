"""Admin keyboards for the bot."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_approval_keyboard(user_id: int, request_id: int) -> InlineKeyboardMarkup:
    """Keyboard for approving/rejecting access requests."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_select:{user_id}:{request_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject:{user_id}:{request_id}"
                )
            ]
        ]
    )
    return keyboard


def get_inbound_selection_keyboard(user_id: int, request_id: int, inbounds: list) -> InlineKeyboardMarkup:
    """Keyboard for selecting inbound during approval."""
    buttons = []
    
    for inbound in inbounds:
        buttons.append([
            InlineKeyboardButton(
                text=f"🔹 {inbound.remark} ({inbound.protocol}:{inbound.port})",
                callback_data=f"approve_inbound:{user_id}:{request_id}:{inbound.inbound_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Отмена",
            callback_data=f"reject:{user_id}:{request_id}"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_inbound_list_keyboard(inbounds: list) -> InlineKeyboardMarkup:
    """Keyboard with list of all inbounds from 3x-ui."""
    buttons = []
    
    for inbound in inbounds:
        status_emoji = "✅" if inbound.get("is_enabled") else "⚪"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {inbound['remark']} ({inbound['protocol']}:{inbound['port']})",
                callback_data=f"toggle_inbound:{inbound['id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data="refresh_inbounds"
        )
    ])
    
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_back"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_user_management_keyboard(user_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Keyboard for managing a specific user."""
    buttons = []
    
    # Toggle active status button
    if is_active:
        buttons.append([
            InlineKeyboardButton(
                text="🔴 Деактивировать",
                callback_data=f"deactivate:{user_id}"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text="🟢 Активировать",
                callback_data=f"activate:{user_id}"
            )
        ])
    
    # Delete button
    buttons.append([
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"delete:{user_id}"
        )
    ])
    
    # Back button
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_list"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_user_list_keyboard(users: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Keyboard with paginated user list."""
    buttons = []
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_users = users[start_idx:end_idx]
    
    for user in page_users:
        status_emoji = "✅" if user.is_active else "❌"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {user.full_name} (@{user.username or 'no_username'})",
                callback_data=f"user_info:{user.id}"
            )
        ])
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"admin_page:{page-1}")
        )
    if end_idx < len(users):
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"admin_page:{page+1}")
        )
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Back to main menu button
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_back"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_delete_confirmation_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Keyboard for confirming user deletion."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"confirm_delete:{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"user_info:{user_id}"
                )
            ]
        ]
    )
    return keyboard


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Main admin menu keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Пользователи бота",
                    callback_data="admin_users"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Все клиенты 3x-ui",
                    callback_data="admin_all_clients"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Настройки инбаундов",
                    callback_data="admin_settings"
                )
            ]
        ]
    )
    return keyboard

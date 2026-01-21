"""Admin handlers for the bot."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin_kb import (
    get_user_list_keyboard,
    get_user_management_keyboard,
    get_delete_confirmation_keyboard,
    get_inbound_selection_keyboard,
    get_inbound_list_keyboard
)
from bot.keyboards.user_kb import get_main_menu_keyboard
from database.repositories import UserRepository, AccessRequestRepository, ActiveInboundRepository
from services.xui_client import XUIClient, XUIClientError
from utils.formatters import format_traffic_gb, format_status, format_date
from core.logger import log
from bot.middlewares.auth import AdminCheckMiddleware


router = Router()
router.message.middleware(AdminCheckMiddleware())
router.callback_query.middleware(AdminCheckMiddleware())


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    """Handle /admin command - show user list."""
    user_repo = UserRepository(session)
    users = await user_repo.get_all()
    
    if not users:
        await message.answer("📋 Список пользователей пуст.")
        return
    
    total_users = len(users)
    active_users = len([u for u in users if u.is_active])
    approved_users = len([u for u in users if u.is_approved])
    
    stats_text = (
        "👨‍💼 <b>Панель администратора</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Одобрено: {approved_users}\n"
        f"🟢 Активных: {active_users}\n\n"
        "Выберите пользователя для управления:"
    )
    
    await message.answer(
        stats_text,
        reply_markup=get_user_list_keyboard(users),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_page:"))
async def admin_page(callback: CallbackQuery, session: AsyncSession):
    """Handle pagination for user list."""
    page = int(callback.data.split(":")[1])
    
    user_repo = UserRepository(session)
    users = await user_repo.get_all()
    
    await callback.message.edit_reply_markup(
        reply_markup=get_user_list_keyboard(users, page=page)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("approve_select:"))
async def approve_select_inbound(callback: CallbackQuery, session: AsyncSession):
    """Show inbound selection for approval."""
    _, user_id, request_id = callback.data.split(":")
    user_id = int(user_id)
    request_id = int(request_id)
    
    inbound_repo = ActiveInboundRepository(session)
    enabled_inbounds = await inbound_repo.get_enabled()
    
    if not enabled_inbounds:
        await callback.answer(
            "❌ Нет активных инбаундов. Используйте /settings для настройки.",
            show_alert=True
        )
        return
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        "🔹 <b>Выберите инбаунд для подключения:</b>",
        reply_markup=get_inbound_selection_keyboard(user_id, request_id, enabled_inbounds),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("approve_inbound:"))
async def approve_request(callback: CallbackQuery, session: AsyncSession):
    """Handle access request approval with selected inbound."""
    _, user_id, request_id, inbound_id = callback.data.split(":")
    user_id = int(user_id)
    request_id = int(request_id)
    inbound_id = int(inbound_id)
    
    user_repo = UserRepository(session)
    request_repo = AccessRequestRepository(session)
    inbound_repo = ActiveInboundRepository(session)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    inbound = await inbound_repo.get_by_inbound_id(inbound_id)
    if not inbound:
        await callback.answer("❌ Инбаунд не найден.", show_alert=True)
        return
    
    try:
        # Create client in 3x-ui
        async with XUIClient() as xui:
            await xui.create_client(
                email=user.email,
                uuid=user.uuid,
                enable=True,
                inbound_id=inbound_id
            )
        
        # Update database
        await user_repo.update_approval_status(user_id, True, inbound_id)
        await request_repo.update_status(request_id, "approved", callback.from_user.id)
        
        # Notify user
        await callback.bot.send_message(
            user.tg_id,
            "🎉 <b>Ваша заявка одобрена!</b>\n\n"
            f"Инбаунд: {inbound.remark} ({inbound.protocol})\n\n"
            "Теперь вы можете пользоваться VPN.\n"
            "Используйте /start для доступа к функциям.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        
        # Update admin message
        await callback.message.edit_text(
            f"{callback.message.text}\n\n"
            f"✅ <b>Одобрено администратором</b>\n"
            f"Инбаунд: {inbound.remark}",
            parse_mode="HTML"
        )
        
        await callback.answer("✅ Заявка одобрена!")
        log.info(f"Admin {callback.from_user.id} approved user {user_id} with inbound {inbound_id}")
    
    except XUIClientError as e:
        error_msg = str(e)
        log.error(f"Error creating client in 3x-ui: {e}")
        
        # Check if it's a duplicate email error
        if "Duplicate email" in error_msg or "duplicate" in error_msg.lower():
            await callback.answer(
                f"❌ Клиент с email '{user.email}' уже существует в 3x-ui.\n"
                f"Удалите его из панели или используйте другой инбаунд.",
                show_alert=True
            )
        else:
            await callback.answer(
                f"❌ Ошибка при создании клиента в 3x-ui:\n{error_msg[:100]}",
                show_alert=True
            )
    except Exception as e:
        log.error(f"Error approving request: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("reject:"))
async def reject_request(callback: CallbackQuery, session: AsyncSession):
    """Handle access request rejection."""
    _, user_id, request_id = callback.data.split(":")
    user_id = int(user_id)
    request_id = int(request_id)
    
    user_repo = UserRepository(session)
    request_repo = AccessRequestRepository(session)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    try:
        # Update request status
        await request_repo.update_status(request_id, "rejected", callback.from_user.id)
        
        # Delete user from database to allow re-application
        await user_repo.delete_user(user_id)
        
        # Notify user
        await callback.bot.send_message(
            user.tg_id,
            "❌ К сожалению, ваша заявка на доступ была отклонена.\n\n"
            "Вы можете подать новую заявку, используя /start"
        )
        
        # Update admin message
        await callback.message.edit_text(
            f"{callback.message.text}\n\n"
            f"❌ <b>Отклонено администратором</b>",
            parse_mode="HTML"
        )
        
        await callback.answer("✅ Заявка отклонена. Пользователь удален из базы.")
        log.info(f"Admin {callback.from_user.id} rejected and deleted user {user_id}")
    
    except Exception as e:
        log.error(f"Error rejecting request: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("user_info:"))
async def show_user_info(callback: CallbackQuery, session: AsyncSession):
    """Show detailed user information."""
    user_id = int(callback.data.split(":")[1])
    
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    # Get traffic statistics
    try:
        async with XUIClient() as xui:
            traffic = await xui.get_client_traffic(user.email)
            traffic_text = format_traffic_gb(traffic["total"])
    except Exception as e:
        log.error(f"Error getting traffic: {e}")
        traffic_text = "Недоступно"
    
    user_info = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"📝 Имя: {user.full_name}\n"
        f"🆔 Telegram ID: {user.tg_id}\n"
        f"📱 Username: @{user.username or 'нет'}\n"
        f"📧 Email: {user.email}\n"
        f"🔐 Протокол: {user.protocol}\n"
        f"📊 Статус: {format_status(user.is_active)}\n"
        f"📈 Использовано: {traffic_text}\n"
        f"📅 Создан: {format_date(user.created_at)}\n"
    )
    
    await callback.message.edit_text(
        user_info,
        reply_markup=get_user_management_keyboard(user_id, user.is_active),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("deactivate:"))
async def deactivate_user(callback: CallbackQuery, session: AsyncSession):
    """Deactivate user."""
    user_id = int(callback.data.split(":")[1])
    
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    try:
        # Check if user has inbound_id
        if not user.inbound_id:
            await callback.answer("❌ У пользователя нет назначенного инбаунда.", show_alert=True)
            return
        
        # Update status in 3x-ui
        async with XUIClient() as xui:
            await xui.update_client_status(user.email, user.uuid, user.inbound_id, False)
        
        # Update database
        await user_repo.update_active_status(user_id, False)
        
        # Notify user
        await callback.bot.send_message(
            user.tg_id,
            "⚠️ Ваш доступ к VPN был деактивирован администратором."
        )
        
        await callback.answer("✅ Пользователь деактивирован.")
        
        # Refresh user info
        await show_user_info(callback, session)
        
        log.info(f"Admin {callback.from_user.id} deactivated user {user_id}")
    
    except Exception as e:
        log.error(f"Error deactivating user: {e}")
        await callback.answer("❌ Ошибка при деактивации.", show_alert=True)


@router.callback_query(F.data.startswith("activate:"))
async def activate_user(callback: CallbackQuery, session: AsyncSession):
    """Activate user."""
    user_id = int(callback.data.split(":")[1])
    
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    try:
        # Check if user has inbound_id
        if not user.inbound_id:
            await callback.answer("❌ У пользователя нет назначенного инбаунда.", show_alert=True)
            return
        
        # Update status in 3x-ui
        async with XUIClient() as xui:
            await xui.update_client_status(user.email, user.uuid, user.inbound_id, True)
        
        # Update database
        await user_repo.update_active_status(user_id, True)
        
        # Notify user
        await callback.bot.send_message(
            user.tg_id,
            "✅ Ваш доступ к VPN был активирован администратором.",
            reply_markup=get_main_menu_keyboard()
        )
        
        await callback.answer("✅ Пользователь активирован.")
        
        # Refresh user info
        await show_user_info(callback, session)
        
        log.info(f"Admin {callback.from_user.id} activated user {user_id}")
    
    except Exception as e:
        log.error(f"Error activating user: {e}")
        await callback.answer("❌ Ошибка при активации.", show_alert=True)


@router.callback_query(F.data.startswith("delete:"))
async def confirm_delete_user(callback: CallbackQuery):
    """Ask for confirmation before deleting user."""
    user_id = int(callback.data.split(":")[1])
    
    await callback.message.edit_text(
        "⚠️ <b>Подтверждение удаления</b>\n\n"
        "Вы уверены, что хотите удалить этого пользователя?\n"
        "Это действие нельзя отменить!",
        reply_markup=get_delete_confirmation_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def delete_user(callback: CallbackQuery, session: AsyncSession):
    """Delete user from database and 3x-ui."""
    user_id = int(callback.data.split(":")[1])
    
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return
    
    try:
        # Delete from 3x-ui (if user has inbound_id)
        if user.inbound_id:
            async with XUIClient() as xui:
                await xui.delete_client(user.uuid, user.inbound_id)
        
        # Delete from database
        await user_repo.delete_user(user_id)
        
        # Notify user
        try:
            await callback.bot.send_message(
                user.tg_id,
                "❌ Ваш доступ к VPN был удален администратором."
            )
        except Exception:
            pass  # User might have blocked the bot
        
        await callback.message.edit_text(
            "✅ Пользователь успешно удален."
        )
        
        log.info(f"Admin {callback.from_user.id} deleted user {user_id}")
    
    except Exception as e:
        log.error(f"Error deleting user: {e}")
        await callback.answer("❌ Ошибка при удалении.", show_alert=True)


@router.callback_query(F.data == "admin_list")
async def back_to_list(callback: CallbackQuery, session: AsyncSession):
    """Go back to user list."""
    user_repo = UserRepository(session)
    users = await user_repo.get_all()
    
    total_users = len(users)
    active_users = len([u for u in users if u.is_active])
    approved_users = len([u for u in users if u.is_approved])
    
    stats_text = (
        "👨‍💼 <b>Панель администратора</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Одобрено: {approved_users}\n"
        f"🟢 Активных: {active_users}\n\n"
        "Выберите пользователя для управления:"
    )
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_user_list_keyboard(users),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession):
    """Handle /settings command - manage active inbounds."""
    inbound_repo = ActiveInboundRepository(session)
    
    try:
        # Get all inbounds from 3x-ui
        async with XUIClient() as xui:
            all_inbounds = await xui.get_inbound_list()
        
        if not all_inbounds:
            await message.answer("❌ Не удалось получить список инбаундов из 3x-ui.")
            return
        
        # Get enabled inbounds from DB
        enabled_inbounds = await inbound_repo.get_enabled()
        enabled_ids = {inb.inbound_id for inb in enabled_inbounds}
        
        # Prepare inbound list with status
        inbound_list = []
        for inbound in all_inbounds:
            inbound_list.append({
                "id": inbound.get("id"),
                "remark": inbound.get("remark", "Без названия"),
                "protocol": inbound.get("protocol", "Unknown"),
                "port": inbound.get("port", 0),
                "is_enabled": inbound.get("id") in enabled_ids
            })
        
        settings_text = (
            "⚙️ <b>Настройки инбаундов</b>\n\n"
            "Выберите инбаунды, которые будут доступны для подключения пользователей.\n\n"
            "✅ - Включен\n"
            "⚪ - Выключен"
        )
        
        await message.answer(
            settings_text,
            reply_markup=get_inbound_list_keyboard(inbound_list),
            parse_mode="HTML"
        )
        
    except Exception as e:
        log.error(f"Error getting inbound list: {e}")
        await message.answer("❌ Ошибка при получении списка инбаундов.")


@router.callback_query(F.data.startswith("toggle_inbound:"))
async def toggle_inbound(callback: CallbackQuery, session: AsyncSession):
    """Toggle inbound enabled status."""
    inbound_id = int(callback.data.split(":")[1])
    
    inbound_repo = ActiveInboundRepository(session)
    
    try:
        # Get all inbounds from 3x-ui
        async with XUIClient() as xui:
            all_inbounds = await xui.get_inbound_list()
        
        # Find the inbound
        selected_inbound = None
        for inb in all_inbounds:
            if inb.get("id") == inbound_id:
                selected_inbound = inb
                break
        
        if not selected_inbound:
            await callback.answer("❌ Инбаунд не найден.", show_alert=True)
            return
        
        # Check if exists in DB
        existing = await inbound_repo.get_by_inbound_id(inbound_id)
        
        if existing:
            # Toggle status
            new_status = not existing.is_enabled
            await inbound_repo.toggle_enabled(inbound_id, new_status)
        else:
            # Create new active inbound
            await inbound_repo.create_or_update(
                inbound_id=inbound_id,
                remark=selected_inbound.get("remark", "Без названия"),
                protocol=selected_inbound.get("protocol", "Unknown"),
                port=selected_inbound.get("port", 0),
                is_enabled=True
            )
        
        # Refresh the list
        enabled_inbounds = await inbound_repo.get_enabled()
        enabled_ids = {inb.inbound_id for inb in enabled_inbounds}
        
        inbound_list = []
        for inbound in all_inbounds:
            inbound_list.append({
                "id": inbound.get("id"),
                "remark": inbound.get("remark", "Без названия"),
                "protocol": inbound.get("protocol", "Unknown"),
                "port": inbound.get("port", 0),
                "is_enabled": inbound.get("id") in enabled_ids
            })
        
        await callback.message.edit_reply_markup(
            reply_markup=get_inbound_list_keyboard(inbound_list)
        )
        await callback.answer("✅ Статус обновлен!")
        
    except Exception as e:
        log.error(f"Error toggling inbound: {e}")
        await callback.answer("❌ Ошибка при обновлении статуса.", show_alert=True)


@router.callback_query(F.data == "refresh_inbounds")
async def refresh_inbounds(callback: CallbackQuery, session: AsyncSession):
    """Refresh inbound list from 3x-ui."""
    await cmd_settings(callback.message, session)
    await callback.answer("🔄 Список обновлен!")

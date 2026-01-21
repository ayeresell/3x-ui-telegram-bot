"""User handlers for the bot."""

import uuid
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.user_kb import (
    get_request_access_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard
)
from database.repositories import UserRepository, AccessRequestRepository, ActiveInboundRepository
from services.xui_client import XUIClient
from utils.qr_generator import generate_vless_qr
from utils.formatters import format_traffic_gb, format_date, format_status
from core.config import settings
from core.logger import log
from bot.keyboards.admin_kb import get_approval_keyboard


class AccessRequestStates(StatesGroup):
    """FSM states for access request."""
    waiting_for_name = State()


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    """Handle /start command."""
    # Check if user is admin
    if message.from_user.id == settings.ADMIN_TG_ID:
        user_repo = UserRepository(session)
        users = await user_repo.get_all()
        
        total_users = len(users)
        active_users = len([u for u in users if u.is_active])
        approved_users = len([u for u in users if u.is_approved])
        
        # Import here to avoid circular import
        from bot.keyboards.admin_kb import get_admin_menu_keyboard
        
        stats_text = (
            "👨‍💼 <b>Панель администратора</b>\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"✅ Одобрено: {approved_users}\n"
            f"🟢 Активных: {active_users}\n\n"
            "Выберите действие:"
        )
        
        await message.answer(
            stats_text,
            reply_markup=get_admin_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Regular user flow
    user_repo = UserRepository(session)
    user = await user_repo.get_by_tg_id(message.from_user.id)
    
    if user and user.is_approved:
        # User is approved, show main menu
        await message.answer(
            f"👋 Привет, {user.full_name}!\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
    elif user and not user.is_approved:
        # User exists but not approved yet
        await message.answer(
            "⏳ Ваша заявка на рассмотрении.\n"
            "Ожидайте одобрения администратора.",
            reply_markup=get_request_access_keyboard()
        )
    else:
        # New user
        await message.answer(
            "👋 Добро пожаловать в VPN бот!\n\n"
            "Для получения доступа к VPN нажмите кнопку ниже:",
            reply_markup=get_request_access_keyboard()
        )


@router.message(F.text == "📝 Запросить доступ")
async def request_access(message: Message, state: FSMContext, session: AsyncSession):
    """Handle access request button."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_tg_id(message.from_user.id)
    
    if user:
        if user.is_approved:
            await message.answer(
                "✅ У вас уже есть доступ!",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(
                "⏳ Ваша заявка уже отправлена.\n"
                "Ожидайте одобрения администратора."
            )
        return
    
    # Start FSM for name input
    await state.set_state(AccessRequestStates.waiting_for_name)
    await message.answer(
        "📝 Пожалуйста, введите ваше имя:",
        reply_markup=get_cancel_keyboard()
    )


@router.message(StateFilter(AccessRequestStates.waiting_for_name), F.text == "❌ Отмена")
async def cancel_request(message: Message, state: FSMContext):
    """Cancel access request."""
    await state.clear()
    await message.answer(
        "❌ Запрос отменен.",
        reply_markup=get_request_access_keyboard()
    )


@router.message(StateFilter(AccessRequestStates.waiting_for_name))
async def process_name(message: Message, state: FSMContext, session: AsyncSession):
    """Process user name and create access request."""
    full_name = message.text.strip()
    
    if len(full_name) < 2:
        await message.answer("❌ Имя слишком короткое. Попробуйте еще раз:")
        return
    
    # Create user in database
    user_repo = UserRepository(session)
    request_repo = AccessRequestRepository(session)
    
    user_uuid = str(uuid.uuid4())
    
    # Format email as "Name_Username" or "Name_TelegramID"
    username_part = message.from_user.username if message.from_user.username else str(message.from_user.id)
    email = f"{full_name}_{username_part}"
    
    try:
        user = await user_repo.create(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            full_name=full_name,
            uuid=user_uuid,
            email=email
        )
        
        # Create access request
        access_request = await request_repo.create(user.id)
        
        # Notify admin
        admin_message = (
            "🔔 <b>Новая заявка на доступ</b>\n\n"
            f"👤 Имя: {full_name}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n"
            f"📱 Username: @{message.from_user.username or 'нет'}\n"
        )
        
        await message.bot.send_message(
            settings.ADMIN_TG_ID,
            admin_message,
            reply_markup=get_approval_keyboard(user.id, access_request.id),
            parse_mode="HTML"
        )
        
        await state.clear()
        await message.answer(
            "✅ Заявка отправлена!\n"
            "Ожидайте одобрения администратора.",
            reply_markup=get_request_access_keyboard()
        )
        
        log.info(f"Access request created: user_id={user.id}, tg_id={message.from_user.id}")
    
    except Exception as e:
        log.error(f"Error creating access request: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_request_access_keyboard()
        )
        await state.clear()


@router.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message, session: AsyncSession):
    """Show user profile with traffic statistics."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_tg_id(message.from_user.id)
    
    if not user or not user.is_approved:
        await message.answer(
            "❌ У вас нет доступа. Запросите доступ сначала.",
            reply_markup=get_request_access_keyboard()
        )
        return
    
    # Get traffic statistics from 3x-ui
    try:
        async with XUIClient() as xui:
            traffic = await xui.get_client_traffic(user.email)
            traffic_used = format_traffic_gb(traffic["total"])
    except Exception as e:
        log.error(f"Error getting traffic stats: {e}")
        traffic_used = "Недоступно"
    
    profile_text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"📝 Имя: {user.full_name}\n"
        f"🔐 Протокол: {user.protocol}\n"
        f"📊 Статус: {format_status(user.is_active)}\n"
        f"📈 Использовано трафика: {traffic_used}\n"
        f"📅 Дата подключения: {format_date(user.created_at)}\n"
    )
    
    await message.answer(profile_text, parse_mode="HTML")


@router.message(F.text == "🔗 Подключиться")
async def show_connection(message: Message, session: AsyncSession):
    """Generate and show connection link and QR code."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_tg_id(message.from_user.id)
    
    if not user or not user.is_approved:
        await message.answer(
            "❌ У вас нет доступа. Запросите доступ сначала.",
            reply_markup=get_request_access_keyboard()
        )
        return
    
    if not user.is_active:
        await message.answer(
            "❌ Ваш доступ деактивирован.\n"
            "Обратитесь к администратору."
        )
        return
    
    try:
        # Get connection link from 3x-ui API
        connection_link = None
        
        if user.inbound_id:
            # Get link from 3x-ui
            async with XUIClient() as xui:
                connection_link = await xui.get_client_link(user.inbound_id, user.email)
        
        if not connection_link:
            # Fallback: generate link manually (for old users or if API fails)
            log.warning(f"Could not get link from API, generating manually for {user.email}")
            from utils.qr_generator import generate_vless_link
            connection_link = generate_vless_link(
                user.uuid,
                user.email,
                server=settings.VLESS_SERVER,
                port=settings.VLESS_PORT,
                sni=settings.VLESS_SNI
            )
        
        # Generate QR code from link
        from utils.qr_generator import generate_qr_code
        qr_image = generate_qr_code(connection_link)
        
        # Send QR code
        qr_file = BufferedInputFile(qr_image.read(), filename="vpn_qr.png")
        await message.answer_photo(
            qr_file,
            caption=(
                "🔗 <b>Подключение к VPN</b>\n\n"
                "Отсканируйте QR-код или скопируйте ссылку ниже:\n\n"
                f"<code>{connection_link}</code>"
            ),
            parse_mode="HTML"
        )
        
        log.info(f"Connection info sent to user: tg_id={message.from_user.id}")
    
    except Exception as e:
        log.error(f"Error generating connection info: {e}")
        await message.answer("❌ Ошибка при генерации данных подключения.")


@router.message(F.text == "📖 Инструкции")
async def show_instructions(message: Message):
    """Show VPN client installation instructions."""
    instructions = (
        "📖 <b>Инструкции по подключению</b>\n\n"
        "<b>Шаг 1: Установите приложение</b>\n\n"
        "📱 <b>Android:</b>\n"
        "V2RayNG - https://play.google.com/store/apps/details?id=com.v2ray.ang\n\n"
        "💻 <b>Windows/Linux:</b>\n"
        "Nekoray - https://github.com/MatsuriDayo/nekoray/releases\n\n"
        "🍎 <b>iOS:</b>\n"
        "Streisand - https://apps.apple.com/app/streisand/id6450534064\n\n"
        "<b>Шаг 2: Подключитесь</b>\n"
        "1. Нажмите кнопку '🔗 Подключиться' в боте\n"
        "2. Отсканируйте QR-код в приложении или скопируйте ссылку\n"
        "3. Нажмите 'Подключиться' в приложении\n\n"
        "✅ Готово! Вы подключены к VPN."
    )
    
    await message.answer(instructions, parse_mode="HTML", disable_web_page_preview=True)

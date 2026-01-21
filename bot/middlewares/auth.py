"""Authentication and authorization middleware."""

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from core.config import settings
from core.logger import log


class AdminCheckMiddleware(BaseMiddleware):
    """Middleware to check if user is admin."""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Check if user is admin before processing."""
        user_id = event.from_user.id
        
        # Check if user is admin
        is_admin = user_id == settings.ADMIN_TG_ID
        data["is_admin"] = is_admin
        
        if not is_admin:
            if isinstance(event, Message):
                await event.answer("❌ У вас нет прав для выполнения этой команды.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ У вас нет прав для выполнения этого действия.", show_alert=True)
            return
        
        return await handler(event, data)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware to provide database session."""
    
    def __init__(self, session_pool):
        super().__init__()
        self.session_pool = session_pool
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Provide database session to handler."""
        async with self.session_pool() as session:
            data["session"] = session
            return await handler(event, data)

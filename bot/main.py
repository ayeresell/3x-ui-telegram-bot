"""Main entry point for the VPN bot."""

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.config import settings
from core.logger import log
from database.database import init_db, async_session_maker
from bot.middlewares.auth import DatabaseMiddleware
from bot.handlers import user, admin


async def main():
    """Initialize and start the bot."""
    log.info("Starting VPN bot...")
    
    # Initialize database
    try:
        await init_db()
    except Exception as e:
        log.error(f"Failed to initialize database: {e}")
        sys.exit(1)
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Register middlewares
    dp.message.middleware(DatabaseMiddleware(async_session_maker))
    dp.callback_query.middleware(DatabaseMiddleware(async_session_maker))
    
    # Register routers
    dp.include_router(user.router)
    dp.include_router(admin.router)
    
    log.info("Bot initialized successfully")
    
    # Start polling
    try:
        log.info("Starting polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        log.error(f"Error during polling: {e}")
    finally:
        await bot.session.close()
        log.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        sys.exit(1)

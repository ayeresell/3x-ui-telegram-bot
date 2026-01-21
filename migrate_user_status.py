"""
Migration script to update is_active default value.
Sets is_active = False for users who are not approved yet.
"""

import asyncio
from sqlalchemy import update
from database.database import async_session_maker, engine
from database.models import User, Base
from core.logger import log


async def migrate():
    """Update is_active for existing users."""
    try:
        # Create tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async with async_session_maker() as session:
            # Set is_active = False for users who are not approved
            result = await session.execute(
                update(User)
                .where(User.is_approved == False)
                .values(is_active=False)
            )
            
            await session.commit()
            
            rows_updated = result.rowcount
            log.info(f"Migration completed: Updated {rows_updated} users")
            print(f"✅ Migration completed: Updated {rows_updated} users with is_active=False")
            
    except Exception as e:
        log.error(f"Migration failed: {e}")
        print(f"❌ Migration failed: {e}")


if __name__ == "__main__":
    print("🔄 Running migration to update user status...")
    asyncio.run(migrate())

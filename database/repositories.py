"""Repository classes for database operations."""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, AccessRequest, ActiveInbound
from core.logger import log


class UserRepository:
    """Repository for User model operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        tg_id: int,
        username: Optional[str],
        full_name: str,
        uuid: str,
        email: str,
        protocol: str = "VLESS"
    ) -> User:
        """Create a new user."""
        user = User(
            tg_id=tg_id,
            username=username,
            full_name=full_name,
            uuid=uuid,
            email=email,
            protocol=protocol
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        log.info(f"Created user: tg_id={tg_id}, email={email}")
        return user
    
    async def get_by_tg_id(self, tg_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[User]:
        """Get all users."""
        result = await self.session.execute(select(User))
        return list(result.scalars().all())
    
    async def get_approved_users(self) -> List[User]:
        """Get all approved users."""
        result = await self.session.execute(
            select(User).where(User.is_approved == True)
        )
        return list(result.scalars().all())
    
    async def update_approval_status(self, user_id: int, is_approved: bool, inbound_id: Optional[int] = None) -> Optional[User]:
        """Update user approval status."""
        values = {"is_approved": is_approved, "updated_at": datetime.utcnow()}
        if inbound_id is not None:
            values["inbound_id"] = inbound_id
        
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(**values)
        )
        await self.session.commit()
        log.info(f"Updated approval status for user_id={user_id}: is_approved={is_approved}, inbound_id={inbound_id}")
        return await self.get_by_id(user_id)
    
    async def update_active_status(self, user_id: int, is_active: bool) -> Optional[User]:
        """Update user active status."""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=is_active, updated_at=datetime.utcnow())
        )
        await self.session.commit()
        log.info(f"Updated active status for user_id={user_id}: is_active={is_active}")
        return await self.get_by_id(user_id)
    
    async def delete_user(self, user_id: int) -> bool:
        """Delete user by ID."""
        result = await self.session.execute(
            delete(User).where(User.id == user_id)
        )
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            log.info(f"Deleted user_id={user_id}")
        return deleted


class AccessRequestRepository:
    """Repository for AccessRequest model operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user_id: int) -> AccessRequest:
        """Create a new access request."""
        access_request = AccessRequest(
            user_id=user_id,
            status="pending"
        )
        self.session.add(access_request)
        await self.session.commit()
        await self.session.refresh(access_request)
        log.info(f"Created access request for user_id={user_id}")
        return access_request
    
    async def get_by_id(self, request_id: int) -> Optional[AccessRequest]:
        """Get access request by ID."""
        result = await self.session.execute(
            select(AccessRequest).where(AccessRequest.id == request_id)
        )
        return result.scalar_one_or_none()
    
    async def get_pending_requests(self) -> List[AccessRequest]:
        """Get all pending access requests."""
        result = await self.session.execute(
            select(AccessRequest).where(AccessRequest.status == "pending")
        )
        return list(result.scalars().all())
    
    async def update_status(
        self,
        request_id: int,
        status: str,
        admin_id: Optional[int] = None
    ) -> Optional[AccessRequest]:
        """Update access request status."""
        await self.session.execute(
            update(AccessRequest)
            .where(AccessRequest.id == request_id)
            .values(
                status=status,
                admin_id=admin_id,
                processed_at=datetime.utcnow()
            )
        )
        await self.session.commit()
        log.info(f"Updated access request {request_id}: status={status}, admin_id={admin_id}")
        return await self.get_by_id(request_id)


class ActiveInboundRepository:
    """Repository for ActiveInbound model operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_or_update(
        self,
        inbound_id: int,
        remark: str,
        protocol: str,
        port: int,
        is_enabled: bool = True
    ) -> ActiveInbound:
        """Create or update active inbound."""
        # Check if exists
        result = await self.session.execute(
            select(ActiveInbound).where(ActiveInbound.inbound_id == inbound_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update
            await self.session.execute(
                update(ActiveInbound)
                .where(ActiveInbound.inbound_id == inbound_id)
                .values(
                    remark=remark,
                    protocol=protocol,
                    port=port,
                    is_enabled=is_enabled
                )
            )
            await self.session.commit()
            log.info(f"Updated active inbound: inbound_id={inbound_id}")
            return await self.get_by_inbound_id(inbound_id)
        else:
            # Create
            inbound = ActiveInbound(
                inbound_id=inbound_id,
                remark=remark,
                protocol=protocol,
                port=port,
                is_enabled=is_enabled
            )
            self.session.add(inbound)
            await self.session.commit()
            await self.session.refresh(inbound)
            log.info(f"Created active inbound: inbound_id={inbound_id}, remark={remark}")
            return inbound
    
    async def get_by_inbound_id(self, inbound_id: int) -> Optional[ActiveInbound]:
        """Get active inbound by inbound ID."""
        result = await self.session.execute(
            select(ActiveInbound).where(ActiveInbound.inbound_id == inbound_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[ActiveInbound]:
        """Get all active inbounds."""
        result = await self.session.execute(select(ActiveInbound))
        return list(result.scalars().all())
    
    async def get_enabled(self) -> List[ActiveInbound]:
        """Get all enabled active inbounds."""
        result = await self.session.execute(
            select(ActiveInbound).where(ActiveInbound.is_enabled == True)
        )
        return list(result.scalars().all())
    
    async def toggle_enabled(self, inbound_id: int, is_enabled: bool) -> Optional[ActiveInbound]:
        """Toggle inbound enabled status."""
        await self.session.execute(
            update(ActiveInbound)
            .where(ActiveInbound.inbound_id == inbound_id)
            .values(is_enabled=is_enabled)
        )
        await self.session.commit()
        log.info(f"Toggled inbound {inbound_id}: is_enabled={is_enabled}")
        return await self.get_by_inbound_id(inbound_id)
    
    async def delete_by_inbound_id(self, inbound_id: int) -> bool:
        """Delete active inbound by inbound ID."""
        result = await self.session.execute(
            delete(ActiveInbound).where(ActiveInbound.inbound_id == inbound_id)
        )
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            log.info(f"Deleted active inbound: inbound_id={inbound_id}")
        return deleted

"""User service for business logic."""

from typing import Optional, Tuple
import uuid as uuid_lib

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import UserRepository, AccessRequestRepository
from services.xui_client import XUIClient, XUIClientError
from core.logger import log


class UserService:
    """Service for user-related business logic."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.request_repo = AccessRequestRepository(session)
    
    async def create_access_request(
        self,
        tg_id: int,
        username: Optional[str],
        full_name: str
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Create access request for a new user.
        
        Returns:
            Tuple of (success, message, request_id)
        """
        # Check if user already exists
        existing_user = await self.user_repo.get_by_tg_id(tg_id)
        
        if existing_user:
            if existing_user.is_approved:
                return False, "У вас уже есть доступ!", None
            else:
                return False, "Ваша заявка уже отправлена.", None
        
        # Create user
        user_uuid = str(uuid_lib.uuid4())
        email = f"user_{tg_id}"
        
        try:
            user = await self.user_repo.create(
                tg_id=tg_id,
                username=username,
                full_name=full_name,
                uuid=user_uuid,
                email=email
            )
            
            # Create access request
            access_request = await self.request_repo.create(user.id)
            
            log.info(f"Access request created: user_id={user.id}, tg_id={tg_id}")
            return True, "Заявка успешно создана!", access_request.id
        
        except Exception as e:
            log.error(f"Error creating access request: {e}")
            return False, "Произошла ошибка при создании заявки.", None
    
    async def approve_user(
        self,
        user_id: int,
        request_id: int,
        admin_id: int
    ) -> Tuple[bool, str]:
        """
        Approve user access request and create client in 3x-ui.
        
        Returns:
            Tuple of (success, message)
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False, "Пользователь не найден."
        
        try:
            # Create client in 3x-ui
            async with XUIClient() as xui:
                await xui.create_client(
                    email=user.email,
                    uuid=user.uuid,
                    enable=True
                )
            
            # Update database
            await self.user_repo.update_approval_status(user_id, True)
            await self.request_repo.update_status(request_id, "approved", admin_id)
            
            log.info(f"User approved: user_id={user_id}, admin_id={admin_id}")
            return True, "Пользователь успешно одобрен!"
        
        except XUIClientError as e:
            log.error(f"Error creating client in 3x-ui: {e}")
            return False, f"Ошибка при создании клиента: {str(e)}"
        except Exception as e:
            log.error(f"Error approving user: {e}")
            return False, "Произошла ошибка при одобрении."
    
    async def reject_user(
        self,
        user_id: int,
        request_id: int,
        admin_id: int
    ) -> Tuple[bool, str]:
        """
        Reject user access request.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            await self.request_repo.update_status(request_id, "rejected", admin_id)
            log.info(f"User rejected: user_id={user_id}, admin_id={admin_id}")
            return True, "Заявка отклонена."
        except Exception as e:
            log.error(f"Error rejecting user: {e}")
            return False, "Произошла ошибка при отклонении."
    
    async def toggle_user_status(
        self,
        user_id: int,
        activate: bool
    ) -> Tuple[bool, str]:
        """
        Activate or deactivate user.
        
        Returns:
            Tuple of (success, message)
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False, "Пользователь не найден."
        
        try:
            # Update status in 3x-ui
            async with XUIClient() as xui:
                await xui.update_client_status(user.email, user.uuid, activate)
            
            # Update database
            await self.user_repo.update_active_status(user_id, activate)
            
            action = "активирован" if activate else "деактивирован"
            log.info(f"User {action}: user_id={user_id}")
            return True, f"Пользователь {action}."
        
        except Exception as e:
            log.error(f"Error toggling user status: {e}")
            return False, "Произошла ошибка при изменении статуса."
    
    async def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Delete user from database and 3x-ui.
        
        Returns:
            Tuple of (success, message)
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False, "Пользователь не найден."
        
        try:
            # Delete from 3x-ui
            async with XUIClient() as xui:
                await xui.delete_client(user.uuid)
            
            # Delete from database
            await self.user_repo.delete_user(user_id)
            
            log.info(f"User deleted: user_id={user_id}")
            return True, "Пользователь удален."
        
        except Exception as e:
            log.error(f"Error deleting user: {e}")
            return False, "Произошла ошибка при удалении."

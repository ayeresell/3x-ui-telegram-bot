"""SQLAlchemy models for the VPN bot database."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class User(Base):
    """User model for VPN clients."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    inbound_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ID инбаунда, к которому подключен
    protocol: Mapped[str] = mapped_column(String(50), default="VLESS", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    traffic_limit_gb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationship
    access_requests: Mapped[list["AccessRequest"]] = relationship(
        "AccessRequest", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, tg_id={self.tg_id}, email={self.email}, is_approved={self.is_approved})>"


class AccessRequest(Base):
    """Access request model for tracking user approval workflow."""
    
    __tablename__ = "access_requests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, approved, rejected
    admin_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="access_requests")
    
    def __repr__(self) -> str:
        return f"<AccessRequest(id={self.id}, user_id={self.user_id}, status={self.status})>"


class ActiveInbound(Base):
    """Model for storing active inbounds selected by admin."""
    
    __tablename__ = "active_inbounds"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inbound_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    remark: Mapped[str] = mapped_column(String(255), nullable=False)  # Название инбаунда
    protocol: Mapped[str] = mapped_column(String(50), nullable=False)  # VLESS, VMess, etc.
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Включен ли для выбора
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<ActiveInbound(id={self.id}, inbound_id={self.inbound_id}, remark={self.remark})>"

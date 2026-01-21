"""Data formatting utilities."""

from datetime import datetime


def format_traffic_gb(bytes_value: int) -> str:
    """
    Convert bytes to gigabytes with 2 decimal places.
    
    Args:
        bytes_value: Traffic in bytes
    
    Returns:
        Formatted string like "1.23 ГБ"
    """
    gb = bytes_value / (1024 ** 3)
    return f"{gb:.2f} ГБ"


def format_traffic_mb(bytes_value: int) -> str:
    """
    Convert bytes to megabytes with 2 decimal places.
    
    Args:
        bytes_value: Traffic in bytes
    
    Returns:
        Formatted string like "123.45 МБ"
    """
    mb = bytes_value / (1024 ** 2)
    return f"{mb:.2f} МБ"


def format_datetime(dt: datetime) -> str:
    """
    Format datetime to readable string.
    
    Args:
        dt: Datetime object
    
    Returns:
        Formatted string like "21.01.2026 15:30"
    """
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date(dt: datetime) -> str:
    """
    Format datetime to date string.
    
    Args:
        dt: Datetime object
    
    Returns:
        Formatted string like "21.01.2026"
    """
    return dt.strftime("%d.%m.%Y")


def format_status(is_active: bool) -> str:
    """
    Format active status to emoji and text.
    
    Args:
        is_active: Boolean status
    
    Returns:
        Formatted string with emoji
    """
    return "✅ Активен" if is_active else "❌ Деактивирован"


def format_approval_status(is_approved: bool) -> str:
    """
    Format approval status to emoji and text.
    
    Args:
        is_approved: Boolean approval status
    
    Returns:
        Formatted string with emoji
    """
    return "✅ Одобрен" if is_approved else "⏳ Ожидает одобрения"

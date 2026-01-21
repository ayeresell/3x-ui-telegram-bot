"""QR code and VLESS link generation utilities."""

from io import BytesIO
from urllib.parse import urlencode
from typing import Optional
import qrcode

from core.config import settings
from core.logger import log


def generate_vless_link(
    uuid: str, 
    email: str, 
    server: Optional[str] = None,
    port: Optional[int] = None,
    sni: Optional[str] = None
) -> str:
    """
    Generate VLESS connection link.
    
    Args:
        uuid: Client UUID
        email: Client email (used as remark)
        server: Server address (defaults to settings)
        port: Server port (defaults to settings)
        sni: SNI (defaults to settings)
    
    Returns:
        VLESS connection string
    """
    # Use provided values or defaults from settings
    server = server or settings.VLESS_SERVER
    port = port or settings.VLESS_PORT
    sni = sni or settings.VLESS_SNI
    
    # Build query parameters
    params = {
        "type": settings.VLESS_TYPE,
        "security": settings.VLESS_SECURITY,
        "sni": sni
    }
    
    # Build VLESS link
    # Format: vless://uuid@server:port?params#remark
    link = f"vless://{uuid}@{server}:{port}?{urlencode(params)}#{email}"
    
    log.info(f"Generated VLESS link for {email}")
    return link


def generate_qr_code(data: str) -> BytesIO:
    """
    Generate QR code image from data string.
    
    Args:
        data: String data to encode (e.g., VLESS link)
    
    Returns:
        BytesIO object containing PNG image
    """
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to BytesIO
    bio = BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    
    log.info("Generated QR code")
    return bio


def generate_vless_qr(
    uuid: str, 
    email: str,
    server: Optional[str] = None,
    port: Optional[int] = None,
    sni: Optional[str] = None
) -> tuple[str, BytesIO]:
    """
    Generate both VLESS link and QR code.
    
    Args:
        uuid: Client UUID
        email: Client email
        server: Server address (optional)
        port: Server port (optional)
        sni: SNI (optional)
    
    Returns:
        Tuple of (vless_link, qr_code_image)
    """
    link = generate_vless_link(uuid, email, server, port, sni)
    qr_image = generate_qr_code(link)
    return link, qr_image

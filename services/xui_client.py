"""3x-ui API client for VPN management."""

import json
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from core.config import settings
from core.logger import log


class XUIClientError(Exception):
    """Custom exception for XUI client errors."""
    pass


class XUIClient:
    """HTTP client for 3x-ui panel API."""
    
    def __init__(self):
        self.base_url = settings.XUI_BASE_URL.rstrip('/')
        self.username = settings.XUI_USERNAME
        self.password = settings.XUI_PASSWORD
        self.session_cookie: Optional[str] = None
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
            follow_redirects=True,
            verify=settings.XUI_VERIFY_SSL  # Проверка SSL (по умолчанию False для самоподписанных сертификатов)
        )
        await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        retry_on_auth_error: bool = True
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling and retry logic."""
        if not self.client:
            raise XUIClientError("Client not initialized. Use async context manager.")
        
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie
        
        try:
            start_time = datetime.now()
            
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await self.client.post(url, json=data, headers=headers)
            else:
                raise XUIClientError(f"Unsupported HTTP method: {method}")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            log.info(f"XUI API {method} {endpoint} - Status: {response.status_code} - Time: {elapsed:.2f}s")
            
            # Handle authentication errors
            if response.status_code == 401 and retry_on_auth_error:
                log.warning("Session expired, re-authenticating...")
                await self.login()
                return await self._make_request(method, endpoint, data, retry_on_auth_error=False)
            
            # Handle other errors
            if response.status_code >= 400:
                log.error(f"XUI API error: {response.status_code} - {response.text}")
                raise XUIClientError(f"API request failed with status {response.status_code}")
            
            return response.json()
        
        except httpx.RequestError as e:
            log.error(f"Network error during XUI API request: {e}")
            raise XUIClientError(f"Network error: {e}")
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON response: {e}")
            raise XUIClientError(f"Invalid JSON response: {e}")
    
    async def login(self) -> bool:
        """Authenticate and get session cookie."""
        login_url = f"{self.base_url}/login"
        
        try:
            log.info(f"Authenticating with 3x-ui panel...")
            log.info(f"Base URL: {self.base_url}")
            log.info(f"Login URL: {login_url}")
            log.info(f"Username: {self.username}")
            
            # Try login with form data
            response = await self.client.post(
                login_url,
                data={
                    "username": self.username,
                    "password": self.password
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            log.info(f"Login response status: {response.status_code}")
            log.info(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                # Extract session cookie
                cookies = response.cookies
                log.info(f"Cookies received: {list(cookies.keys())}")
                
                if cookies:
                    cookie_parts = []
                    for name, value in cookies.items():
                        cookie_parts.append(f"{name}={value}")
                    self.session_cookie = "; ".join(cookie_parts)
                    log.info("Successfully authenticated with 3x-ui panel")
                    return True
                else:
                    log.error("No cookies received from 3x-ui panel")
                    log.error(f"Response body: {response.text[:500]}")
                    raise XUIClientError("No session cookie received")
            
            log.error(f"Authentication failed with status {response.status_code}")
            log.error(f"Response body: {response.text[:500]}")
            raise XUIClientError(f"Authentication failed with status {response.status_code}")
        
        except httpx.ConnectError as e:
            log.error(f"Connection error during login: {e}")
            log.error(f"Failed to connect to: {login_url}")
            raise XUIClientError(f"Connection failed: Cannot connect to {login_url}")
        except httpx.TimeoutException as e:
            log.error(f"Timeout error during login: {e}")
            raise XUIClientError(f"Connection timeout to {login_url}")
        except httpx.RequestError as e:
            log.error(f"Network error during login: {type(e).__name__} - {e}")
            raise XUIClientError(f"Login failed: {type(e).__name__} - {e}")
        except Exception as e:
            log.error(f"Login error: {type(e).__name__} - {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            raise XUIClientError(f"Login failed: {type(e).__name__} - {e}")
    
    async def get_inbound(self, inbound_id: int) -> Dict[str, Any]:
        """Get inbound configuration by ID."""
        log.info(f"Getting inbound configuration: id={inbound_id}")
        result = await self._make_request("GET", f"/panel/api/inbounds/get/{inbound_id}")
        return result
    
    async def create_client(
        self,
        email: str,
        uuid: str,
        inbound_id: int,
        enable: bool = True
    ) -> bool:
        """Create a new client in the inbound."""
        log.info(f"Creating client: email={email}, uuid={uuid}, inbound_id={inbound_id}")
        
        # Check if client exists in any inbound
        existing_client = await self.find_client_in_all_inbounds(email)
        if existing_client:
            inbound_remark = existing_client['inbound_remark']
            log.warning(f"Client {email} already exists in inbound '{inbound_remark}'")
            raise XUIClientError(f"Клиент с таким именем уже существует в инбаунде '{inbound_remark}'. Попросите пользователя выбрать другое имя.")
        
        # Prepare request data with complete client info as per 3x-ui API spec
        request_data = {
            "id": inbound_id,
            "settings": json.dumps({
                "clients": [
                    {
                        "id": uuid,
                        "email": email,
                        "enable": enable,
                        "flow": "",
                        "limitIp": 0,
                        "totalGB": 0,
                        "expiryTime": 0,
                        "tgId": "",
                        "subId": "",
                        "reset": 0
                    }
                ]
            })
        }
        
        log.info(f"Sending addClient request: inbound_id={inbound_id}, email={email}, uuid={uuid}")
        log.debug(f"Request data: {request_data}")
        
        # Add client via API
        result = await self._make_request("POST", "/panel/api/inbounds/addClient", request_data)
        
        if result.get("success"):
            log.info(f"Successfully created client: {email}")
            return True
        else:
            error_msg = result.get('msg', 'Unknown error')
            log.error(f"Failed to create client with email '{email}': {result}")
            
            # Parse duplicate email error
            if "Duplicate email" in error_msg:
                # Extract the duplicate email from error message
                import re
                match = re.search(r'Duplicate email: (.+)', error_msg)
                if match:
                    duplicate_email = match.group(1).strip()
                    log.error(f"Duplicate email detected: '{duplicate_email}' (we tried to create: '{email}')")
                    raise XUIClientError(f"В 3x-ui уже существует клиент с email '{duplicate_email}'. Удалите его через панель 3x-ui.")
            
            raise XUIClientError(f"Failed to create client: {error_msg}")
    
    async def get_client_traffic(self, email: str) -> Dict[str, int]:
        """Get client traffic statistics by email."""
        log.info(f"Getting traffic stats for client: {email}")
        
        result = await self._make_request("GET", f"/panel/api/inbounds/getClientTraffics/{email}")
        
        if result.get("success") and result.get("obj"):
            obj = result["obj"]
            traffic = {
                "up": obj.get("up", 0),
                "down": obj.get("down", 0),
                "total": obj.get("up", 0) + obj.get("down", 0)
            }
            log.info(f"Traffic for {email}: {traffic}")
            return traffic
        
        log.warning(f"No traffic data found for {email}")
        return {"up": 0, "down": 0, "total": 0}
    
    async def update_client_status(
        self,
        email: str,
        uuid: str,
        inbound_id: int,
        enable: bool
    ) -> bool:
        """Update client enable/disable status."""
        log.info(f"Updating client status: email={email}, enable={enable}")
        
        # Get current inbound configuration
        inbound_data = await self.get_inbound(inbound_id)
        
        if not inbound_data.get("success"):
            raise XUIClientError("Failed to get inbound configuration")
        
        obj = inbound_data.get("obj")
        settings_str = obj.get("settings", "{}")
        settings_dict = json.loads(settings_str)
        
        # Find and update client
        clients = settings_dict.get("clients", [])
        client_found = False
        
        for client in clients:
            if client.get("email") == email or client.get("id") == uuid:
                client["enable"] = enable
                client_found = True
                break
        
        if not client_found:
            raise XUIClientError(f"Client not found: {email}")
        
        # Update via API
        request_data = {
            "id": uuid,
            "inboundId": inbound_id,
            "enable": enable
        }
        
        result = await self._make_request("POST", f"/panel/api/inbounds/updateClient/{uuid}", request_data)
        
        if result.get("success"):
            log.info(f"Successfully updated client status: {email}")
            return True
        else:
            log.error(f"Failed to update client: {result}")
            raise XUIClientError(f"Failed to update client: {result.get('msg', 'Unknown error')}")
    
    async def delete_client(
        self,
        uuid: str,
        inbound_id: int
    ) -> bool:
        """Delete client from inbound."""
        log.info(f"Deleting client: uuid={uuid}, inbound_id={inbound_id}")
        
        result = await self._make_request(
            "POST",
            f"/panel/api/inbounds/{inbound_id}/delClient/{uuid}",
            {}
        )
        
        if result.get("success"):
            log.info(f"Successfully deleted client: {uuid}")
            return True
        else:
            log.error(f"Failed to delete client: {result}")
            raise XUIClientError(f"Failed to delete client: {result.get('msg', 'Unknown error')}")
    
    async def get_inbound_list(self) -> list:
        """Get list of all inbounds."""
        log.info("Getting inbound list")
        result = await self._make_request("GET", "/panel/api/inbounds/list")
        
        if result.get("success"):
            return result.get("obj", [])
        
        return []
    
    async def find_client_in_all_inbounds(self, email: str) -> Optional[Dict[str, Any]]:
        """Find client by email in all inbounds."""
        log.info(f"Searching for client with email: {email}")
        
        inbounds = await self.get_inbound_list()
        
        for inbound in inbounds:
            inbound_id = inbound.get("id")
            settings_str = inbound.get("settings", "{}")
            
            try:
                settings_dict = json.loads(settings_str)
                clients = settings_dict.get("clients", [])
                
                for client in clients:
                    if client.get("email") == email:
                        log.info(f"Found client {email} in inbound {inbound_id}")
                        return {
                            "inbound_id": inbound_id,
                            "inbound_remark": inbound.get("remark", "Unknown"),
                            "client": client
                        }
            except json.JSONDecodeError:
                continue
        
        log.info(f"Client {email} not found in any inbound")
        return None
    
    async def delete_client_from_all_inbounds(self, email: str) -> bool:
        """Delete client by email from all inbounds where it exists."""
        log.info(f"Attempting to delete client {email} from all inbounds")
        
        client_info = await self.find_client_in_all_inbounds(email)
        
        if not client_info:
            log.warning(f"Client {email} not found in any inbound")
            return False
        
        inbound_id = client_info["inbound_id"]
        uuid = client_info["client"].get("id")
        
        try:
            await self.delete_client(uuid, inbound_id)
            log.info(f"Successfully deleted client {email} from inbound {inbound_id}")
            return True
        except Exception as e:
            log.error(f"Failed to delete client {email}: {e}")
            return False
    
    async def get_client_link(self, inbound_id: int, email: str) -> Optional[str]:
        """
        Get client connection link from 3x-ui.
        
        Args:
            inbound_id: Inbound ID
            email: Client email
        
        Returns:
            Connection link (vless://, vmess://, etc.) or None if not found
        """
        log.info(f"Getting client link: inbound_id={inbound_id}, email={email}")
        
        try:
            # Get inbound configuration
            inbound_data = await self.get_inbound(inbound_id)
            
            if not inbound_data.get("success"):
                log.error("Failed to get inbound configuration")
                return None
            
            obj = inbound_data.get("obj")
            if not obj:
                log.error("No inbound object in response")
                return None
            
            # Parse settings to find client
            settings_str = obj.get("settings", "{}")
            settings_dict = json.loads(settings_str)
            clients = settings_dict.get("clients", [])
            
            # Find client by email
            target_client = None
            for client in clients:
                if client.get("email") == email:
                    target_client = client
                    break
            
            if not target_client:
                log.error(f"Client not found: {email}")
                return None
            
            # Generate link based on protocol and settings
            protocol = obj.get("protocol", "").lower()
            port = obj.get("port")
            
            # Get stream settings
            stream_settings_str = obj.get("streamSettings", "{}")
            stream_settings = json.loads(stream_settings_str) if isinstance(stream_settings_str, str) else stream_settings_str
            
            # Get network type and security
            network = stream_settings.get("network", "tcp")
            security = stream_settings.get("security", "none")
            
            # Build link based on protocol
            if protocol == "vless":
                link = await self._build_vless_link(
                    target_client,
                    obj,
                    stream_settings,
                    port,
                    network,
                    security
                )
            elif protocol == "vmess":
                link = await self._build_vmess_link(
                    target_client,
                    obj,
                    stream_settings,
                    port,
                    network,
                    security
                )
            elif protocol == "trojan":
                link = await self._build_trojan_link(
                    target_client,
                    obj,
                    stream_settings,
                    port,
                    network,
                    security
                )
            else:
                log.warning(f"Unsupported protocol: {protocol}")
                return None
            
            log.info(f"Successfully generated link for {email}")
            return link
        
        except Exception as e:
            log.error(f"Error getting client link: {e}")
            return None
    
    async def _build_vless_link(
        self,
        client: dict,
        inbound: dict,
        stream_settings: dict,
        port: int,
        network: str,
        security: str
    ) -> str:
        """Build VLESS connection link."""
        from urllib.parse import urlencode, quote
        
        uuid = client.get("id")
        email = client.get("email", "")
        flow = client.get("flow", "")
        
        # Get server address (use remark or listen address)
        server = inbound.get("listen", "0.0.0.0")
        if server == "0.0.0.0" or server == "":
            # Use external address from settings or base URL
            server = self.base_url.replace("https://", "").replace("http://", "").split(":")[0]
        
        # Build query parameters
        params = {
            "type": network,
            "encryption": "none"
        }
        
        # Add security parameters
        if security == "tls":
            params["security"] = "tls"
            tls_settings = stream_settings.get("tlsSettings", {})
            sni = tls_settings.get("serverName", "")
            if sni:
                params["sni"] = sni
            alpn = tls_settings.get("alpn", [])
            if alpn:
                params["alpn"] = ",".join(alpn)
        
        elif security == "reality":
            params["security"] = "reality"
            reality_settings = stream_settings.get("realitySettings", {})
            
            # Public key
            pbk = reality_settings.get("publicKey", "")
            if pbk:
                params["pbk"] = pbk
            
            # Fingerprint
            fp = reality_settings.get("fingerprint", "")
            if fp:
                params["fp"] = fp
            
            # SNI
            server_names = reality_settings.get("serverNames", [])
            if server_names:
                params["sni"] = server_names[0]
            
            # Short IDs
            short_ids = reality_settings.get("shortIds", [])
            if short_ids:
                params["sid"] = short_ids[0]
            
            # Spider X
            spider_x = reality_settings.get("spiderX", "")
            if spider_x:
                params["spx"] = quote(spider_x)
        
        # Add flow if present
        if flow:
            params["flow"] = flow
        
        # Add network-specific parameters
        if network == "ws":
            ws_settings = stream_settings.get("wsSettings", {})
            path = ws_settings.get("path", "/")
            params["path"] = quote(path)
            headers = ws_settings.get("headers", {})
            host = headers.get("Host", "")
            if host:
                params["host"] = host
        
        elif network == "grpc":
            grpc_settings = stream_settings.get("grpcSettings", {})
            service_name = grpc_settings.get("serviceName", "")
            if service_name:
                params["serviceName"] = service_name
        
        elif network == "tcp":
            tcp_settings = stream_settings.get("tcpSettings", {})
            header = tcp_settings.get("header", {})
            header_type = header.get("type", "none")
            if header_type != "none":
                params["headerType"] = header_type
        
        # Build link
        query_string = urlencode(params, safe="/:,")
        link = f"vless://{uuid}@{server}:{port}?{query_string}#{quote(email)}"
        
        return link
    
    async def _build_vmess_link(
        self,
        client: dict,
        inbound: dict,
        stream_settings: dict,
        port: int,
        network: str,
        security: str
    ) -> str:
        """Build VMess connection link."""
        import base64
        
        uuid = client.get("id")
        email = client.get("email", "")
        
        # Get server address
        server = inbound.get("listen", "0.0.0.0")
        if server == "0.0.0.0" or server == "":
            server = self.base_url.replace("https://", "").replace("http://", "").split(":")[0]
        
        # Build VMess config
        vmess_config = {
            "v": "2",
            "ps": email,
            "add": server,
            "port": str(port),
            "id": uuid,
            "aid": "0",
            "net": network,
            "type": "none",
            "host": "",
            "path": "",
            "tls": security if security == "tls" else ""
        }
        
        # Add network-specific settings
        if network == "ws":
            ws_settings = stream_settings.get("wsSettings", {})
            vmess_config["path"] = ws_settings.get("path", "/")
            headers = ws_settings.get("headers", {})
            vmess_config["host"] = headers.get("Host", "")
        
        # Encode to base64
        vmess_json = json.dumps(vmess_config)
        vmess_base64 = base64.b64encode(vmess_json.encode()).decode()
        
        return f"vmess://{vmess_base64}"
    
    async def _build_trojan_link(
        self,
        client: dict,
        inbound: dict,
        stream_settings: dict,
        port: int,
        network: str,
        security: str
    ) -> str:
        """Build Trojan connection link."""
        from urllib.parse import urlencode, quote
        
        password = client.get("password", "")
        email = client.get("email", "")
        
        # Get server address
        server = inbound.get("listen", "0.0.0.0")
        if server == "0.0.0.0" or server == "":
            server = self.base_url.replace("https://", "").replace("http://", "").split(":")[0]
        
        # Build query parameters
        params = {
            "type": network,
            "security": security
        }
        
        if security == "tls":
            tls_settings = stream_settings.get("tlsSettings", {})
            sni = tls_settings.get("serverName", "")
            if sni:
                params["sni"] = sni
        
        # Build link
        query_string = urlencode(params)
        link = f"trojan://{password}@{server}:{port}?{query_string}#{quote(email)}"
        
        return link

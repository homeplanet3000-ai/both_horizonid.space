import asyncio
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger
from config import (
    MARZBAN_PASSWORD,
    MARZBAN_RETRY_BACKOFF_SECONDS,
    MARZBAN_RETRY_COUNT,
    MARZBAN_TIMEOUT_SECONDS,
    MARZBAN_URL,
    MARZBAN_USERNAME,
    PREFER_MOBILE_VLESS_WS,
    SUBSCRIPTION_DOMAIN,
    VLESS_FLOW,
)
from services.http import get_session

class MarzbanAPI:
    def __init__(self) -> None:
        self.base_url = MARZBAN_URL
        self.tokens: Dict[str, str] = {}

    async def get_token(self, base_url: Optional[str] = None) -> Optional[str]:
        """Получение токена администратора"""
        url = f"{base_url or self.base_url}/api/admin/token"
        data = {"username": MARZBAN_USERNAME, "password": MARZBAN_PASSWORD}
        timeout = aiohttp.ClientTimeout(total=MARZBAN_TIMEOUT_SECONDS)

        for attempt in range(MARZBAN_RETRY_COUNT + 1):
            try:
                session = await get_session()
                async with session.post(url, data=data, timeout=timeout) as resp:
                    if resp.status == 200:
                        json_resp = await resp.json()
                        token = json_resp.get("access_token")
                        self.tokens[base_url or self.base_url] = token
                        return token
                    logger.error("Marzban Auth Failed: %s", resp.status)
                    return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning("Marzban Auth Error (attempt %s/%s): %s", attempt + 1, MARZBAN_RETRY_COUNT + 1, e)
                if attempt < MARZBAN_RETRY_COUNT:
                    await asyncio.sleep(MARZBAN_RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                return None
        return None

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        base_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Внутренний метод для запросов с авто-обновлением токена"""
        base = base_url or self.base_url
        token = self.tokens.get(base)
        if not token:
            token = await self.get_token(base)
        if not token:
            logger.error("Marzban token is missing; request aborted for %s %s", method, endpoint)
            return None

        url = f"{base}/api/{endpoint}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        timeout = aiohttp.ClientTimeout(total=MARZBAN_TIMEOUT_SECONDS)

        for attempt in range(MARZBAN_RETRY_COUNT + 1):
            try:
                session = await get_session()
                async with session.request(method, url, json=json, headers=headers, timeout=timeout) as resp:
                    if resp.status == 401:  # Токен протух
                        token = await self.get_token(base)
                        if not token:
                            logger.error("Marzban token refresh failed for %s", base)
                            return None
                        headers["Authorization"] = f"Bearer {token}"
                        async with session.request(method, url, json=json, headers=headers, timeout=timeout) as resp_retry:
                            return await self._handle_response(resp_retry)
                    if resp.status >= 500 and attempt < MARZBAN_RETRY_COUNT:
                        logger.warning("Marzban server error %s; retrying", resp.status)
                        await asyncio.sleep(MARZBAN_RETRY_BACKOFF_SECONDS * (attempt + 1))
                        continue
                    return await self._handle_response(resp)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning("Marzban request failed (attempt %s/%s): %s", attempt + 1, MARZBAN_RETRY_COUNT + 1, e)
                if attempt < MARZBAN_RETRY_COUNT:
                    await asyncio.sleep(MARZBAN_RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                return None
        return None

    async def _handle_response(self, resp: aiohttp.ClientResponse) -> Optional[Dict[str, Any]]:
        if resp.status in [200, 201]:
            return await resp.json()
        elif resp.status == 409: # Пользователь уже существует
            return {"status": "conflict"}
        else:
            logger.error(f"API Error {resp.status}: {await resp.text()}")
            return None

    async def create_or_update_user(
        self,
        user_id: int,
        data_limit_bytes: int = 0,
        base_url: Optional[str] = None,
    ) -> Optional[str]:
        """Создает или обновляет пользователя. data_limit=0 это безлимит."""
        user_info = await self.ensure_user(user_id, data_limit_bytes=data_limit_bytes, base_url=base_url)
        return self._extract_link(user_info)

    async def ensure_user(
        self,
        user_id: int,
        data_limit_bytes: int = 0,
        base_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Создает или обновляет пользователя и возвращает актуальные данные."""
        username = f"user_{user_id}"
        proxy_settings = {"flow": VLESS_FLOW} if VLESS_FLOW else None

        payload = {
            "username": username,
            "inbounds": {"vless": ["VLESS_REALITY"]},
            "data_limit": data_limit_bytes,
            "status": "active",
        }
        if proxy_settings:
            payload["proxies"] = {"vless": proxy_settings}

        res = await self._request("POST", "user", json=payload, base_url=base_url)

        if res and res.get("status") == "conflict":
            update_payload = {"data_limit": data_limit_bytes, "status": "active"}
            if proxy_settings:
                update_payload["proxies"] = {"vless": proxy_settings}
            if data_limit_bytes == 0:
                update_payload["used_traffic"] = 0

            await self._request("PUT", f"user/{username}", json=update_payload, base_url=base_url)
            res = await self.get_user_info(username, base_url=base_url)

        return res

    async def get_user_info(self, username: str, base_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return await self._request("GET", f"user/{username}", base_url=base_url)

    def extract_link(self, user_info: Optional[Dict[str, Any]]) -> Optional[str]:
        return self._extract_link(user_info)

    def _extract_link(self, user_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """Вытаскивает VLESS ссылку и меняет IP на домен"""
        if not user_data or "links" not in user_data:
            return None
        
        links = user_data.get("links", [])
        target_link = None
        normalized_links = [(link, link.lower()) for link in links]

        if PREFER_MOBILE_VLESS_WS:
            for link, lower in normalized_links:
                if "vless://" not in lower:
                    continue
                if "type=ws" in lower or "type%3dws" in lower:
                    if "path=" in lower or "path%3d" in lower:
                        if "host=" in lower or "host%3d" in lower:
                            if "flow=" not in lower and "flow%3d" not in lower:
                                target_link = link
                                break

        # Ищем приоритетную ссылку с Flow
        if not target_link:
            for link in links:
                if not VLESS_FLOW:
                    break
                if f"flow={VLESS_FLOW}" in link or f"flow%3D{VLESS_FLOW}" in link:
                    target_link = link
                    break

        # Ищем VLESS Reality
        if not target_link:
            for link in links:
                if "VLESS_REALITY" in link or "REALITY" in link or "reality" in link:
                    target_link = link
                    break

        # Ищем приоритетную ссылку (WS CDN)
        if not target_link:
            for link in links:
                if "VLESS_WS_CDN" in link:
                    target_link = link
                    break
        
        if not target_link and links:
            target_link = links[0]

        if target_link and SUBSCRIPTION_DOMAIN:
            # Заменяем старые IP на домен из конфига
            target_link = target_link.replace("144.31.255.97", SUBSCRIPTION_DOMAIN)
            target_link = target_link.replace("64.188.97.154", SUBSCRIPTION_DOMAIN)
            
        return target_link

# Экземпляр для импорта
marzban_api = MarzbanAPI()

import aiohttp
from loguru import logger
from config import MARZBAN_URL, MARZBAN_USERNAME, MARZBAN_PASSWORD, SUBSCRIPTION_DOMAIN

class MarzbanAPI:
    def __init__(self):
        self.base_url = MARZBAN_URL
        self.token = None

    async def get_token(self):
        """Получение токена администратора"""
        url = f"{self.base_url}/api/admin/token"
        data = {"username": MARZBAN_USERNAME, "password": MARZBAN_PASSWORD}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as resp:
                    if resp.status == 200:
                        json_resp = await resp.json()
                        self.token = json_resp.get("access_token")
                        return self.token
                    else:
                        logger.error(f"Marzban Auth Failed: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Marzban Connection Error: {e}")
            return None

    async def _request(self, method, endpoint, json=None):
        """Внутренний метод для запросов с авто-обновлением токена"""
        if not self.token:
            await self.get_token()

        url = f"{self.base_url}/api/{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=json, headers=headers) as resp:
                if resp.status == 401: # Токен протух
                    await self.get_token()
                    headers["Authorization"] = f"Bearer {self.token}"
                    async with session.request(method, url, json=json, headers=headers) as resp_retry:
                        return await self._handle_response(resp_retry)
                return await self._handle_response(resp)

    async def _handle_response(self, resp):
        if resp.status in [200, 201]:
            return await resp.json()
        elif resp.status == 409: # Пользователь уже существует
            return {"status": "conflict"}
        else:
            logger.error(f"API Error {resp.status}: {await resp.text()}")
            return None

    async def create_or_update_user(self, user_id: int, data_limit_bytes: int = 0):
        """Создает или обновляет пользователя. data_limit=0 это безлимит."""
        username = f"user_{user_id}"
        
        # Данные для создания
        payload = {
            "username": username,
            "proxies": {"vless": {}},
            "inbounds": {"vless": ["VLESS_REALITY"]},
            "data_limit": data_limit_bytes,
            "status": "active"
        }

        # 1. Пробуем создать
        res = await self._request("POST", "user", json=payload)
        
        # 2. Если уже есть (conflict), обновляем лимиты
        if res and res.get("status") == "conflict":
            # Сбрасываем потребление при обновлении
            update_payload = {"data_limit": data_limit_bytes, "status": "active"}
            if data_limit_bytes == 0: 
                 update_payload["used_traffic"] = 0
            
            await self._request("PUT", f"user/{username}", json=update_payload)
            # Запрашиваем актуальные данные для получения ссылок
            res = await self.get_user_info(username)

        return self._extract_link(res)

    async def get_user_info(self, username):
        return await self._request("GET", f"user/{username}")

    def _extract_link(self, user_data):
        """Вытаскивает VLESS ссылку и меняет IP на домен"""
        if not user_data or "links" not in user_data:
            return None
        
        links = user_data.get("links", [])
        target_link = None
        
        # Ищем приоритетную ссылку (WS CDN)
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

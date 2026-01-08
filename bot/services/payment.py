import asyncio
import hashlib
from urllib.parse import urlencode

import aiohttp
from loguru import logger
from config import (
    AAIO_API_KEY,
    AAIO_MERCHANT_ID,
    AAIO_SECRET_1,
    PAYMENT_RETRY_BACKOFF_SECONDS,
    PAYMENT_RETRY_COUNT,
    PAYMENT_TIMEOUT_SECONDS,
)

class PaymentService:
    @staticmethod
    def generate_url(amount: float, order_id: str, email: str):
        currency = "RUB"
        desc = f"Order {order_id}"
        if not (AAIO_MERCHANT_ID and AAIO_SECRET_1):
            logger.error("AAIO credentials missing; cannot generate payment URL")
            return None
        if not email:
            logger.error("Payment email missing; cannot generate payment URL")
            return None

        # Формула SHA-256: merchant_id:amount:currency:secret_1:order_id
        sign_str = f"{AAIO_MERCHANT_ID}:{amount}:{currency}:{AAIO_SECRET_1}:{order_id}"
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()

        params = {
            "merchant_id": AAIO_MERCHANT_ID,
            "amount": amount,
            "currency": currency,
            "order_id": order_id,
            "sign": sign,
            "desc": desc,
            "email": email,
        }
        url = f"https://aaio.so/merchant/pay?{urlencode(params)}"
        return url

    @staticmethod
    async def check_status(order_id: str):
        """Проверяет статус заказа через API"""
        if not (AAIO_MERCHANT_ID and AAIO_API_KEY):
            logger.error("AAIO credentials missing; cannot check payment status")
            return False
        url = "https://aaio.so/api/info-pay"
        params = {
            'merchant_id': AAIO_MERCHANT_ID,
            'order_id': order_id
        }
        headers = {
            'Accept': 'application/json',
            'X-Api-Key': AAIO_API_KEY
        }
        timeout = aiohttp.ClientTimeout(total=PAYMENT_TIMEOUT_SECONDS)

        for attempt in range(PAYMENT_RETRY_COUNT + 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, data=params, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('type') == 'success' and data.get('status') == 'success':
                                return True
                            return False
                        logger.error("AAIO Check Error: %s", await resp.text())
                        if attempt < PAYMENT_RETRY_COUNT:
                            await asyncio.sleep(PAYMENT_RETRY_BACKOFF_SECONDS * (attempt + 1))
                            continue
                        return False
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error("AAIO Connection Error (attempt %s/%s): %s", attempt + 1, PAYMENT_RETRY_COUNT + 1, e)
                if attempt < PAYMENT_RETRY_COUNT:
                    await asyncio.sleep(PAYMENT_RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                return False
        return False

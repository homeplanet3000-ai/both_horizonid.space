import hashlib
import aiohttp
from loguru import logger
from config import AAIO_MERCHANT_ID, AAIO_SECRET_1, AAIO_API_KEY

class PaymentService:
    @staticmethod
    def generate_url(amount: float, order_id: str, email: str = "user@mail.com"):
        currency = "RUB"
        desc = f"Order {order_id}"
        
        # Формула SHA-256: merchant_id:amount:currency:secret_1:order_id
        sign_str = f"{AAIO_MERCHANT_ID}:{amount}:{currency}:{AAIO_SECRET_1}:{order_id}"
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()

        url = (
            f"https://aaio.so/merchant/pay?"
            f"merchant_id={AAIO_MERCHANT_ID}&"
            f"amount={amount}&"
            f"currency={currency}&"
            f"order_id={order_id}&"
            f"sign={sign}&"
            f"desc={desc}&"
            f"email={email}"
        )
        return url

    @staticmethod
    async def check_status(order_id: str):
        """Проверяет статус заказа через API"""
        url = "https://aaio.so/api/info-pay"
        params = {
            'merchant_id': AAIO_MERCHANT_ID,
            'order_id': order_id
        }
        headers = {
            'Accept': 'application/json',
            'X-Api-Key': AAIO_API_KEY
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('type') == 'success' and data.get('status') == 'success':
                            return True
                        return False
                    else:
                        logger.error(f"AAIO Check Error: {await resp.text()}")
                        return False
        except Exception as e:
            logger.error(f"AAIO Connection Error: {e}")
            return False

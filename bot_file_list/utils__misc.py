import qrcode
import io
from aiogram.types import BufferedInputFile

def generate_qr(text: str) -> BufferedInputFile:
    """
    Генерирует QR-код из текста и возвращает объект для отправки в Telegram.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Сохраняем в байтовый буфер (в память, не на диск)
    bio = io.BytesIO()
    img.save(bio)
    bio.seek(0)

    return BufferedInputFile(bio.read(), filename="qrcode.png")

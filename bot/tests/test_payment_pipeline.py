from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from database import db
from handlers import pay


class DummyMessage:
    def __init__(self, user_id: int = 456) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.answer = AsyncMock()
        self.delete = AsyncMock()
        self.bot = SimpleNamespace(send_message=AsyncMock())


class DummyCallback:
    def __init__(self, data: str, user_id: int, message: DummyMessage) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = message
        self.answer = AsyncMock()


@pytest.mark.asyncio
async def test_process_success_payment_generates_key_and_records(temp_db: str, monkeypatch) -> None:
    await db.init_db()
    user_id = 456
    order_id = "order-123"
    await db.add_user(user_id, "tester", "Test User")

    async with db.get_db() as conn:
        await conn.execute(
            "INSERT INTO payments (order_id, user_id, amount, months, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, user_id, 100.0, 1, "processing", 0),
        )
        await conn.commit()

    monkeypatch.setattr(pay.marzban_api, "create_or_update_user", AsyncMock(return_value="vless://test-key"))
    monkeypatch.setattr(pay, "get_server", lambda server_id: {"marzban_url": "http://example.com"})

    message = DummyMessage(user_id)

    await pay.process_success_payment(message, user_id, 1, 100.0, order_id, "AAIO", "default")

    async with db.get_db() as conn:
        cursor = await conn.execute("SELECT status FROM payments WHERE order_id = ?", (order_id,))
        status_row = await cursor.fetchone()
        cursor = await conn.execute("SELECT link FROM subscriptions WHERE user_id = ?", (user_id,))
        subscription_row = await cursor.fetchone()

    assert status_row[0] == "paid"
    assert subscription_row[0] == "vless://test-key"
    assert any("Оплата прошла успешно" in call.args[0] for call in message.answer.await_args_list)


@pytest.mark.asyncio
async def test_check_payment_triggers_success_flow(temp_db: str, monkeypatch) -> None:
    await db.init_db()
    user_id = 789
    order_id = "order-456"
    await db.add_user(user_id, "tester2", "Test User 2")

    async with db.get_db() as conn:
        await conn.execute(
            "INSERT INTO payments (order_id, user_id, amount, months, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, user_id, 200.0, 3, "pending", 0),
        )
        await conn.commit()

    message = DummyMessage(user_id)
    callback = DummyCallback(f"check_pay_{order_id}", user_id, message)

    monkeypatch.setattr(pay.PaymentService, "check_status", AsyncMock(return_value=True))
    process_mock = AsyncMock()
    monkeypatch.setattr(pay, "process_success_payment", process_mock)

    await pay.check_payment(callback)

    process_mock.assert_awaited_once()

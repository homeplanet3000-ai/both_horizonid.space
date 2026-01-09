from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from database import db
from handlers import pay, user


class DummyMessage:
    def __init__(self, user_id: int = 123, full_name: str = "Test User", username: str = "tester") -> None:
        self.from_user = SimpleNamespace(id=user_id, full_name=full_name, username=username)
        self.answer = AsyncMock()
        self.answer_photo = AsyncMock()
        self.delete = AsyncMock()
        self.bot = SimpleNamespace(send_message=AsyncMock())


@pytest.mark.asyncio
async def test_start_command_sends_welcome(temp_db: str) -> None:
    await db.init_db()
    message = DummyMessage()
    command = SimpleNamespace(args=None)

    await user.cmd_start(message, command)

    message.answer.assert_awaited()


@pytest.mark.asyncio
async def test_buy_command_opens_tariffs_menu(temp_db: str) -> None:
    await db.init_db()
    message = DummyMessage()

    await pay.show_tariffs(message)

    message.answer.assert_awaited()


@pytest.mark.asyncio
async def test_status_command_profile_without_subscription(temp_db: str) -> None:
    await db.init_db()
    message = DummyMessage()
    await db.add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)

    await user.show_profile(message)

    message.answer.assert_awaited()

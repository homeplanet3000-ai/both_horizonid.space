import json
import os
import random
from functools import lru_cache
from typing import Any, Dict, Tuple

from database import db

CONTENT_PATH = os.path.join(os.path.dirname(__file__), "..", "content", "messages.json")
WELCOME_VARIANTS = ("A", "B")


@lru_cache
def load_content() -> Dict[str, Any]:
    with open(CONTENT_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_message(key: str) -> str:
    content = load_content()
    message = content.get(key)
    if not isinstance(message, str):
        raise KeyError(f"Missing message template for key '{key}'")
    return message


async def get_welcome_message(user_id: int, full_name: str) -> Tuple[str, str]:
    variant = await db.get_user_welcome_variant(user_id)
    if variant not in WELCOME_VARIANTS:
        variant = random.choice(WELCOME_VARIANTS)
        await db.set_user_welcome_variant(user_id, variant)

    content = load_content()
    template = content["welcome"][variant]
    return template.format(full_name=full_name), variant

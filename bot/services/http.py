import asyncio
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

_session: Optional[aiohttp.ClientSession] = None
_lock = asyncio.Lock()


async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session and not _session.closed:
        return _session
    async with _lock:
        if _session and not _session.closed:
            return _session
        _session = aiohttp.ClientSession()
        return _session


async def close_session() -> None:
    global _session
    if _session and not _session.closed:
        await _session.close()
    _session = None

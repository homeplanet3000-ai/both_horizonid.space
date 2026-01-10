import asyncio
import logging
import time
from typing import Dict

from config import MONITOR_INTERVAL_SECONDS, MONITOR_TARGETS, MONITOR_TIMEOUT_SECONDS
from services.alerts import send_alert
from services.http import get_session

logger = logging.getLogger(__name__)

STATUS_UP = "up"
STATUS_DOWN = "down"

_status_cache: Dict[str, str] = {}


def _format_latency(latency_ms: float) -> str:
    return f"{latency_ms:.0f}ms"


def _format_status_message(target: dict, status: str, latency_ms: float | None = None) -> str:
    name = target.get("name", target.get("id", "unknown"))
    url = target.get("url", "")
    if status == STATUS_UP:
        latency_text = f" ({_format_latency(latency_ms)})" if latency_ms is not None else ""
        return f"✅ <b>{name}</b> доступен{latency_text}\n<code>{url}</code>"
    return f"🔴 <b>{name}</b> недоступен\n<code>{url}</code>"


async def _check_target(target: dict) -> tuple[str, float | None]:
    url = target.get("url")
    expected_statuses = target.get("expected_statuses", [200])
    timeout_seconds = float(target.get("timeout_seconds") or MONITOR_TIMEOUT_SECONDS)
    if not url:
        return STATUS_DOWN, None

    session = await get_session()
    start = time.perf_counter()
    try:
        async with session.get(url, timeout=timeout_seconds) as resp:
            latency_ms = (time.perf_counter() - start) * 1000
            if resp.status in expected_statuses:
                return STATUS_UP, latency_ms
            return STATUS_DOWN, latency_ms
    except Exception as exc:
        logger.warning("Monitor target failed (%s): %s", url, exc)
        return STATUS_DOWN, None


async def monitoring_loop(interval_seconds: int | None = None) -> None:
    if not MONITOR_TARGETS:
        logger.info("Monitoring targets not configured; skipping monitoring loop")
        return

    interval = interval_seconds or MONITOR_INTERVAL_SECONDS
    logger.info("Monitoring loop started with %s targets", len(MONITOR_TARGETS))

    while True:
        for target in MONITOR_TARGETS:
            target_id = target.get("id") or target.get("url")
            if not target_id:
                continue
            status, latency_ms = await _check_target(target)
            previous = _status_cache.get(target_id)
            _status_cache[target_id] = status
            if previous and previous != status:
                await send_alert(_format_status_message(target, status, latency_ms))
            elif previous is None:
                logger.info("Monitor target %s initialized as %s", target_id, status)
        await asyncio.sleep(interval)

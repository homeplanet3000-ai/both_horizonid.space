import asyncio
import logging
import time

import aiohttp

from config import (
    HEALTHCHECK_INTERVAL_SECONDS,
    HEALTHCHECK_LATENCY_DOWN_MS,
    HEALTHCHECK_LATENCY_WARN_MS,
    HEALTHCHECK_TIMEOUT_SECONDS,
    SERVERS,
)
from services.alerts import send_alert
from services.failover import update_dns

logger = logging.getLogger(__name__)

STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_DOWN = "down"

_server_status = {server["id"]: STATUS_OK for server in SERVERS}
_server_latency_ms = {server["id"]: None for server in SERVERS}
_active_server_id = None


def status_emoji(status: str) -> str:
    return {
        STATUS_OK: "🟢",
        STATUS_WARN: "🟡",
        STATUS_DOWN: "🔴",
    }.get(status, "🟡")


def get_servers():
    return [
        {
            **server,
            "status": _server_status.get(server["id"], STATUS_WARN),
            "latency_ms": _server_latency_ms.get(server["id"]),
        }
        for server in SERVERS
    ]


def get_server(server_id: str):
    for server in SERVERS:
        if server["id"] == server_id:
            return {**server, "status": _server_status.get(server_id, STATUS_WARN)}
    return None


def get_active_server():
    servers = get_servers()
    for server in servers:
        if server["status"] == STATUS_OK:
            return server
    return servers[0] if servers else None


async def _check_server(session: aiohttp.ClientSession, server: dict):
    url = server.get("health_check_url") or server.get("marzban_url")
    if not url:
        return STATUS_WARN
    try:
        timeout_seconds = float(server.get("health_check_timeout") or HEALTHCHECK_TIMEOUT_SECONDS)
        warn_ms = int(server.get("latency_warn_ms") or HEALTHCHECK_LATENCY_WARN_MS)
        down_ms = int(server.get("latency_down_ms") or HEALTHCHECK_LATENCY_DOWN_MS)
        start = time.monotonic()
        async with session.get(url, timeout=timeout_seconds) as resp:
            latency_ms = int((time.monotonic() - start) * 1000)
            _server_latency_ms[server["id"]] = latency_ms
            if resp.status != 200:
                return STATUS_DOWN
            if latency_ms >= down_ms:
                return STATUS_DOWN
            if latency_ms >= warn_ms:
                return STATUS_WARN
            return STATUS_OK
    except Exception as e:
        logger.warning("Health check failed for %s: %s", server.get("id"), e)
        _server_latency_ms[server["id"]] = None
        return STATUS_DOWN


async def health_check_loop(interval_seconds: int = HEALTHCHECK_INTERVAL_SECONDS):
    while True:
        async with aiohttp.ClientSession() as session:
            tasks = [asyncio.create_task(_check_server(session, server)) for server in SERVERS]
            results = await asyncio.gather(*tasks)
            for server, status in zip(SERVERS, results):
                previous = _server_status.get(server["id"])
                _server_status[server["id"]] = status
                if previous and previous != status:
                    latency_ms = _server_latency_ms.get(server["id"])
                    latency_note = f" ({latency_ms} ms)" if latency_ms is not None else ""
                    await send_alert(f"⚡ Сервер <b>{server['id']}</b> сменил статус: {status}{latency_note}")
        active_server = get_active_server()
        if active_server:
            global _active_server_id
            if _active_server_id != active_server["id"]:
                update_success = await update_dns(active_server.get("public_ip"))
                if update_success:
                    _active_server_id = active_server["id"]
                    await send_alert(f"🔁 Активный сервер: <b>{active_server['id']}</b>")
                else:
                    await send_alert(
                        f"⚠️ Не удалось переключить DNS на <b>{active_server['id']}</b>. "
                        "Проверьте Cloudflare."
                    )
        await asyncio.sleep(interval_seconds)

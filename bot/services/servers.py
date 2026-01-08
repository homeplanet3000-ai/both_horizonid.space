import asyncio
import logging

import aiohttp

from config import SERVERS
from services.alerts import send_alert
from services.failover import update_dns

logger = logging.getLogger(__name__)

STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_DOWN = "down"

_server_status = {server["id"]: STATUS_OK for server in SERVERS}
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
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                return STATUS_OK
            return STATUS_WARN
    except Exception as e:
        logger.warning("Health check failed for %s: %s", server.get("id"), e)
        return STATUS_DOWN


async def health_check_loop(interval_seconds: int = 300):
    while True:
        async with aiohttp.ClientSession() as session:
            tasks = [asyncio.create_task(_check_server(session, server)) for server in SERVERS]
            results = await asyncio.gather(*tasks)
            for server, status in zip(SERVERS, results):
                previous = _server_status.get(server["id"])
                _server_status[server["id"]] = status
                if previous and previous != status:
                    await send_alert(f"⚡ Сервер <b>{server['id']}</b> сменил статус: {status}")
        active_server = get_active_server()
        if active_server:
            global _active_server_id
            if _active_server_id != active_server["id"]:
                _active_server_id = active_server["id"]
                await send_alert(f"🔁 Активный сервер: <b>{active_server['id']}</b>")
                await update_dns(active_server.get("public_ip"))
        await asyncio.sleep(interval_seconds)

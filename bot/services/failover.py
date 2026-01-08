import logging

import aiohttp

from config import (
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_DNS_NAME,
    CLOUDFLARE_RECORD_ID,
    CLOUDFLARE_ZONE_ID,
)

logger = logging.getLogger(__name__)


async def update_dns(target_ip: str):
    if not (CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID and CLOUDFLARE_RECORD_ID):
        logger.info("Cloudflare credentials missing; skip DNS update")
        return False
    if not target_ip:
        logger.warning("No target IP for DNS update")
        return False
    url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records/{CLOUDFLARE_RECORD_ID}"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "type": "A",
        "name": CLOUDFLARE_DNS_NAME,
        "content": target_ip,
        "ttl": 120,
        "proxied": False,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=payload, headers=headers, timeout=10) as resp:
                data = await resp.json()
                if not data.get("success"):
                    logger.warning("Cloudflare DNS update failed: %s", data)
                    return False
                return True
    except Exception as e:
        logger.warning("Cloudflare DNS update error: %s", e)
        return False

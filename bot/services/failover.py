import asyncio
import logging

import aiohttp

from config import (
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_DNS_NAME,
    CLOUDFLARE_RECORD_ID,
    CLOUDFLARE_RETRY_BACKOFF_SECONDS,
    CLOUDFLARE_RETRY_COUNT,
    CLOUDFLARE_TIMEOUT_SECONDS,
    CLOUDFLARE_ZONE_ID,
)

logger = logging.getLogger(__name__)


async def update_dns(target_ip: str) -> bool:
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
    timeout = aiohttp.ClientTimeout(total=CLOUDFLARE_TIMEOUT_SECONDS)
    for attempt in range(CLOUDFLARE_RETRY_COUNT + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.put(url, json=payload, headers=headers) as resp:
                    data = await resp.json()
                    if not data.get("success"):
                        logger.warning("Cloudflare DNS update failed: %s", data)
                        if attempt < CLOUDFLARE_RETRY_COUNT:
                            await asyncio.sleep(CLOUDFLARE_RETRY_BACKOFF_SECONDS * (attempt + 1))
                            continue
                        return False
                    logger.info("Cloudflare DNS updated to %s", target_ip)
                    return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning("Cloudflare DNS update error (attempt %s/%s): %s", attempt + 1, CLOUDFLARE_RETRY_COUNT + 1, e)
            if attempt < CLOUDFLARE_RETRY_COUNT:
                await asyncio.sleep(CLOUDFLARE_RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            return False
    return False

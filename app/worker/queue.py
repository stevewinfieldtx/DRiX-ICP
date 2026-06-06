"""Enqueue background jobs onto ARQ/Redis. Degrades to no-op if Redis is down."""
import logging

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

log = logging.getLogger(__name__)


async def enqueue(func_name: str, *args) -> None:
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await pool.enqueue_job(func_name, *args)
        await pool.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("enqueue %s failed (%s); skipping background job", func_name, exc)

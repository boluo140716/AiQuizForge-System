"""统一的缓存 / 限流存储。

设计目标：把原本放在「每个进程自己的内存」里的缓存与限流计数，改为放在 Redis，
这样多开几个 ai_service 副本时，缓存和限流才是共享、一致的。

降级策略：若 Redis 不可用（例如本机没启动 Redis），自动降级为进程内存，仅保证
本地开发/演示能跑；此时多副本下缓存与限流会失效——所以正式部署必须提供 Redis。
"""
import logging
import time
import uuid
from collections import defaultdict
from typing import Optional

from decouple import config

logger = logging.getLogger(__name__)

# 默认 db=2，与 Django 的缓存(db1) / Celery(db0) 隔离，互不干扰
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/2")

_client = None
_redis_ok: Optional[bool] = None  # None=尚未探测, True=可用, False=不可用

# ---- 降级用：进程内存（仅本地兜底，不可用于多副本）----
_mem_kv: dict[str, tuple[float, str]] = {}
_mem_zset: dict[str, list[float]] = defaultdict(list)
_MEM_KV_MAX = 256


async def _get_client():
    """返回可用的 Redis 客户端；不可用则返回 None（触发降级）。"""
    global _client, _redis_ok

    if _client is None:
        try:
            import redis.asyncio as aioredis
            _client = aioredis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        except Exception as e:  # 依赖缺失等
            logger.error("初始化 Redis 客户端失败，降级为进程内存：%s", e)
            _redis_ok = False
            return None

    if _redis_ok is None:
        try:
            await _client.ping()
            _redis_ok = True
            logger.info("已连接 Redis：%s", REDIS_URL)
        except Exception as e:
            _redis_ok = False
            logger.warning("Redis 不可用，降级为进程内存（多副本下缓存/限流将不共享）：%s", e)

    return _client if _redis_ok else None


async def cache_get(key: str) -> Optional[str]:
    """读缓存。返回字符串值或 None。"""
    global _redis_ok

    client = await _get_client()
    if client is not None:
        try:
            return await client.get(key)
        except Exception as e:
            _redis_ok = False
            logger.warning("Redis GET 失败，降级为进程内存：%s", e)

    item = _mem_kv.get(key)
    if item is None:
        return None
    expire_at, value = item
    if time.time() < expire_at:
        return value
    _mem_kv.pop(key, None)
    return None


async def cache_set(key: str, value: str, ttl: int) -> None:
    """写缓存，ttl 秒后过期。"""
    global _redis_ok

    client = await _get_client()
    if client is not None:
        try:
            await client.set(key, value, ex=ttl)
            return
        except Exception as e:
            _redis_ok = False
            logger.warning("Redis SET 失败，降级为进程内存：%s", e)

    if len(_mem_kv) >= _MEM_KV_MAX:
        oldest = min(_mem_kv, key=lambda k: _mem_kv[k][0])
        _mem_kv.pop(oldest, None)
    _mem_kv[key] = (time.time() + ttl, value)


async def rate_limit_ok(key: str, limit: int, window: int) -> bool:
    """滑动窗口限流：window 秒内最多 limit 次。返回 True=放行，False=超限。"""
    global _redis_ok

    now = time.time()

    client = await _get_client()
    if client is not None:
        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)              # 清掉窗口外的旧记录
            pipe.zadd(key, {f"{now}-{uuid.uuid4().hex[:8]}": now})   # 记录本次请求
            pipe.zcard(key)                                           # 统计窗口内数量
            pipe.expire(key, window)                                  # 窗口过期自动清理
            _, _, count, _ = await pipe.execute()
            return int(count) <= limit
        except Exception as e:
            _redis_ok = False
            logger.warning("Redis 限流失败，降级为进程内存：%s", e)

    records = [t for t in _mem_zset[key] if now - t < window]
    if len(records) >= limit:
        _mem_zset[key] = records
        return False
    records.append(now)
    _mem_zset[key] = records
    return True

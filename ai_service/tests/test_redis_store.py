"""手动验证 redis_store：滑动窗口限流 + 缓存共享。

运行方式（在 ai-service 容器内，需先 rebuild 让 redis 依赖装上）：
    docker compose up -d redis
    docker compose build ai-service
    docker compose up -d ai-service
    docker compose exec ai-service python tests/test_redis_store.py

期望输出：
    Redis 可用： True
    限流 3/60s 连续 4 次 -> [True, True, True, False]
    缓存读回： {"hello":"世界"}
    另一副本能读到该缓存键： {"hello":"世界"}   （证明缓存放在 Redis，副本之间共享）
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_store import REDIS_URL, cache_get, cache_set, rate_limit_ok  # noqa: E402


async def main():
    import redis.asyncio as aioredis

    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await client.ping()
        print("Redis 可用： True")
    except Exception as e:
        print(f"Redis 不可用（会降级为进程内存）：{e}")
        return

    # 1) 滑动窗口限流：窗口内最多 3 次
    key = "rl:test:unittest"
    await client.delete(key)
    results = [await rate_limit_ok(key, 3, 60) for _ in range(4)]
    print(f"限流 3/60s 连续 4 次 -> {results}   （期望 [True, True, True, False]）")

    # 2) 缓存读写
    ck = "llm:cache:unittest"
    await client.delete(ck)
    await cache_set(ck, '{"hello":"世界"}', 60)
    print(f"缓存读回： {await cache_get(ck)}   （期望 {{\"hello\":\"世界\"}}）")

    # 3) 共享验证：用另一个连接（模拟另一个副本）读同一个键
    other = aioredis.from_url(REDIS_URL, decode_responses=True)
    print(f"另一副本能读到该缓存键： {await other.get(ck)}   （非空即证明共享）")
    await other.aclose()

    # 清理测试键
    await client.delete(key, ck)
    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())

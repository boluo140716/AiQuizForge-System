#!/bin/sh
set -e

# 等待 MySQL 就绪
echo "Waiting for MySQL at ${DB_HOST:-db}:${DB_PORT:-3306}..."
while ! python -c "
import socket, time
s = socket.socket()
s.settimeout(2)
try:
    s.connect(('${DB_HOST:-db}', int('${DB_PORT:-3306}')))
    s.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; do
    echo "  MySQL not ready, retrying in 2s..."
    sleep 2
done
echo "MySQL is ready!"

# 等待 Redis 就绪
echo "Waiting for Redis at ${REDIS_HOST:-redis}:${REDIS_PORT:-6379}..."
while ! python -c "
import socket, time
s = socket.socket()
s.settimeout(2)
try:
    s.connect(('${REDIS_HOST:-redis}', int('${REDIS_PORT:-6379}')))
    s.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; do
    echo "  Redis not ready, retrying in 2s..."
    sleep 2
done
echo "Redis is ready!"

# 运行数据库迁移
echo "Running database migrations..."
python manage.py migrate --noinput

echo "Starting application..."
exec "$@"

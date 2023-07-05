import functools

import redis

from kryptone import logger


@functools.lru_cache(maxsize=1)
def redis_connection(host='redis', port=6379):
    instance = redis.Redis(host, port)
    logger.info('Connecting to Redis...')
    try:
        instance.ping()
    except:
        return False
    else:
        return instance


@functools.lru_cache(maxsize=1)
def memcache_connection(host='memcache', port=11211):
    from pymemcache.client.base import Client
    instance = Client(f'{host}:{port}')
    try:
        instance._connect()
        return instance
    except:
        return False

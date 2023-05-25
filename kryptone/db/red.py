import redis


class RedisConnection:
    def __init__(self):
        self.host = None
        self.port = None
        self.password = None
        self.connection = redis.Redis(
            host=self.host,
            port=self.port,
            password=self.password
        )

import sys
import logging
import socket
from typing import List, Optional

import redis

from datetime import datetime as dt
from datetime import timedelta

from dinofw.cache import ICache
from dinofw.config import ConfigKeys, RedisKeys

logger = logging.getLogger(__name__)


class MemoryCache:
    def __init__(self):
        self.vals = dict()

    def set(self, key, value, ttl=30):
        try:
            expires_at = (dt.utcnow() + timedelta(seconds=ttl)).timestamp()
            self.vals[key] = (expires_at, value)
        except:
            pass

    def get(self, key):
        try:
            if key not in self.vals:
                return None
            expires_at, value = self.vals[key]
            now = dt.utcnow().timestamp()
            if now > expires_at:
                del self.vals[key]
                return None
            return value
        except:
            return None

    def delete(self, key):
        if key in self.vals:
            del self.vals[key]

    def flushall(self):
        self.vals = dict()


class CacheRedis(ICache):
    def __init__(self, env, host: str, port: int = 6379, db: int = 0):
        if env.config.get(ConfigKeys.TESTING, False) or host == "mock":
            from fakeredis import FakeStrictRedis

            self.redis_pool = None
            self.redis_instance = FakeStrictRedis(host=host, port=port, db=db)
        else:
            self.redis_pool = redis.ConnectionPool(host=host, port=port, db=db)
            self.redis_instance = None

        self.cache = MemoryCache()

        args = sys.argv
        for a in ["--bind", "-b"]:
            bind_arg_pos = [i for i, x in enumerate(args) if x == a]
            if len(bind_arg_pos) > 0:
                bind_arg_pos = bind_arg_pos[0]
                break

        self.listen_port = "standalone"
        if bind_arg_pos is not None and not isinstance(bind_arg_pos, list):
            self.listen_port = args[bind_arg_pos + 1].split(":")[1]

        self.listen_host = socket.gethostname().split(".")[0]

    def get_user_ids_in_group(self, group_id: str):
        return self.redis.smembers(RedisKeys.user_ids_in_group(group_id))

    def set_user_ids_in_group(self, group_id: str, user_ids: List[int]):
        key = RedisKeys.user_ids_in_group(group_id)
        self.redis.delete(key)
        return self.redis.sadd(key, *user_ids)

    def get_last_read_time_in_group_for_user(self, group_id: str, user_id: int) -> Optional[dt]:
        # TODO: when/how to update? when user retrieves messages or when acking or both?

        key = RedisKeys.last_read_time(group_id)
        last_read = self.redis.hget(key, user_id)

        if last_read is None:
            return None

        last_sent = int(float(str(last_read, "utf-8")))
        return dt.utcfromtimestamp(last_sent)

    def set_last_read_time_in_group_for_user(self, group_id: str, user_id: int, last_read: dt) -> None:
        key = RedisKeys.last_read_time(group_id)
        last_read = last_read.strftime("%s")
        self.redis.hset(key, user_id, last_read)

    def get_last_send_time_in_group_for_user(self, group_id: str, user_id: int) -> Optional[dt]:
        key = RedisKeys.last_send_time(group_id)
        last_sent = self.redis.hget(key, user_id)

        if last_sent is None:
            return None

        last_sent = int(float(str(last_sent, "utf-8")))
        return dt.utcfromtimestamp(last_sent)

    def set_last_send_time_in_group_for_user(self, group_id: str, user_id: int, last_sent: dt) -> None:
        key = RedisKeys.last_send_time(group_id)
        last_sent = last_sent.strftime("%s")
        self.redis.hset(key, user_id, last_sent)

    @property
    def redis(self):
        if self.redis_pool is None:
            return self.redis_instance
        return redis.Redis(connection_pool=self.redis_pool)

    def _flushall(self) -> None:
        self.redis.flushdb()
        self.cache.flushall()

    def _set(self, key, val, ttl=None) -> None:
        if ttl is None:
            self.cache.set(key, val)
        else:
            self.cache.set(key, val, ttl=ttl)

    def _get(self, key):
        return self.cache.get(key)

    def _del(self, key) -> None:
        self.cache.delete(key)

import redis
import json
import os
from odoo.tools import config


class Redis:
    conn = None

    def __init__(self, ip="", port=""):
        self.IS_ENABLE = True
        if not ip:
            try:
                ip = '127.0.0.1'
            except:
                self.IS_ENABLE = False
            
        if not port:
            try:
                port = config['redis_port']
            except:
                port = 6379

        self.conn = redis.Redis(ip, port, encoding="utf-8", decode_responses=True)

    def set(self, key='', data='', ex=60):
        if self.IS_ENABLE:
            try:
                self.conn.set(key, data, ex=ex)
            except:
                pass

    def get(self, key=''):
        if self.IS_ENABLE:
            return self.conn.get(key)
        
        return None

    def is_expired(self, key):
        value = self.get(key=key)

        if not value:
            return True

        return False

    def flush(self, key):
        try:
            self.conn.delete(key)
        except:
            pass

    def flushall(self):
        try:
            self.conn.flushall()
        except:
            pass

    def lrande(self, key):
        return self.conn.lrange(key, 0, -1)
        
    def rpush(self, key ,value):
        try:
            self.conn.rpush(key, value)
        except:
            pass

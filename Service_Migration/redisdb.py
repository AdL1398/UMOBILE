#!/usr/bin/env python2.7

import redis
import ast

r = redis.StrictRedis(host='192.168.1.104', port=6379, db=0)

def set(key, value):
    r.set(key, value)

def exists(key):
    return r.exists(key)

def get(key):
    value = r.get(key)
    if value == None:
        return None
    else:
        # Check dict syntax
        try:
            dict = ast.literal_eval(value)
            return dict
        except Exception, e:
            print 'Error: Cannot parse value', e

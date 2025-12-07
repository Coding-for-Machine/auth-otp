import time

cache_data = {}

def set_cache(key, value, cache_time: int = 3600):
    expire_at = time.time() + cache_time
    cache_data[key] = {"data": value, "expire_at": expire_at}
    return cache_data[key]

def get_cache(key):
    item = cache_data.get(key)
    if item:
        if time.time() <= item["expire_at"]:
            return item["data"], item["expire_at"]
        else:
            del cache_data[key]
    return None, None

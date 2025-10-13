import asyncio


def sync(f):
    def wrapper(*args, **kwargs):
        asyncio.get_event_loop().create_task(f(*args, **kwargs))

    return wrapper

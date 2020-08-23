from functools import wraps


def validate_with_keyerror(exc_cls, return_value=True):

    def decorated(func):
        @wraps(func)
        async def wrapper(this, key, *args, **kwargs):
            code, msg, value = await func(this, key, *args, **kwargs)
            if code == -1:
                raise KeyError(key)
            elif code != 1:
                raise exc_cls(msg)
            if return_value:
                return value

        return wrapper

    return decorated


def validate(exc_cls, return_value=True):

    def decorated(func):
        @wraps(func)
        async def wrapper(this, *args, **kwargs):
            code, msg, value = await func(this, *args, **kwargs)
            if code != 1:
                raise exc_cls(msg)
            if return_value:
                return value

        return wrapper

    return decorated

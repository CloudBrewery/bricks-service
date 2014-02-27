import functools

from bricks.objects import brick
from bricks.objects import brickconfig


def objectify(klass):
    """Decorator to convert database results into specified objects."""
    def the_decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            try:
                return klass._from_db_object(klass(), result)
            except TypeError:
                # TODO(deva): handle lists of objects better
                #             once support for those lands and is imported.
                return [klass._from_db_object(klass(), obj) for obj in result]
        return wrapper
    return the_decorator

BrickConfig = brickconfig.BrickConfig
Brick = brick.Brick

__all__ = (BrickConfig,
           Brick)

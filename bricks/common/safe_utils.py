"""Utilities and helper functions that won't produce circular imports."""

import inspect


def getcallargs(function, *args, **kwargs):
    """This is a simplified inspect.getcallargs (2.7+).

    It should be replaced when python >= 2.7 is standard.
    """
    keyed_args = {}
    argnames, varargs, keywords, defaults = inspect.getargspec(function)

    keyed_args.update(kwargs)

    #NOTE(alaski) the implicit 'self' or 'cls' argument shows up in
    # argnames but not in args or kwargs.  Uses 'in' rather than '==' because
    # some tests use 'self2'.
    if 'self' in argnames[0] or 'cls' == argnames[0]:
        # The function may not actually be a method or have im_self.
        # Typically seen when it's stubbed with mox.
        if inspect.ismethod(function) and hasattr(function, 'im_self'):
            keyed_args[argnames[0]] = function.im_self
        else:
            keyed_args[argnames[0]] = None

    remaining_argnames = filter(lambda x: x not in keyed_args, argnames)
    keyed_args.update(dict(zip(remaining_argnames, args)))

    if defaults:
        num_defaults = len(defaults)
        for argname, value in zip(argnames[-num_defaults:], defaults):
            if argname not in keyed_args:
                keyed_args[argname] = value

    return keyed_args

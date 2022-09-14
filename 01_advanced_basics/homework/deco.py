#!/usr/bin/env python
# -*- coding: utf-8 -*-
from functools import update_wrapper, wraps


def disable(func):
    def wrapper(*args):
        return func(*args)

    update_wrapper(wrapper, func)
    return wrapper


def decorator(func):
    """
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    """

    def wrapper(*args):
        wrapper.__doc__ = func.__doc__
        return func(*args)

    return wrapper


@decorator
def countcalls(func):
    """Decorator that counts calls made to the function decorated."""

    def wrapper(*args):
        wrapper.calls += 1
        return func(*args)

    wrapper.calls = 0
    return wrapper


def memo(func):
    """
    Memoize a function so that it caches all return values for
    faster future lookups.
    """
    results = {}

    def wrapper(*args):
        if args in results:
            return results[args]
        result = func(*args)
        results[args] = result
        return result

    return wrapper


def n_ary(func):
    """
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    """

    def wrapper(x, *args):
        return x if not args else func(x, wrapper(*args))

    return wrapper


#
def trace(symbols):
    """Trace calls made to function decorated."""

    def trace_func(func):
        @wraps(func)
        def wrapper(*args):
            print(symbols * wrapper.trace, "--> fib{}".format(*args))
            wrapper.trace += 1
            result = func(*args)
            wrapper.trace -= 1
            print(symbols * wrapper.trace, "<-- fib{0} == {1}".format(*args, result))
            return result

        wrapper.trace = 0
        return wrapper

    return trace_func


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace(symbols="####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n - 1) + fib(n - 2)


def main():
    print(foo(4, 3))
    print(foo(4, 3, 2))
    print(foo(4, 3))
    print("foo was called", foo.calls, "times")
    #
    print(bar(4, 3))
    print(bar(4, 3, 2))
    print(bar(4, 3, 2, 1))
    print("bar was called", bar.calls, "times")

    print(fib.__doc__)
    fib(3)
    print(fib.calls, "calls made")


def a(*args):
    print(len(args))


@trace("####№№№№")
def sum_func(a, b):
    return a + b


if __name__ == "__main__":
    main()

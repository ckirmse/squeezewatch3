#!/usr/bin/python

class Deferred:
    """Synchronous callback chain drop-in for twisted.internet.defer.Deferred."""

    def __init__(self):
        self._cbs = []

    def addCallback(self, fn, *args, **kwargs):
        self._cbs.append((fn, args, kwargs))
        return self

    def callback(self, result):
        for fn, args, kwargs in self._cbs:
            result = fn(result, *args, **kwargs)

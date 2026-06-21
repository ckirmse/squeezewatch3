#!/usr/bin/python

class Deferred:
    """Synchronous callback chain drop-in for twisted.internet.defer.Deferred."""

    def __init__(self):
        self._cbs = []

    def addCallback(self, fn, *extra):
        self._cbs.append((fn, extra))
        return self

    def callback(self, result):
        for fn, extra in self._cbs:
            result = fn(result, *extra)

#! /usr/bin/env python
# -*- coding: utf-8 -*-

from gevent import monkey

monkey.patch_all(thread=False)

from gevent_requests import get, gmap, gimap, is_callable_with_two_args

########### Constants ############
urls = ["http://gitee.com", "http://www.baidu.com", "http://www.cn.bing.com"]


############# tests ##############
def test_get():
    to_fetch = (get(url) for url in urls)
    fetched = gmap(to_fetch)
    for f in fetched:
        assert f.ok, True


def test_gimap_with_size():
    to_fetch = (get(url) for url in urls)
    gimap(to_fetch, size=len(urls) - 1)
    for fetching in to_fetch:
        assert fetching.send(), True


import os
import time
import unittest

import requests
from requests.exceptions import Timeout
import gevent_requests

HTTPBIN_URL = os.environ.get("HTTPBIN_URL", "http://httpbin.org/")


def httpbin(*suffix):
    """Returns url for HTTPBIN resource."""
    return HTTPBIN_URL + "/".join(suffix)


N = 5
URLS = [httpbin("get?p=%s" % i) for i in range(N)]


class TestGeventRequests(unittest.TestCase):

    def test_gmap(self):
        reqs = [gevent_requests.get(url) for url in URLS]
        resp = gevent_requests.gmap(reqs, size=N)
        self.assertEqual([r.url for r in resp], URLS)

    def test_gimap(self):
        reqs = (gevent_requests.get(url) for url in URLS)
        i = 0
        for i, r in enumerate(gevent_requests.gimap(reqs, size=N)):
            self.assertTrue(r.url in URLS)
        self.assertEqual(i, N - 1)

    def test_hooks(self):
        result = {}

        def hook(r, **kwargs):
            result[r.url] = True
            return r

        reqs = [gevent_requests.get(url, hooks={"response": [hook]}) for url in URLS]
        gevent_requests.gmap(reqs, size=N)
        self.assertEqual(sorted(result.keys()), sorted(URLS))

    def test_callback_kwarg(self):
        result = {"ok": False}

        def callback(r, **kwargs):
            result["ok"] = True
            return r

        self.get(URLS[0], callback=callback)
        self.assertTrue(result["ok"])

    def test_session_and_cookies(self):
        c1 = {"k1": "v1"}
        r = self.get(httpbin("cookies/set"), params=c1).json()
        self.assertEqual(r["cookies"], c1)
        s = requests.Session()
        r = self.get(httpbin("cookies/set"), session=s, params=c1).json()
        self.assertEqual(dict(s.cookies), c1)

        # ensure all cookies saved
        c2 = {"k2": "v2"}
        c1.update(c2)
        r = self.get(httpbin("cookies/set"), session=s, params=c2).json()
        self.assertEqual(dict(s.cookies), c1)

        # ensure new session is created
        r = self.get(httpbin("cookies")).json()
        self.assertEqual(r["cookies"], {})

        # cookies as param
        c3 = {"p1": "42"}
        r = self.get(httpbin("cookies"), cookies=c3).json()
        self.assertEqual(r["cookies"], c3)

    def test_calling_request(self):
        reqs = [gevent_requests.request("POST", httpbin("post"), data={"p": i}) for i in range(N)]
        resp = gevent_requests.gmap(reqs, size=N)
        self.assertEqual([int(r.json()["form"]["p"]) for r in resp], list(range(N)))

    def test_stream_enabled(self):
        r = gevent_requests.gmap([gevent_requests.get(httpbin("stream/10"))], size=2, stream=True)[0]
        self.assertFalse(r._content_consumed)

    def test_concurrency_with_delayed_url(self):
        t = time.time()
        n = 10
        reqs = [gevent_requests.get(httpbin("delay/1")) for _ in range(n)]
        gevent_requests.gmap(reqs, size=n)
        self.assertLess((time.time() - t), n)

    def test_map_timeout_no_exception_handler(self):
        """
        compliance with existing 0.2.0 behaviour
        """
        reqs = [gevent_requests.get(httpbin("delay/1"), timeout=0.001), gevent_requests.get(httpbin("/"))]
        responses = gevent_requests.gmap(reqs)
        self.assertIsNone(responses[0])
        self.assertTrue(responses[1].ok)
        self.assertEqual(len(responses), 2)

    def test_map_timeout_exception_handler_no_return(self):
        """
        ensure default behaviour for a handler that returns None
        """

        def exception_handler(request, exception):
            pass

        reqs = [gevent_requests.get(httpbin("delay/1"), timeout=0.001), gevent_requests.get(httpbin("/"))]
        responses = gevent_requests.gmap(reqs, exception_handler=exception_handler)
        self.assertIsNone(responses[0])
        self.assertTrue(responses[1].ok)
        self.assertEqual(len(responses), 2)

    def test_map_timeout_exception_handler_returns_exception(self):
        """
        ensure returned value from exception handler is stuffed in the map result
        """

        def exception_handler(request, exception):
            return exception

        reqs = [gevent_requests.get(httpbin("delay/1"), timeout=0.001), gevent_requests.get(httpbin("/"))]
        responses = gevent_requests.gmap(reqs, exception_handler=exception_handler)
        self.assertIsInstance(responses[0], Timeout)
        self.assertTrue(responses[1].ok)
        self.assertEqual(len(responses), 2)

    def test_gimap_timeout_no_exception_handler(self):
        """
        compliance with existing 0.2.0 behaviour
        """
        reqs = [gevent_requests.get(httpbin("delay/1"), timeout=0.001)]
        out = []
        try:
            for r in gevent_requests.gimap(reqs):
                out.append(r)
        except Timeout:
            pass
        self.assertEqual(out, [])

    def test_gimap_timeout_exception_handler_no_return(self):
        """
        ensure gimap-default behaviour for a handler that returns None
        """

        def exception_handler(request, exception):
            pass

        reqs = [gevent_requests.get(httpbin("delay/1"), timeout=0.001)]
        out = []
        for r in gevent_requests.gimap(reqs, exception_handler=exception_handler):
            out.append(r)
        self.assertEqual(out, [])

    def test_gimap_timeout_exception_handler_returns_value(self):
        """
        ensure behaviour for a handler that returns a value
        """

        def exception_handler(request, exception):
            return "a value"

        reqs = [gevent_requests.get(httpbin("delay/1"), timeout=0.001)]
        out = []
        for r in gevent_requests.gimap(reqs, exception_handler=exception_handler):
            out.append(r)
        self.assertEqual(out, ["a value"])

    def test_map_timeout_exception(self):
        class ExceptionHandler:
            def __init__(self):
                self.counter = 0

            def callback(self, request, exception):
                self.counter += 1

        eh = ExceptionHandler()
        reqs = [gevent_requests.get(httpbin("delay/1"), timeout=0.001)]
        list(gevent_requests.gmap(reqs, exception_handler=eh.callback))
        self.assertEqual(eh.counter, 1)

    def test_gimap_timeout_exception(self):
        class ExceptionHandler:
            def __init__(self):
                self.counter = 0

            def callback(self, request, exception):
                self.counter += 1

        eh = ExceptionHandler()
        reqs = [gevent_requests.get(httpbin("delay/1"), timeout=0.001)]
        list(gevent_requests.gimap(reqs, exception_handler=eh.callback))
        self.assertEqual(eh.counter, 1)

    def get(self, url, **kwargs):
        return gevent_requests.gmap([gevent_requests.get(url, **kwargs)])[0]


class TestIsCallableWithTwoArgs(unittest.TestCase):

    def test_callable_with_two_args(self):
        def func(arg1, arg2):
            pass
        self.assertTrue(is_callable_with_two_args(func))

    def test_callable_with_one_arg(self):
        def func(arg1):
            pass
        self.assertFalse(is_callable_with_two_args(func))

    def test_callable_with_three_args(self):
        def func(arg1, arg2, arg3):
            pass
        self.assertFalse(is_callable_with_two_args(func))

    def test_non_callable(self):
        self.assertFalse(is_callable_with_two_args(123))

    def test_builtin_function(self):
        self.assertFalse(is_callable_with_two_args(int))

    def test_lambda_function(self):
        self.assertTrue(is_callable_with_two_args(lambda x, y: x + y))

    def test_method(self):
        class MyClass:
            def method(self, arg1, arg2):
                pass
        self.assertTrue(is_callable_with_two_args(MyClass().method))

    def test_staticmethod(self):
        class MyClass:
            @staticmethod
            def method(arg1, arg2):
                pass
        self.assertTrue(is_callable_with_two_args(MyClass.method))

    def test_classmethod(self):
        class MyClass:
            @classmethod
            def method(cls, arg1, arg2):
                pass
        self.assertTrue(is_callable_with_two_args(MyClass.method))


if __name__ == "__main__":
    unittest.main()

gevent-requests: Asynchronous Requests

---


![PyPI - License](https://img.shields.io/pypi/l/gevent-requests?style=for-the-badge) [![version](https://img.shields.io/pypi/v/gevent_requests.svg?colorB=blue&style=for-the-badge)](https://pypi.org/project/gevent-requests/) ![pyversions](https://img.shields.io/pypi/pyversions/gevent_requests.svg?style=for-the-badge) ![PyPI - Downloads](https://img.shields.io/pypi/dm/gevent-requests?style=for-the-badge) ![Pepy Total Downlods](https://img.shields.io/pepy/dt/gevent_requests?style=for-the-badge&logo=python)


gevent-requests allows you to use Requests with Gevent to make asynchronous HTTP
Requests easily.


A fork from `grequests <https://github.com/spyoungtech/grequests>`.

It is highly recommended that you patch from the entry and do not include thread, this package does not include patch!

```shell
pip install gevent-requests
```

---

Usage is simple:

```python

from gevent import monkey
monkey.patch_all(thread=False, select=False)
import gevent_requests

urls = [
    'http://www.heroku.com',
    'http://python-tablib.org',
    'http://httpbin.org',
    'https://shields.io',
    'http://fakedomain/',
]
```

Create a set of unsent Requests:

```python
>>> rs = (gevent_requests.get(u) for u in urls)
```
Send them all at the same time:

```python
>>> print(gevent_requests.gmap(rs))
[<Response [200]>, <Response [200]>, <Response [200]>, <Response [200]>, <Response [502]>]
```

Optionally, in the event of a timeout or any other exception during the connection of
the request, you can add an exception handler that will be called with the request and
exception inside the main thread:

```python
>>> def exception_handler(request, exception):
...    print("Request failed")

>>> reqs = [
...    gevent_requests.get('http://httpbin.org/delay/1', timeout=0.001),
...    gevent_requests.get('http://fakedomain/'),
...    gevent_requests.get('http://httpbin.org/status/500')]
>>> print(gevent_requests.gmap(reqs, exception_handler=exception_handler))
Request failed
[None, <Response [502]>, <Response [500]>]
```

For some speed/performance gains, you may also want to use `imap` instead of `map`. `imap` returns a generator of responses. Order of these responses does not map to the order of the requests you send out. The API for `imap` is equivalent to the API for `map`.

Use indexed requests in gevent, use `gimap_enumerate` will yield a indexed requests just like `enumerate` return, an index and a response:

```python
>>> rs = (gevent_requests.get(u) for u in urls)

>>> for i in gevent_requests.gimap_enumerate(rs, size=len(urls)):
        print(i)
(4, <Response [502]>)
(2, <Response [200]>)
(0, <Response [200]>)
(3, <Response [200]>)
(1, <Response [200]>)
```

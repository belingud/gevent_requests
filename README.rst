Gevent-Requests: Asynchronous Requests
===============================

Gevent-Requests allows you to use Requests with Gevent to make asynchronous HTTP
Requests easily.

|version| |pyversions|


**Note**: You should probably use `requests-threads <https://github.com/requests/requests-threads>`_ or `requests-futures <https://github.com/ross/requests-futures>`_ instead.


Usage
-----

Usage is simple:

.. code-block:: python

    from gevent import monkey
    monkey.patch_all(thread=False, select=False)
    import gevent_requests

    urls = [
        'http://www.heroku.com',
        'http://python-tablib.org',
        'http://httpbin.org',
        'http://python-requests.org',
        'http://fakedomain/',
        'http://kennethreitz.com'
    ]

Create a set of unsent Requests:

.. code-block:: python

    >>> rs = (gevent_requests.get(u) for u in urls)

Send them all at the same time:

.. code-block:: python

    >>> gevent_requests.gmap(rs)
    [<Response [200]>, <Response [200]>, <Response [200]>, <Response [200]>, None, <Response [200]>]

Optionally, in the event of a timeout or any other exception during the connection of
the request, you can add an exception handler that will be called with the request and
exception inside the main thread:

.. code-block:: python

    >>> def exception_handler(request, exception):
    ...    print("Request failed")

    >>> reqs = [
    ...    gevent_requests.get('http://httpbin.org/delay/1', timeout=0.001),
    ...    gevent_requests.get('http://fakedomain/'),
    ...    gevent_requests.get('http://httpbin.org/status/500')]
    >>> gevent_requests.gmap(reqs, exception_handler=exception_handler)
    Request failed
    Request failed
    [None, None, <Response [500]>]

For some speed/performance gains, you may also want to use `imap` instead of `map`. `imap` returns a generator of responses. Order of these responses does not map to the order of the requests you send out. The API for `imap` is equivalent to the API for `map`.

Installation
------------

Installation is easy with pip::

    $ pip install gevent-requests
    ✨🍰✨


.. |version| image:: https://img.shields.io/pypi/v/gevent_requests.svg?colorB=blue
    :target: https://pypi.org/project/gevent-requests/

.. |pyversions| image:: https://img.shields.io/pypi/pyversions/gevent_requests.svg?
    :target: https://pypi.org/project/gevnent-requests/

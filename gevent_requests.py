# -*- coding: utf-8 -*-

"""
gevent_requests
~~~~~~~~~

This module contains an asynchronous replica of ``requests.api``, powered
by gevent. All API methods return a ``Request`` instance (as opposed to
``Response``). A list of requests can be sent with ``map()``.

A fork from grequests, grequests is not very applicable for all Python web server.
For example, run a flask server with no thread patch ``monkey.patch_all(thread=False)``
"""
import traceback
from functools import wraps

try:
    import gevent
    from gevent.pool import Pool
except ImportError:
    raise RuntimeError("Gevent is required for grequests.Install gevent by pip first.")

from requests import Session, Response

__all__ = (
    "gmap",
    "gimap",
    "get",
    "options",
    "head",
    "post",
    "put",
    "patch",
    "delete",
    "request",
)


class AsyncRequest(object):
    """Asynchronous request.

    Accept same parameters as ``Session.request`` and some additional:

    :param session: Session which will do request
    :type requests.Session:
    :param callback: Callback called on response.
                     Same as passing ``hooks={'response': callback}``
    :type Callable:
    """

    def __init__(self, method, url, **kwargs):
        #: Request method
        self.method = method
        #: URL to request
        self.url = url
        #: Associated ``requests.Session``
        self.session = kwargs.pop("session", None)
        if self.session is None:
            self.session = Session()
            self._close = True
        else:
            self._close = False  # don't close adapters after each request if the user provided the session

        callback = kwargs.pop("callback", None)
        if callback:
            kwargs["hooks"] = {"response": callback}

        #: The rest arguments for ``requests.Session.request``
        self.kwargs = kwargs
        #: Resulting ``requests.Response``
        self.response = None

        #: exception info
        self.exception = None
        self.traceback = None

    def send(self, **kwargs):
        """
        Prepares request based on parameter passed to constructor and optional ``kwargs``.
        Then sends request and saves response to :attr:`response`

        :returns: ``requests.Response``
        """
        merged_kwargs = {}
        merged_kwargs.update(self.kwargs)
        merged_kwargs.update(kwargs)
        try:
            self.response = self.session.request(self.method, self.url, **merged_kwargs)
        except Exception as e:
            self.exception = e
            self.traceback = traceback.format_exc()
        finally:
            if self._close:
                # if we provided the session object, make sure we're cleaning up
                # because there's no sense in keeping it open at this point if it wont be reused
                self.session.close()
        return self

    @classmethod
    def partial(cls, method):
        """
        Partial self as a named request short cut
        :param: method
        :type: str
        """
        @wraps(cls)
        def decorator(url, **kwargs):
            return cls(method, url, **kwargs)

        return decorator


def send(r, pool=None, stream=False):
    """Sends the request object using the specified pool. If a pool isn't
    specified this method blocks. Pools are useful because you can specify size
    and can hence limit concurrency.

    :param r:
    :type r: AsyncRequest
    :param pool:
    :type pool: Pool
    :param stream:
    :type stream: bool
    :return: greenlet
    """
    if pool is not None:
        return pool.spawn(r.send, stream=stream)

    return gevent.spawn(r.send, stream=stream)


# Shortcuts for creating AsyncRequest with appropriate HTTP method
get = AsyncRequest.partial("GET")
options = AsyncRequest.partial("OPTIONS")
head = AsyncRequest.partial("HEAD")
post = AsyncRequest.partial("POST")
put = AsyncRequest.partial("PUT")
patch = AsyncRequest.partial("PATCH")
delete = AsyncRequest.partial("DELETE")


# synonym
def request(method, url, **kwargs):
    return AsyncRequest(method, url, **kwargs)


def gmap(requests, stream=False, size=None, exception_handler=None, gtimeout=None):
    """Concurrently converts a list of Requests to Responses.

    :param requests: a collection of Request objects.
    :param stream: If True, the content will not be downloaded immediately.
    :param size: Specifies the number of requests to make at a time. If None, no throttling occurs.
    :param exception_handler: Callback function, called when exception occured. Params: Request, Exception
    :param gtimeout: Gevent joinall timeout in seconds. (Note: unrelated to requests timeout)
    """
    assert exception_handler is None or callable(exception_handler), "exception_handler has to be a callable object"

    requests = list(requests)

    pool = Pool(size) if size else None
    jobs = [send(r, pool, stream=stream) for r in requests]
    gevent.joinall(jobs, timeout=gtimeout)

    ret = []

    for req in requests:
        if req.response is not None:
            ret.append(req.response)
        elif exception_handler and hasattr(req, "exception"):
            ret.append(exception_handler(req, req.exception))
        elif exception_handler and not hasattr(req, "exception"):
            ret.append(exception_handler(req, None))
        else:
            ret.append(None)

    return ret


def gimap(requests, stream=False, size=2, exception_handler=None):
    """Concurrently converts a generator object of Requests to
    a generator of Responses.

    :param requests: a generator of Request objects.
    :param stream: If True, the content will not be downloaded immediately.
    :param size: Specifies the number of requests to make at a time. default is 2
    :param exception_handler: Callback function, called when exception occurred. Params: Request, Exception
    """

    pool = Pool(size)

    def _send(r):
        return r.send(stream=stream)

    for req in pool.imap_unordered(_send, requests):
        if req.response is not None:
            yield req.response
        elif exception_handler:
            ex_result = exception_handler(req, req.exception)
            if ex_result is not None:
                yield ex_result

    pool.join()

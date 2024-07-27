# -*- coding: utf-8 -*-

"""
gevent_requests
~~~~~~~~~

This module contains an asynchronous replica of ``requests.api``, powered
by gevent. All API methods return a ``Request`` instance (as opposed to
``Response``). A list of requests can be sent with ``map()``.

A fork from gevent_requests, gevent_requests is not very applicable for all Python web server.
For example, run a flask server with no thread patch ``monkey.patch_all(thread=False)``
"""
__version__ = "1.1.1"

import builtins
import traceback
from functools import wraps

try:
    import gevent
    from gevent.pool import Pool
except ImportError:
    raise RuntimeError(
        "Gevent is required for gevent_requests. Install gevent by pip first."
    ) from None

from requests import Session

__all__ = (
    "gmap",
    "gimap",
    "gimap_enumerate",
    "get",
    "options",
    "head",
    "post",
    "put",
    "patch",
    "delete",
    "request",
)

all_builtins = builtins.__dict__.values()


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
    """
    Sends an asynchronous request using gevent.

    Args:
        r (AsyncRequest): The request object to send.
        pool (Optional[Pool]): The gevent pool to use for sending the request. If not provided, a new greenlet will be created.
        stream (bool, optional): If True, the content of the response will not be downloaded immediately. Defaults to False.

    Returns:
        gevent.Greenlet: The greenlet that will execute the request.

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
    """
    Executes a concurrent mapping operation on the given `requests` iterator using a gevent pool.

    Args:
        requests (Iterable[AsyncRequest]): An iterable of AsyncRequest objects representing the requests to be executed concurrently.
        stream (bool, optional): If True, the content of the response will not be downloaded immediately. Defaults to False.
        size (int, optional): The number of requests to make at a time. Defaults to None.
        exception_handler (Callable[[AsyncRequest, Exception], Optional[Union[AsyncRequest, Response]]], optional):
            A callback function that handles exceptions raised during the execution of the requests.
            It takes the request object and the exception as parameters and returns an optional AsyncRequest or Response object.
            Defaults to None.
        gtimeout (float, optional): The maximum time (in seconds) that the function should wait for all requests to complete.
            If None, there is no timeout. Defaults to None.

    Returns:
        List[Optional[Response]]: A list of response objects for each request. If an exception occurs during the execution of a request,
            the corresponding response in the list will be None.

    Raises:
        AssertionError: If `exception_handler` is not None or callable.

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
    """
    Executes a concurrent mapping operation on the given `requests` iterator using a gevent pool.

    Args:
        requests (Iterable[AsyncRequest]): An iterable of AsyncRequest objects representing the requests to be executed concurrently.
        stream (bool, optional): If True, the content of the response will not be downloaded immediately. Defaults to False.
        size (int, optional): The number of requests to make at a time. Defaults to 2.
        exception_handler (Callable[[AsyncRequest, Exception], Optional[Union[AsyncRequest, Response]]], optional):
            A callback function that handles exceptions raised during the execution of the requests.
            It takes the request object and the exception as parameters and returns an optional AsyncRequest or Response object.
            Defaults to None.

    Yields:
        Union[AsyncRequest, Response]: A response object for each request.

    Raises:
        AssertionError: If `exception_handler` is not None or callable.

    Returns:
        None
    """
    assert exception_handler is None or callable(exception_handler), "exception_handler has to be a callable object"
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


def gimap_enumerate(requests, stream=False, size=2, exception_handler=None):
    """
    Executes a concurrent mapping operation on the given `requests` iterator using a gevent pool.
    The function yields a tuple of index and response for each request in the iterator.

    Args:
        requests (Iterable[Tuple[int, AsyncRequest]]): An iterable of tuples containing the index and AsyncRequest object for each request.
        stream (bool, optional): If True, the content of the response will not be downloaded immediately. Defaults to False.
        size (int, optional): The number of requests to make at a time. Defaults to 2.
        exception_handler (Callable[[AsyncRequest, Exception], Optional[Union[AsyncRequest, Response]]], optional):
            A callback function that handles exceptions raised during the execution of the requests.
            It takes the request object and the exception as parameters and returns an optional AsyncRequest or Response object.
            Defaults to None.

    Yields:
        Tuple[int, Union[AsyncRequest, Response]]: A tuple containing the index and response for each request.

    Raises:
        AssertionError: If `exception_handler` is not None or callable.

    Returns:
        None
    """
    assert exception_handler is None or callable(exception_handler), "exception_handler has to be a callable object"
    pool = Pool(size)

    def _send(r):
        # r is a tuple of (index, request)
        return r[0], r[1].send(stream=stream)

    indexed_requests = enumerate(list(requests))

    for index, req in pool.imap_unordered(_send, indexed_requests):
        if req.response is not None:
            yield index, req.response
        elif exception_handler:
            ex_result = exception_handler(req, req.exception)
            if ex_result is not None:
                yield index, ex_result

    pool.join()

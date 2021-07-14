# -*- coding: utf-8 -*-
"""
Gevent-Requests allows you to use Requests with Gevent to make asynchronous HTTP
Requests easily.
And this project also allow your own custom useage with gevent in your production environment,
for example your can use it with flask like:

>>> from gevent import monkey
>>> monkey.patch_all(thread=False, select=False)

Usage
-----

Usage is simple::

    >>> # First patch the socket
    >>> import gevent_requests

    >>> urls = [
    >>>     'http://www.heroku.com',
    >>>     'http://tablib.org',
    >>>     'http://httpbin.org',
    >>>     'http://python-requests.org',
    >>>     'http://kennethreitz.com'
    >>> ]

Create a set of unsent Requests::

    >>> rs = (gevent_requests.get(u) for u in urls)

Send them all at the same time::

    >>> gevent_requests.gmap(rs)
    [<Response [200]>, <Response [200]>, <Response [200]>, <Response [200]>, <Response [200]>]

"""

from setuptools import setup

setup(
    name="gevent_requests",
    version="0.6.1",
    url="https://github.com/belingud/grequests",
    license="BSD",
    author="Belingud",
    author_email="im.victor@qq.com",
    description="Use requests with gevent in your production",
    long_description=__doc__,
    install_requires=["gevent>0.8", "requests"],
    tests_require=["pytest"],
    py_modules=["gevent_requests"],
    zip_safe=False,
    include_package_data=True,
    platforms="any",
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)

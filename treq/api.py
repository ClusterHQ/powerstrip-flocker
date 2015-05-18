from twisted.web.client import Agent

from treq.client import HTTPClient
from treq._utils import default_reactor # default_pool
from twisted.internet.endpoints import (TCP4ClientEndpoint, SSL4ClientEndpoint,
        UNIXClientEndpoint)
from zope.interface import implementer
from twisted.web.iweb import IAgent
from twisted.web.error import SchemeNotSupported
from urllib import unquote

from twisted.web import client
client._HTTP11ClientFactory.noisy = False

@implementer(IAgent)
class UNIXCapableAgent(Agent):
    """
    Subclass of Agent which has the ability to connect to UNIX sockets, such as
    the Docker API.

    See http://tm.tl/6634
    """
    def _getEndpoint(self, parsedURI):
        """
        Get an endpoint for the given host and port, using a transport
        selected based on scheme.

        @param scheme: A string like C{'http'} or C{'https'} or C{'unix'} (the
            only three supported values) to use to determine how to establish the
            connection.

        @param host: A C{str} giving the hostname which will be connected to in
            order to issue a request.

        @param port: An C{int} giving the port number the connection will be
            on.

        @return: An endpoint which can be used to connect to given address.
        """
        # XXX Bad copy and paste from twisted.web.client.  Must try harder.
        # (Upstreaming this improvement with tests is the way forwards.)
        scheme, host, port = parsedURI.scheme, parsedURI.host, parsedURI.port
        kwargs = {}
        if self._endpointFactory._connectTimeout is not None:
            kwargs['timeout'] = self._connectTimeout
        if scheme == 'http':

            if host.startswith("unix="):
                # "host" actually means "path" here, and we disregard the port
                header, path = host.split("=")
                path = unquote(path)
                if header == "unix":
                    return UNIXClientEndpoint(self._reactor, path, **kwargs)

            kwargs['bindAddress'] = self._endpointFactory._bindAddress
            return TCP4ClientEndpoint(self._reactor, host, port, **kwargs)
        elif scheme == 'https':
            kwargs['bindAddress'] = self._endpointFactory._bindAddress
            return SSL4ClientEndpoint(self._reactor, host, port,
                                      self._wrapContextFactory(host, port),
                                      **kwargs)
        else:
            raise SchemeNotSupported("Unsupported scheme: %r" % (scheme,))



def head(url, **kwargs):
    """
    Make a ``HEAD`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).head(url, **kwargs)


def get(url, headers=None, **kwargs):
    """
    Make a ``GET`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).get(url, headers=headers, **kwargs)


def post(url, data=None, **kwargs):
    """
    Make a ``POST`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).post(url, data=data, **kwargs)


def put(url, data=None, **kwargs):
    """
    Make a ``PUT`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).put(url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    """
    Make a ``PATCH`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).patch(url, data=data, **kwargs)


def delete(url, **kwargs):
    """
    Make a ``DELETE`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).delete(url, **kwargs)


def request(method, url, **kwargs):
    """
    Make an HTTP request.

    :param str method: HTTP method. Example: ``'GET'``, ``'HEAD'``. ``'PUT'``,
         ``'POST'``.
    :param str url: http or https URL, which may include query arguments.

    :param headers: Optional HTTP Headers to send with this request.
    :type headers: Headers or None

    :param params: Optional parameters to be append as the query string to
        the URL, any query string parameters in the URL already will be
        preserved.

    :type params: dict w/ str or list/tuple of str values, list of 2-tuples, or
        None.

    :param data: Optional request body.
    :type data: str, file-like, IBodyProducer, or None

    :param reactor: Optional twisted reactor.

    :param bool persistent: Use persistent HTTP connections.  Default: ``True``
    :param bool allow_redirects: Follow HTTP redirects.  Default: ``True``

    :param auth: HTTP Basic Authentication information.
    :type auth: tuple of ('username', 'password').

    :param int timeout: Request timeout seconds. If a response is not
        received within this timeframe, a connection is aborted with
        ``CancelledError``.

    :rtype: Deferred that fires with an IResponse provider.

    """
    return _client(**kwargs).request(method, url, **kwargs)


#
# Private API
#

def _client(*args, **kwargs):
    reactor = default_reactor(kwargs.get('reactor'))
    #pool = default_pool(reactor,
    #                    kwargs.get('pool'),
    #                    kwargs.get('persistent'))

    # XXX setting pool to None is necessary to stop weird bug where deferreds
    # never fire on requests after chunked requests.
    pool = None
    agent = UNIXCapableAgent(reactor, pool=pool)
    return HTTPClient(agent)

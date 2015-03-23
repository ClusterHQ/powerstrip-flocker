# Copyright ClusterHQ Limited. See LICENSE file for details.

from twisted.web import server, resource
from twisted.application import service, internet

from powerstripflocker.adapter import AdapterResource, HandshakeResource

def getAdapter():
    root = resource.Resource()

    v1 = resource.Resource()
    root.putChild("v1", v1)

    volume = resource.Resource()
    v1.putChild("volume", volume)
    volume.putChild("volumes", AdapterResource())

    v1.putChild("handshake", HandshakeResource())

    site = server.Site(root)
    return site

application = service.Application("Powerstrip Flocker Adapter")

adapterServer = internet.UNIXServer("/var/run/docker-plugin/plugin.sock", getAdapter())
adapterServer.setServiceParent(application)

# Copyright ClusterHQ Limited. See LICENSE file for details.

from twisted.web import server, resource
from twisted.application import service, internet

from powerstripflocker.adapter import AdapterResource

def getAdapter():
    root = resource.Resource()
    root.putChild("flocker-adapter", AdapterResource())
    site = server.Site(root)
    return site

application = service.Application("Powerstrip Flocker Adapter")

adapterServer = internet.TCPServer(9042, getAdapter(), interface='0.0.0.0')
adapterServer.setServiceParent(application)

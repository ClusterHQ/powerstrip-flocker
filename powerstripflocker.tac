# Copyright ClusterHQ Limited. See LICENSE file for details.

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.web import server, resource
import json

from powerstripflocker.adapter import AdapterResource

def getAdapter():
    root = resource.Resource()
    root.putChild("flocker-adapter", AdapterResource())
    site = server.Site(root)
    return site

application = service.Application("Powerstrip Flocker Adapter")

adapterServer = internet.TCPServer(80, adapterAPI, interface='0.0.0.0')
adapterServer.setServiceParent(application)

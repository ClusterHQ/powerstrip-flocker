# Copyright ClusterHQ Inc. See LICENSE file for details.

from twisted.web import server, resource
from twisted.application import service, internet

from powerstripflocker.adapter import (HandshakeResource, CreateResource,
    DestroyResource, MountResource, UnmountResource)

def getHandshakeServer():
    root = resource.Resource()
    v1 = resource.Resource()
    root.putChild("v1", v1)
    v1.putChild("handshake", HandshakeResource())
    site = server.Site(root)
    return site

def getVolumeServer():
    root = resource.Resource()
    v1 = resource.Resource()
    root.putChild("v1", v1)
    volume = resource.Resource()
    v1.putChild("volume", volume)
    volume.putChild("create", CreateResource())
    volume.putChild("destroy", DestroyResource())
    volume.putChild("mount", MountResource())
    volume.putChild("unmount", UnmountResource())
    site = server.Site(root)
    return site

application = service.Application("Flocker Plugin for Docker")

adapterServer = internet.UNIXServer("/var/run/docker-plugin/handshake.sock", getHandshakeServer())
adapterServer.setServiceParent(application)

volumeServer = internet.UNIXServer("/var/run/docker-plugin/volume.sock", getVolumeServer())
volumeServer.setServiceParent(application)

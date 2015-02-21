"""
Some Resources used by passthru.
"""
from twisted.internet import reactor, defer
from twisted.web import server, resource
import json
import pprint
import os

from twisted.web.client import Agent
from treq.client import HTTPClient
import treq

class AdapterResource(resource.Resource):
    """
    A powerstrip adapter which integrates Docker with Flocker for portable
    volumes.
    """
    isLeaf = True

    def __init__(self, *args, **kw):
        self.agent = Agent(reactor) # no connectionpool
        self.client = HTTPClient(self.agent)
        return resource.Resource.__init__(self, *args, **kw)

    def render_POST(self, request):
        """
        Handle a pre-hook: either create a filesystem, or move it in place.
        """
        requestJson = json.loads(request.content.read())
        if requestJson["Type"] != "pre-hook":
            raise Exception("unsupported hook type %s" %
                (requestJson["Type"],))

        pprint.pprint(os.environ)
        # BASE_URL like http://control-service/v1/ ^
        jsonPayload = requestJson["ClientRequest"]["Body"]
        jsonParsed = json.loads(jsonPayload)

        self.baseURL = os.environ.get("FLOCKER_CONTROL_SERVICE_BASE_URL")
        self.ip = os.environ.get("MY_NETWORK_IDENTITY")
        self.hostUUID = os.environ.get("MY_HOST_UUID")

        # simplest possible implementation: always create a volume.
        fsCreateDeferreds = []
        if jsonParsed['HostConfig']['Binds'] is not None:
            # newBinds = []
            for bind in jsonParsed['HostConfig']['Binds']:
                host_path, remainder = bind.split(":", 1)
                if host_path.startswith("/flocker/"):
                    fs = host_path[len("/flocker/"):]
                    # new_host_path = "/hcfs/%s" % (fs,)
                    d = self.client.post(self.baseURL + "/configuration/datasets",
                            json.dumps({"primary": self.ip, "metadata": {"name": fs}}),
                            headers={'Content-Type': ['application/json']})
                    d.addCallback(treq.json_content)
                    fsCreateDeferreds.append(d)
                    # newBinds.append("%s:%s" % (new_host_path, remainder))

        d = defer.gatherResults(fsCreateDeferreds)
        def gotCreatedDatasets(listNewDatasets):
            # TODO: poll /v1/state/datasets until the dataset appears
            print "<" * 80
            pprint.pprint(listNewDatasets)
            print "<" * 80
            request.write(json.dumps({
                "PowerstripProtocolVersion": 1,
                "ModifiedClientRequest": {
                    "Method": "POST",
                    "Request": request.uri,
                    "Body": json.dumps(jsonParsed)}}))
            request.finish()
        d.addCallback(gotCreatedDatasets)
        """
        gettingFilesystemsInPlace = []
        [...]
                    # TODO validation
                    if "/" in fs:
                        raise Exception("Not allowed flocker filesystems more than one level deep")
                    if fs not in self.sitejuggler.currentMasters:
                        # XXX could also require that the filesystem has been
                        # pre-created by e.g. some admin tool
                        d = self.sitejuggler.createFilesystem(fs)
                    else:
                        d = defer.succeed(None)
                    # try to move the filesystem here.
                    # TODO: and lock it, blow up with an error if this fails <- do this next
                    # (lease is already claimed somewhere else, etc). then
                    # don't pass through to docker.
                    def doneCreate(ignored):
                        # fs should be in currentMaster, because if it didn't,
                        # we just created it
                        print ("dockerapi", ">> currentMasters after create",
                                repr(self.sitejuggler.currentMasters[fs]))
                        if self.sitejuggler.currentMasters[fs] != self.sitejuggler.ip:
                            return self.sitejuggler.emit_move_site_to_server(
                                    dataset=fs, ip=self.sitejuggler.ip, forceMove=0)
                    d.addCallback(doneCreate)
                    def checkInPlace(ignored):
                        # Sanity check that the volume is now in place on this host.
                        if self.sitejuggler.currentMasters[fs] != self.sitejuggler.ip:
                            raise Exception("failed to migrate volume into position")
                    d.addCallback(checkInPlace)
                    gettingFilesystemsInPlace.append(d)
            newJsonParsed['HostConfig']['Binds'] = newBinds
        # outside the loop now; XXX check that gatherResults fails on any error
        print 'getting filesystems in place:', gettingFilesystemsInPlace
        dlist = defer.gatherResults(gettingFilesystemsInPlace)
        def doneMoves(ignored):
            request.write(json.dumps({
                "PowerstripProtocolVersion": 1,
                "ModifiedClientRequest": {
                    "Method": "POST",
                    "Request": request.uri,
                    "Body": json.dumps(newJson)}}))
            request.finish()
        dlist.addCallback(doneMoves)
        """
        return server.NOT_DONE_YET

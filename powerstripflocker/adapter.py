"""
Some Resources used by passthru.
"""
from twisted.internet import defer
from twisted.web import server, resource
import json

# Gross hack to avoid threading sitejuggler through everywhere.
theSiteJuggler = []

class AdapterResource(resource.Resource):
    isLeaf = True
    def render_POST(self, request):
        """
        Handle a pre-hook: either create a filesystem, or move it in place.
        """
        requestJson = json.loads(request.content.read())
        if requestJson["Type"] != "pre-hook":
            raise Exception("unsupported hook type %s" %
                (requestJson["Type"],))

        self.sitejuggler = theSiteJuggler[0]

        jsonPayload = requestJson["ClientRequest"]["Body"]
        jsonParsed = json.loads(jsonPayload)
        gettingFilesystemsInPlace = []
        if jsonParsed['HostConfig']['Binds'] is not None:
            newJsonParsed = jsonParsed.copy()
            newBinds = []
            for bind in jsonParsed['HostConfig']['Binds']:
                host_path, remainder = bind.split(":", 1)
                if host_path.startswith("/flocker/"):
                    fs = host_path[len("/flocker/"):]
                    new_host_path = "/hcfs/%s" % (fs,)
                    newBinds.append("%s:%s" % (new_host_path, remainder))
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
            newJson = json.dumps(newJsonParsed)
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
        return server.NOT_DONE_YET

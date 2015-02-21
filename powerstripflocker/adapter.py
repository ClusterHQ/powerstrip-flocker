"""
A Powerstrip adapter which integrates Docker with Flocker to enable portable
volumes without wrapping Docker.

See:
* https://github.com/clusterhq/powerstrip
* https://github.com/clusterhq/flocker
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
    A powerstrip pre-hook for container create.
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
        json_payload = requestJson["ClientRequest"]["Body"]
        json_parsed = json.loads(json_payload)

        self.base_url = os.environ.get("FLOCKER_CONTROL_SERVICE_BASE_URL")
        self.ip = os.environ.get("MY_NETWORK_IDENTITY")
        self.host_uuid = os.environ.get("MY_HOST_UUID")

        def wait_until_volume_created(result, fs):
            """
            Called after a dataset has been created in the cluster's desired
            configuration. Wait until the volume shows up in the cluster actual
            state.

            :return: Deferred which fires with the tuple (dataset_id, fs) --
                that is, the dataset uuid and the corresponding filesystem that
                the docker client asked for -- once the filesystem has been
                created and mounted (iow, exists in the cluster state).
            """
            dataset_id = result["dataset_id"]
            def dataset_exists():
                d = self.agent.get(self.base_url + "/state/datasets")
                d.addCallback(treq.json_content)
                def check_dataset_exists(datasets):
                    for dataset in datasets:
                        if dataset["dataset_id"] == dataset_id:
                            return True
                    return False
                d.addCallback(check_dataset_exists)
                return d
            d = loop_until(dataset_exists)
            d.addCallback(lambda ignored: (dataset_id, fs))
            return d

        # simplest possible implementation: always create a volume.
        fs_create_deferreds = []
        if json_parsed['HostConfig']['Binds'] is not None:
            for bind in json_parsed['HostConfig']['Binds']:
                host_path, remainder = bind.split(":", 1)
                if host_path.startswith("/flocker/"):
                    fs = host_path[len("/flocker/"):]
                    d = self.client.post(self.base_url + "/configuration/datasets",
                        json.dumps({"primary": self.ip, "metadata": {"name": fs}}),
                        headers={'Content-Type': ['application/json']})
                    d.addCallback(treq.json_content)
                    d.addCallback(wait_until_volume_created, fs=fs)
                    fs_create_deferreds.append(d)

        d = defer.gatherResults(fs_create_deferreds)
        def got_created_datasets(list_new_datasets): # TODO this might become got_created_and_moved_datasets
            print "<" * 80
            pprint.pprint(list_new_datasets)
            print "<" * 80
            # newBinds = []
            # new_host_path = "/hcfs/%s" % (fs,)
            # newBinds.append("%s:%s" % (new_host_path, remainder))
            request.write(json.dumps({
                "PowerstripProtocolVersion": 1,
                "ModifiedClientRequest": {
                    "Method": "POST",
                    "Request": request.uri,
                    "Body": json.dumps(json_parsed)}}))
            request.finish()
        d.addCallback(got_created_datasets)
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


# borrowed from flocker.testtools
from twisted.internet.defer import maybeDeferred
from twisted.internet.task import deferLater

def loop_until(predicate):
    """Call predicate every 0.1 seconds, until it returns something ``Truthy``.

    :param predicate: Callable returning termination condition.
    :type predicate: 0-argument callable returning a Deferred.

    :return: A ``Deferred`` firing with the first ``Truthy`` response from
        ``predicate``.
    """
    d = maybeDeferred(predicate)

    def loop(result):
        if not result:
            d = deferLater(reactor, 0.1, predicate)
            d.addCallback(loop)
            return d
        return result
    d.addCallback(loop)
    return d

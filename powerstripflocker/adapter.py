"""
A Docker plugin which integrates Docker with Flocker to enable portable volumes
without wrapping Docker.

See:
* https://github.com/clusterhq/flocker
"""

from twisted.internet import reactor, defer
from twisted.web import server, resource
from twisted.python import log
import json
import pprint
import os

from twisted.web.client import Agent
from treq.client import HTTPClient
import treq

class HandshakeResource(resource.Resource):
    """
    A hook for initial handshake.  Say that we're a volume plugin.
    """
    isLeaf = True

    def render_POST(self, request):
        return json.dumps(dict(
             Implements=["VolumeDriver"],
        ))

class CreateResource(resource.Resource):
    """
    Docker has asked us to create a named volume.  We do nothing in this case,
    because all the good stuff happens in Mount.
    """
    isLeaf = True

    def render_POST(self, request):
        # expect Name
        print "create:", request.content.read()
        return json.dumps(dict(
             Err=None,
        ))

class RemoveResource(resource.Resource):
    """
    Docker has asked us to remove a named volume.  In our case, we disregard
    this request, because flocker volumes are supposed to be able to outlive
    docker volumes.
    """
    isLeaf = True

    def render_POST(self, request):
        # expect Name
        print "remove:", request.content.read()
        return json.dumps(dict(
             Err=None,
        ))

class PathResource(resource.Resource):
    """
    Docker has asked us for the concrete on-disk location of an extant volume.
    If it hasn't already asked for it to be mounted, or is currently on another
    machine, this is an error.
    """
    def __init__(self, *args, **kw):
        self._agent = Agent(reactor) # no connectionpool
        self.client = HTTPClient(self._agent)
        return resource.Resource.__init__(self, *args, **kw)

    def render_POST(self, request):
        # TODO make a FlockerResource base class
        self.base_url = os.environ.get("FLOCKER_CONTROL_SERVICE_BASE_URL")
        # expect Name
        data = json.loads(request.content.read())
        print "path:", data
        d = self.client.get(self.base_url + "/configuration/datasets")
        d.addCallback(treq.json_content)
        def get_dataset(datasets):
            dataset_id = None
            # 1. find the flocker dataset_id of the named volume
            # 2. look up the path of that volume in the datasets current state
            for dataset in datasets:
                if dataset["metadata"]["name"] == data["Name"]:
                    dataset_id = dataset["dataset_id"]
            d = self.client.get(self.base_url + "/state/datasets")
            d.addCallback(treq.json_content)
            def get_path(datasets, dataset_id):
                if dataset_id is None:
                    path = None
                else:
                    for dataset in datasets:
                        if dataset["dataset_id"] == dataset_id:
                            path = dataset["path"]
                if path is not None:
                    request.write(json.dumps(dict(
                         Mountpoint=path,
                         Err=None,
                    )))
                else:
                    request.write(json.dumps(dict(
                         Mountpoint="",
                         Err="unable to find %s" % (data["Name"],),
                    )))
                request.finish()
            d.addCallback(get_path, dataset_id=dataset_id)
            return d
        d.addCallback(get_dataset)
        return server.NOT_DONE_YET

class UnmountResource(resource.Resource):
    """
    Docker has asked us to unmount a volume.  Rather, it has notified us that
    it is no longer actively using a container with this volume.
    """
    def render_POST(self, request):
        # expect Name
        print "unmount:", request.content.read()
        # XXX actually 'release' the volume in some sense. See
        # https://github.com/ClusterHQ/powerstrip-flocker/issues/1
        return json.dumps(dict(
             Err=None,
        ))

class MountResource(resource.Resource):
    """
    A powerstrip pre-hook for container create.
    """
    isLeaf = True

    def __init__(self, *args, **kw):
        self._agent = Agent(reactor) # no connectionpool
        self.client = HTTPClient(self._agent)
        return resource.Resource.__init__(self, *args, **kw)

    def render_POST(self, request):
        """
        Handle a pre-hook: either create a filesystem, or move it in place.
        """
        json_parsed = json.loads(request.content.read())
        print ">>> called with", json_parsed
        pprint.pprint(os.environ)
        # BASE_URL like http://control-service/v1/ ^

        self.base_url = os.environ.get("FLOCKER_CONTROL_SERVICE_BASE_URL")
        self.ip = os.environ.get("MY_NETWORK_IDENTITY")

        def wait_until_volume_in_place(result, fs):
            """
            Called after a dataset has been created or moved in the cluster's
            desired configuration. Wait until the volume shows up in the
            cluster actual state on the right host (either having been created
            or moved).

            :return: Deferred which fires with the tuple (fs, dataset_id) --
                that is, the filesystem and the corresponding flocker dataset
                uuid that the docker client asked for -- firing only once the
                filesystem has been created/moved and mounted (iow, exists on
                the right host in the cluster state).
            """
            print "wait_until_volume_in_place while processing", fs, "got result", result
            dataset_id = result["dataset_id"]
            def dataset_exists():
                d = self.client.get(self.base_url + "/state/datasets")
                d.addCallback(treq.json_content)
                def check_dataset_exists(datasets):
                    """
                    The /v1/state/datasets API seems to show the volume as
                    being on two hosts at once during a move. We assume
                    therefore that when it settles down to only show it on one
                    host that this means the move is complete.
                    """
                    print "Got", self.ip, self.host_uuid, "datasets:", datasets
                    matching_datasets = []
                    for dataset in datasets:
                        if dataset["dataset_id"] == dataset_id:
                            matching_datasets.append(dataset)
                    if len(matching_datasets) == 1:
                        if matching_datasets[0]["primary"] == self.host_uuid:
                            return matching_datasets[0]
                    return False
                d.addCallback(check_dataset_exists)
                return d
            d = loop_until(dataset_exists)
            d.addCallback(lambda dataset: (fs, dataset))
            return d

        d = self.client.get(self.base_url + "/state/nodes")
        d.addCallback(treq.json_content)
        def find_my_uuid(nodes):
            for node in nodes:
                if node["host"] == self.ip:
                    self.host_uuid = node["uuid"]
                    break
            return self.client.get(self.base_url + "/configuration/datasets")
        d.addCallback(find_my_uuid)

        d.addCallback(treq.json_content)
        def got_dataset_configuration(configured_datasets):
            # form a mapping from names onto dataset objects
            configured_dataset_mapping = {}
            for dataset in configured_datasets:
                if dataset["metadata"].get("name"):
                    configured_dataset_mapping[dataset["metadata"].get("name")] = dataset

            # iterate over the datasets we were asked to create by the docker client
            fs_create_deferreds = []
            old_binds = []
            print "got json_parsed...", json_parsed
            if json_parsed['Name'] is not None and json_parsed['Name'] != "":
                binds = [json_parsed['Name']]
                for bind in binds:
                    fs, remainder = bind, ""
                    # TODO validation
                    # if "/" in fs:
                    #    raise Exception("Not allowed flocker filesystems more than one level deep")
                    old_binds.append((fs, remainder))
                    # if a dataset exists, and is in the right place, we're cool.
                    if fs in configured_dataset_mapping:
                        dataset = configured_dataset_mapping[fs]
                        if dataset["primary"] == self.host_uuid:
                            # check / wait for the state to match the desired
                            # configuration
                            fs_create_deferreds.append(wait_until_volume_in_place(dataset, fs=fs))
                        else:
                            # if a dataset exists, but is on the wrong server [TODO
                            # and is not being used], then move it in place.
                            d = self.client.post(
                                self.base_url + "/configuration/datasets/%s" % (
                                    dataset["dataset_id"].encode('ascii'),),
                                json.dumps({"primary": self.host_uuid}),
                                headers={'Content-Type': ['application/json']})
                            d.addCallback(treq.json_content)
                            d.addCallback(wait_until_volume_in_place, fs=fs)
                            fs_create_deferreds.append(d)
                    else:
                        # if a dataset doesn't exist at all, create it on this server.
                        d = self.client.post(self.base_url + "/configuration/datasets",
                            json.dumps({"primary": self.host_uuid, "metadata": {"name": fs}}),
                            headers={'Content-Type': ['application/json']})
                        d.addCallback(treq.json_content)
                        d.addCallback(wait_until_volume_in_place, fs=fs)
                        fs_create_deferreds.append(d)

            d = defer.gatherResults(fs_create_deferreds)
            def got_created_and_moved_datasets(list_new_datasets):
                dataset_mapping = dict(list_new_datasets)
                print "constructed dataset_mapping", dataset_mapping
                new_binds = []
                for fs, remainder in old_binds:
                    # forget about remainder...
                    new_binds.append(dataset_mapping[fs]["path"])
                new_json = {}
                if new_binds:
                    new_json["Mountpoint"] = new_binds[0]
                    new_json["Err"] = None
                else:
                    # This is how you indicate not handling this request
                    new_json["Mountpoint"] = ""
                    new_json["Err"] = "unable to handle"

                print "<<< responding with", new_json
                request.write(json.dumps(new_json))
                request.finish()
            d.addCallback(got_created_and_moved_datasets)
            return d
        d.addCallback(got_dataset_configuration)
        d.addErrback(log.err, 'while processing configured datasets')
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


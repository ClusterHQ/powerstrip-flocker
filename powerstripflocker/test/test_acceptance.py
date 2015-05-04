# Copyright ClusterHQ Inc. See LICENSE file for details.

"""
Acceptance tests for flocker-plugin which can be run against the same
acceptance testing infrastructure (Vagrant, etc) as Flocker itself.

Eventually flocker-plugin should have unit tests, but starting with integration
tests is a reasonable first pass, since unit tests depend on having a big stack
of (ideally verified) fakes for Docker, flocker API etc.

Run these tests first time with:

$ vagrant box add \
      http://build.clusterhq.com/results/vagrant/master/flocker-tutorial.json
$ admin/run-powerstrip-acceptance-tests \
      --keep --distribution=fedora-20 powerstripflocker.test.test_acceptance

After that, you can do quick test runs with the following.
If you haven't changed the server-side component of flocker-plugin (ie, if
you've only changed the acceptance test):

$ ./quick.sh --no-build

If you have changed flocker-plugin itself (and not just the acceptance
test):

$ ./quick.sh

These tests have a propensity to fail unless you also change "MaxClients"
setting higher than 10 (e.g. 100) in /etc/sshd_config on the nodes you're
testing against.
"""

# hack to ensure we import from flocker module in submodule (rather than a
# version of flocker that happens to be installed locally)
import sys, os, json
FLOCKER_PATH = os.path.dirname(os.path.realpath(__file__ + "/../../")) + "/flocker"
sys.path.insert(0, FLOCKER_PATH)

from twisted.internet import defer, reactor
from twisted.trial.unittest import TestCase
from twisted.web.client import Agent
import socket
import treq
from treq.client import HTTPClient

from flocker.acceptance.test_api import get_test_cluster
from flocker.acceptance.testtools import run_SSH
from flocker.testtools import loop_until

from signal import SIGINT
from os import kill

from characteristic import attributes

# This refers to where to fetch the latest version of flocker-plugin from.
# If you want faster development cycle than Docker automated builds allow you
# can change it from "clusterhq" to your personal repo, and create a repo on
# Docker hub called "flocker-plugin". Then modify $DOCKER_PULL_REPO in
# quick.sh accordingly and use that script.
DOCKER_PULL_REPO = "lmarsden"
PF_VERSION = "volume-plugin"

class PowerstripFlockerTests(TestCase):
    """
    Real flocker-plugin tests against two nodes using the flocker
    acceptance testing framework.
    """

    # Slow builds because initial runs involve pulling some docker images
    # (flocker-plugin).
    timeout = 1200

    def setUp(self):
        """
        Ready the environment for tests which actually run docker
        with flocker-plugin enabled.

        * Log into each node in turn:
          * Load flocker-plugin into docker
        """
        self.agent = Agent(reactor) # no connectionpool
        self.client = HTTPClient(self.agent)
        d = get_test_cluster(self, 2)
        def got_cluster(cluster):
            self.cluster = cluster
            self.plugins = {}
            daemonReadyDeferreds = []
            self.ips = [node.address for node in cluster.nodes]
            for ip in self.ips:
                # cleanup after previous test runs
                #run(ip, ["pkill", "-f", "flocker"])
                for container in ("flocker",):
                    try:
                        run(ip, ["docker", "rm", "-f", container])
                    except Exception:
                        print container, "was not running, not killed, OK."
                # start flocker-plugin
                FLOCKER_PLUGIN = "%s/flocker-plugin:%s" % (DOCKER_PULL_REPO, PF_VERSION)
                run(ip, ["docker", "pull", FLOCKER_PLUGIN])
                # TODO - come up with cleaner/nicer way of flocker-plugin
                # being able to establish its own host uuid (or volume
                # mountpoints), such as API calls.
                # See https://github.com/ClusterHQ/flocker-plugin/issues/2
                # for how to do this now.
                host_uuid = run(ip, ["python", "-c", "import json; "
                    "print json.load(open('/etc/flocker/volume.json'))['uuid']"]).strip()
                self.plugins[ip] = remote_service_for_test(self, ip,
                    ["docker", "run", "--plugin", "--name=flocker",
                       "--expose", "80",
                       "-p", "9999:80", # so that we can detect it being up
                       "-e", "FLOCKER_CONTROL_SERVICE_BASE_URL=%s" % (self.cluster.base_url,),
                       "-e", "MY_NETWORK_IDENTITY=%s" % (ip,),
                       "-e", "MY_HOST_UUID=%s" % (host_uuid,),
                       FLOCKER_PLUGIN])
                print "Waiting for flocker-plugin to show up on", ip, "..."
                daemonReadyDeferreds.append(wait_for_socket(ip, 9999))

            d = defer.gatherResults(daemonReadyDeferreds)
            # def debug():
            #     services
            #     import pdb; pdb.set_trace()
            # d.addCallback(lambda ignored: deferLater(reactor, 1, debug))
            return d
        d.addCallback(got_cluster)
        return d

    def test_create_a_dataset(self):
        """
        Running a docker container specifying a dataset name which has never
        been created before creates it in the API.
        """
        node1, node2 = sorted(self.ips)
        fsName = "test001"
        shell(node1, "docker run "
                     "-v /flocker/%s:/data busybox "
                     "sh -c 'echo 1 > /data/file'" % (fsName,))
        url = self.cluster.base_url + "/configuration/datasets"
        d = self.client.get(url)
        d.addCallback(treq.json_content)
        def verify(result):
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0]["metadata"], {"name": fsName})
            self.assertEqual(result[0]["primary"], node1)
        d.addBoth(verify)
        return d

    def test_create_a_dataset_manifests(self):
        """
        Running a docker container specifying a dataset name which has never
        been created before creates the actual filesystem and mounts it in
        place in time for the container to start.

        We can verify this by asking Docker for the information about which
        volumes are *actually* mounted in the container, then going and
        checking that the real volume path on the host contains the '1' written
        to the 'file' file specified in the docker run command...
        """
        node1, node2 = sorted(self.ips)
        fsName = "test001"
        container_id = shell(node1, "docker run -d "
                                    "-v /flocker/%s:/data busybox "
                                    "sh -c 'echo fish > /data/file'" % (fsName,)).strip()
        # The volume that Docker now has mounted...
        docker_inspect = json.loads(run(node1, ["docker", "inspect", container_id]))
        volume = docker_inspect[0]["Volumes"].values()[0]
        # ... exists as a ZFS volume...
        zfs_volumes = shell(node1, "zfs list -t snapshot,filesystem -r flocker "
                                   "|grep %s |wc -l" % (volume,)).strip()
        self.assertEqual(int(zfs_volumes), 1)
        # ... and contains a file which contains the characters "fish".
        catFileOutput = run(node1, ["cat", "%s/file" % (volume,)]).strip()
        self.assertEqual(catFileOutput, "fish")

    def test_create_two_datasets_same_name(self):
        """
        The metadata stored about a dataset name is checked to make sure that
        no two volumes with the same name are created.  (In fact, if two
        volumes are created with the same name on the same host, it's a shared
        volume.)
        """
        node1, node2 = sorted(self.ips)
        fsName = "test001"
        # First volume...
        container_id_1 = shell(node1, "docker run -d "
                                      "-v /flocker/%s:/data busybox "
                                      "sh -c 'echo fish > /data/file'" % (fsName,)).strip()
        docker_inspect = json.loads(run(node1, ["docker", "inspect", container_id_1]))
        volume_1 = docker_inspect[0]["Volumes"].values()[0]

        # Second volume...
        container_id_2 = shell(node1, "docker run -d "
                                      "-v /flocker/%s:/data busybox "
                                      "sh -c 'echo fish > /data/file'" % (fsName,)).strip()
        docker_inspect = json.loads(run(node1, ["docker", "inspect", container_id_2]))
        volume_2 = docker_inspect[0]["Volumes"].values()[0]
        # ... have the same flocker UUID.
        self.assertEqual(volume_1, volume_2)

    def test_move_a_dataset(self):
        """
        Running a docker container specifying a dataset name which has been
        created before but which is no longer running moves the dataset before
        starting the container.
        """
        node1, node2 = sorted(self.ips)
        fsName = "test001"
        # Write some bytes to a volume on one host...
        shell(node1, "docker run "
                     "-v /flocker/%s:/data busybox "
                     "sh -c 'echo chicken > /data/file'" % (fsName,))
        # ... and read them from the same named volume on another...
        container_id = shell(node2, "docker run -d "
                                    "-v /flocker/%s:/data busybox "
                                    "sh -c 'cat /data/file'" % (fsName,)).strip()
        output = run(node2, ["docker", "logs", container_id])
        self.assertEqual(output.strip(), "chicken")

    def test_move_a_dataset_check_persistence(self):
        """
        The data in the dataset between the initial instantiation of it and the
        second instantiation of it persists.
        """
        pass
    test_move_a_dataset_check_persistence.todo = "not implemented yet"

    def test_dataset_is_not_moved_when_being_used(self):
        """
        If a container (*any* container) is currently running with a dataset
        mounted, an error is reported rather than ripping it out from
        underneath a running container.
        """
        pass
    test_dataset_is_not_moved_when_being_used.todo = "not implemented yet"

    def test_two_datasets_one_move_one_create(self):
        """
        When a docker run command mentions two datasets, one which is currently
        not running on another host, and another which is new, the new one gets
        created and the extant one gets moved. Both operations complete before
        the container is started.
        """
        pass
    test_two_datasets_one_move_one_create.todo = "not implemented yet"


def shell(node, command, input=""):
    """
    Run a command (byte string) in a shell on a remote host. Useful for
    defining env vars, pipelines and such. With optional input (bytes).
    """
    command = ["sh", "-c", command]
    result = run(node, command, input)
    return result


def run(node, command, input=""):
    """
    Synchronously run a command (list of bytes) on a node's address (bytes)
    with optional input (bytes).
    """
    #print "Running", command, "on", node
    result = run_SSH(22, "root", node, command, input)
    #print "Output from", node + ":", result, "(%s)" % (command,)
    return result


def wait_for_socket(hostname, port):
    # TODO: upstream this modified version into flocker (it was copied from
    # flocker.acceptance.test_api)
    """
    Wait until remote TCP socket is available.

    :param str hostname: The host where the remote service is running.

    :return Deferred: Fires when socket is available.
    """
    def api_available():
        try:
            s = socket.socket()
            s.connect((hostname, port))
            return True
        except socket.error:
            return False
    return loop_until(api_available)


@attributes(['address', 'process'])
class RemoteService(object):
    """
    A record of a background SSH process and the node that it's running on.

    :ivar bytes address: The IPv4 address on which the service is running.
    :ivar Subprocess.Popen process: The running ``SSH`` process that is running
        the remote process.
    """


def close(process):
    """
    Kill a process.

    :param subprocess.Popen process: The process to be killed.
    """
    process.stdin.close()
    kill(process.pid, SIGINT)


def remote_service_for_test(test_case, address, command):
    """
    Start a remote process (via SSH) for a test and register a cleanup function
    to stop it when the test finishes.

    :param TestCase test_case: The test case instance on which to register
        cleanup operations.
    :param bytes address: The IPv4 address of the node on which to run
        ``command``.
    :param list command: The command line arguments to run remotely via SSH.
    :returns: A ``RemoteService`` instance.
    """
    service = RemoteService(
        address=address,
        process=run_SSH(
            port=22,
            user='root',
            node=address,
            command=command,
            input=b"",
            key=None,
            background=True
        )
    )
    test_case.addCleanup(close, service.process)
    return service

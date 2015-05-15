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
import sys, os, json
BASE_PATH = os.path.dirname(os.path.realpath(__file__ + "/../../"))
FLOCKER_PATH = BASE_PATH + "/flocker"
DOCKER_PATH = BASE_PATH + "/docker"
PLUGIN_DIR = "/usr/share/docker/plugins"
sys.path.insert(0, FLOCKER_PATH)

from twisted.internet import defer, reactor
from twisted.trial.unittest import TestCase
from twisted.web.client import Agent
import socket
import treq
from treq.client import HTTPClient

from flocker.acceptance.test_api import get_test_cluster

from pipes import quote as shell_quote
from subprocess import PIPE, Popen
def run_SSH(port, user, node, command, input, key=None,
            background=False):
    """
    Run a command via SSH.

    :param int port: Port to connect to.
    :param bytes user: User to run the command as.
    :param bytes node: Node to run command on.
    :param command: Command to run.
    :type command: ``list`` of ``bytes``.
    :param bytes input: Input to send to command.
    :param FilePath key: If not None, the path to a private key to use.
    :param background: If ``True``, don't block waiting for SSH process to
         end or read its stdout. I.e. it will run "in the background".
         Also ensures remote process has pseudo-tty so killing the local SSH
         process will kill the remote one.

    :return: stdout as ``bytes`` if ``background`` is false, otherwise
        return the ``subprocess.Process`` object.
    """
    quotedCommand = ' '.join(map(shell_quote, command))
    command = [
        b'ssh',
        b'-p', b'%d' % (port,),
        b'-o', b'StrictHostKeyChecking=no',
        b'-o', b'UserKnownHostsFile=/dev/null',
        ]

    if key is not None:
        command.extend([
            b"-i",
            key.path])

    if background:
        # Force pseudo-tty so that remote process exists when the ssh
        # client does:
        command.extend([b"-t", b"-t"])

    command.extend([
        b'@'.join([user, node]),
        quotedCommand
    ])
    if background:
        process = Popen(command, stdin=PIPE)
        process.stdin.write(input)
        return process
    else:
        process = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)

    result = process.communicate(input)
    if process.returncode != 0:
        raise Exception('Command Failed', command, process.returncode, result)

    return result[0]


from flocker.testtools import loop_until
from twisted.python.filepath import FilePath

from signal import SIGINT
from os import kill, path, system

from characteristic import attributes

# This refers to where to fetch the latest version of flocker-plugin from.
# If you want faster development cycle than Docker automated builds allow you
# can change it from "clusterhq" to your personal repo, and create a repo on
# Docker hub called "flocker-plugin". Then modify $DOCKER_PULL_REPO in
# quick.sh accordingly and use that script.
DOCKER_PULL_REPO = "lmarsden"
PF_VERSION = "new_integration_tests"

# hacks hacks hacks
BUILD_ONCE = []
INJECT_ONCE = {}
KEY = FilePath(os.path.expanduser("~") + "/.ssh/id_rsa_flocker")


class FlockerTestsMixin():
    """
    Real flocker-plugin tests against two nodes using the flocker
    acceptance testing framework.
    """

    # Slow builds because initial runs involve pulling some docker images
    # (flocker-plugin).
    timeout = 1200

    def _buildDockerOnce(self):
        """
        Using blocking APIs, build docker once per test run.
        """
        if len(BUILD_ONCE):
            return
        if path.exists(DOCKER_PATH):
            dockerCmd = ("cd %(dockerDir)s;"
                   "docker build -t custom-docker .;"
                   "docker run --privileged --rm "
                       "-e DOCKER_GITCOMMIT=`git log -1 --format=%%h` "
                       "-v %(dockerDir)s:/go/src/github.com/docker/docker "
                       "custom-docker hack/make.sh binary" % dict(
                           dockerDir=DOCKER_PATH))
            print "Running docker command:", dockerCmd
            exit = system(dockerCmd)
            if exit > 0:
                raise Exception("failed to build docker")
        BUILD_ONCE.append(1)


    def _injectDockerOnce(self, ip):
        """
        Using blocking APIs, copy the docker binary from whence it was built in
        _buildDockerOnce to the given ip.
        """
        if ip not in INJECT_ONCE:
            INJECT_ONCE[ip] = []
        if len(INJECT_ONCE[ip]):
            return

        if path.exists(DOCKER_PATH):
            # e.g. 1.5.0-plugins
            dockerVersion = open("%s/VERSION" % (DOCKER_PATH,)).read().strip()
            binaryPath = "%(dockerDir)s/bundles/%(dockerVersion)s/binary/docker-%(dockerVersion)s" % dict(
                    dockerDir=DOCKER_PATH, dockerVersion=dockerVersion)
            hostBinaryPath = "/usr/bin/docker"
            exit = system("scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
                          "-i %(key)s %(binaryPath)s root@%(ip)s:%(hostBinaryPath)s" % dict(
                            key=KEY, hostBinaryPath=hostBinaryPath, binaryPath=binaryPath, ip=ip))
            if exit > 0:
                raise Exception("failed to inject docker into %(ip)s" % dict(ip=ip))

        INJECT_ONCE[ip].append(1)


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
            # Build docker if necessary (if there's a docker submodule)
            self._buildDockerOnce()
            for ip in self.ips:
                d = self._runFlockerPlugin(ip)
                daemonReadyDeferreds.append(d)
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
        print "About to run docker run..."
        shell(node1, "docker run "
                     "-v %s:/data --volume-driver=flocker busybox "
                     "sh -c 'echo 1 > /data/file'" % (fsName,))
        url = self.cluster.base_url + "/configuration/datasets"
        d = self.client.get(url)
        d.addCallback(treq.json_content)
        def verify(result):
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0]["metadata"], {"name": fsName})
            #self.assertEqual(result[0]["primary"], node1)
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
        shell(node1, "docker run -d "
                     "-v %s:/data --volume-driver=flocker busybox "
                     "sh -c 'echo fish > /data/file'" % (fsName,)).strip()
        # The volume that Docker now has mounted exists as a ZFS volume...
        zfs_volumes = shell(node1, "zfs list -t snapshot,filesystem -r flocker "
                                   "|grep flocker/ |wc -l").strip()
        self.assertEqual(int(zfs_volumes), 1)
        # ... and contains a file which contains the characters "fish".
        catFileOutput = shell(node1, "docker run "
                                     "-v %s:/data --volume-driver=flocker busybox "
                                     "cat /data/file" % (fsName,)).strip()
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
                                      "-v %s:/data --volume-driver=flocker busybox "
                                      "sh -c 'echo fish > /data/file'" % (fsName,)).strip()
        docker_inspect = json.loads(run(node1, ["docker", "inspect", container_id_1]))
        volume_1 = docker_inspect[0]["Volumes"].values()[0]

        # Second volume...
        container_id_2 = shell(node1, "docker run -d "
                                      "-v %s:/data --volume-driver=flocker busybox "
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
                     "-v %s:/data --volume-driver=flocker busybox "
                     "sh -c 'echo chicken > /data/file'" % (fsName,))
        # ... and read them from the same named volume on another...
        container_id = shell(node2, "docker run -d "
                                    "-v %s:/data --volume-driver=flocker busybox "
                                    "sh -c 'cat /data/file'" % (fsName,)).strip()
        output = run(node2, ["docker", "logs", container_id])
        self.assertEqual(output.strip(), "chicken")

    def test_move_a_dataset_check_persistence(self):
        """
        The data in the dataset between the initial instantiation of it and the
        second instantiation of it persists.
        """
        pass
    test_move_a_dataset_check_persistence.skip = "not implemented yet"

    def test_dataset_is_not_moved_when_being_used(self):
        """
        If a container (*any* container) is currently running with a dataset
        mounted, an error is reported rather than ripping it out from
        underneath a running container.
        """
        pass
    test_dataset_is_not_moved_when_being_used.skip = "not implemented yet"

    def test_two_datasets_one_move_one_create(self):
        """
        When a docker run command mentions two datasets, one which is currently
        not running on another host, and another which is new, the new one gets
        created and the extant one gets moved. Both operations complete before
        the container is started.
        """
        pass
    test_two_datasets_one_move_one_create.skip = "not implemented yet"



class PluginAsContainerTests(TestCase, FlockerTestsMixin):
    """
    Run the plugin inside a container. Test that when a container starts before
    a plugin that it depends on, docker correctly waits some timeout before
    failing the container start.
    """

    def setUp(self):
        return FlockerTestsMixin.setUp(self)

    def _runFlockerPlugin(self, ip):
        # cleanup after previous test runs
        run(ip, ["pkill", "-f", "flocker"])
        shell(ip, "sleep 5 && initctl stop docker || true")
        # Copy docker into the respective node
        self._injectDockerOnce(ip)
        # workaround https://github.com/calavera/docker/pull/4#issuecomment-100046383
        shell(ip, "mkdir -p %s" % (PLUGIN_DIR,))
        # cleanup stale sockets
        shell(ip, "rm -f %s/*" % (PLUGIN_DIR,))
        for container in ("flocker",):
            try:
                run(ip, ["docker", "rm", "-f", container])
            except Exception:
                print container, "was not running, not killed, OK."
        # start flocker-plugin
        FLOCKER_PLUGIN = "%s/flocker-plugin:%s" % (DOCKER_PULL_REPO, PF_VERSION)
        run(ip, ["docker", "pull", FLOCKER_PLUGIN])
        self.plugins[ip] = remote_service_for_test(self, ip,
            ["docker", "run", "--name=flocker",
                "-v", "%s:%s" % (PLUGIN_DIR, PLUGIN_DIR),
                "-e", "FLOCKER_CONTROL_SERVICE_BASE_URL=%s" % (self.cluster.base_url,),
                "-e", "MY_NETWORK_IDENTITY=%s" % (ip,),
               FLOCKER_PLUGIN])
        shell(ip, "sleep 5 && initctl start docker")
        print "Waiting for flocker-plugin to show up on", ip, "..."
        return wait_for_plugin(ip)



class PluginOutsideContainerTests(TestCase, FlockerTestsMixin):
    """
    Run the plugin outside of a container. The plugin will therefore always be
    available at /usr/share/docker/plugins.
    """
    def setUp(self):
        return FlockerTestsMixin.setUp(self)

    def _runFlockerPlugin(self, ip):
        shell(ip, "sleep 5 && initctl stop docker || true")
        # Copy docker into the respective node
        self._injectDockerOnce(ip)
        # workaround https://github.com/calavera/docker/pull/4#issuecomment-100046383
        shell(ip, "mkdir -p %s" % (PLUGIN_DIR,))
        # cleanup stale sockets
        shell(ip, "rm -f %s/*" % (PLUGIN_DIR,))
        cmd = ("cd /root && if [ ! -e powerstrip-flocker ]; then "
                   "git clone https://github.com/clusterhq/powerstrip-flocker && "
                   "cd powerstrip-flocker && "
                   "git checkout %s && cd /root;" % (PF_VERSION,)
               + "fi && cd /root/powerstrip-flocker && "
               + "FLOCKER_CONTROL_SERVICE_BASE_URL=%s" % (self.cluster.base_url,)
               + " MY_NETWORK_IDENTITY=%s" % (ip,)
               + " twistd -noy powerstripflocker.tac")
        print "CMD >>", cmd
        self.plugins[ip] = remote_service_for_test(self, ip,
            ["bash", "-c", cmd])
        shell(ip, "sleep 5 && initctl start docker")
        print "Waiting for flocker-plugin to show up on", ip, "..."
        return wait_for_plugin(ip)



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
    result = run_SSH(22, "root", node, command, input, key=KEY)
    #print "Output from", node + ":", result, "(%s)" % (command,)
    return result


def wait_for_plugin(hostname):
    """
    Wait until a non-zero number of plugins are loaded.
    """
    return loop_until(lambda:
            "flocker.sock" in shell(hostname, "ls -alh %s" % (PLUGIN_DIR,)))


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
            key=KEY,
            background=True
        )
    )
    test_case.addCleanup(close, service.process)
    return service

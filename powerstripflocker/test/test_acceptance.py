# Copyright ClusterHQ Limited. See LICENSE file for details.

"""
Acceptance tests for powerstrip-flocker which can be run against the same
acceptance testing infrastructure (Vagrant, etc) as Flocker itself.

Eventually powerstrip-flocker should have unit tests, but starting with
integration tests is a reasonable first pass, since unit tests depend on having
a big stack of (ideally verified) fakes for Docker, powerstrip, flocker API
etc.

Run these tests first time with:

$ vagrant box add \
      http://build.clusterhq.com/results/vagrant/master/flocker-tutorial.json
$ admin/run-powerstrip-acceptance-tests \
      --keep --distribution=fedora-20 powerstripflocker.test.test_acceptance

After that, you can do quick test runs with the following.
If you haven't changed the server-side component of powerstrip-flocker (ie, if
you've only changed the acceptance test):

$ ./quick.sh --no-build

If you have changed powerstrip-flocker itself (and not just the acceptance
test):

$ ./quick.sh
"""

# hack to ensure we import from flocker module in submodule (rather than a
# version of flocker that happens to be installed locally)
import sys, os
FLOCKER_PATH = os.path.dirname(os.path.realpath(__file__ + "/../../")) + "/flocker"
sys.path.insert(0, FLOCKER_PATH)

from twisted.internet import defer
from twisted.trial.unittest import TestCase
import socket

from flocker.acceptance.test_api import wait_for_cluster, remote_service_for_test
from flocker.acceptance.testtools import run_SSH
from flocker.testtools import loop_until

# This refers to where to fetch the latest version of powerstrip-flocker from.
# If you want faster development cycle than Docker automated builds allow you
# can change it from "clusterhq" to your personal repo, and create a repo on
# Docker hub called "powerstrip-flocker". Then modify $DOCKER_PULL_REPO in
# quick.sh accordingly and use that script.
DOCKER_PULL_REPO = "lmarsden"

class PowerstripFlockerTests(TestCase):
    """
    Real powerstrip-flocker tests against two nodes using the flocker
    acceptance testing framework.
    """

    # Slow builds because initial runs involve pulling some docker images
    # (powerstrip, and powerstrip-flocker).
    timeout = 1200

    def setUp(self):
        """
        Ready the environment for tests which actually run docker against
        powerstrip with powerstrip-flocker enabled.

        * Log into each node in turn:
          * Run powerstrip-flocker in docker
          * Run powerstrip in docker
        """
        d = wait_for_cluster(self, 2)
        def got_cluster(cluster):
            self.cluster = cluster
            self.powerstripflockers = {}
            self.powerstrips = {}
            daemonReadyDeferreds = []
            self.ips = [node.address for node in cluster.nodes]
            for ip in self.ips:
                # cleanup after previous test runs
                run(ip, ["pkill", "-f", "flocker"])
                for proc in ("powerstrip", "powerstrip-flocker"):
                    try:
                        run(ip, ["docker", "rm", "-f", proc])
                    except Exception:
                        print proc, "was not running, not killed, OK."
                # put a powerstrip config in place
                run(ip, ["mkdir", "-p", "/root/powerstrip-config"])
                run(ip, ["sh", "-c", "cat > /root/powerstrip-config/adapters.yml"], """
version: 1
endpoints:
  "POST /*/containers/create":
    pre: [flocker]
adapters:
  flocker: http://powerstrip-flocker/flocker-adapter
""")
                # start powerstrip-flocker
                POWERSTRIP_FLOCKER = "%s/powerstrip-flocker:latest" % (DOCKER_PULL_REPO,)
                run(ip, ["docker", "pull", POWERSTRIP_FLOCKER])
                self.powerstripflockers[ip] = remote_service_for_test(self, ip,
                    ["docker", "run", "--name=powerstrip-flocker",
                       "--expose", "80",
                       "-p", "9999:80", # so that we can detect it being up
                       "-e", "FLOCKER_CONTROL_SERVICE_BASE_URL=%s" % (self.cluster.base_url,),
                       POWERSTRIP_FLOCKER])
                print "Waiting for powerstrip-flocker to show up on", ip, "..."
                daemonReadyDeferreds.append(wait_for_socket(ip, 9999))

                # start powerstrip
                POWERSTRIP = "clusterhq/powerstrip:latest"
                run(ip, ["docker", "pull", POWERSTRIP])
                self.powerstrips[ip] = remote_service_for_test(self, ip,
                    ["docker", "run", "--name=powerstrip",
                       "-p", "2375:2375",
                       "-v", "/var/run/docker.sock:/var/run/docker.sock",
                       "-v", "/root/powerstrip-config/adapters.yml:"
                             "/etc/powerstrip/adapters.yml",
                       "--link", "powerstrip-flocker:powerstrip-flocker",
                       POWERSTRIP])
                print "Waiting for powerstrip to show up on", ip, "..."
                daemonReadyDeferreds.append(wait_for_socket(ip, 2375))

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
        been created before creates it and a manifestation manifests.
        """
        node1, node2 = self.ips
        result = powerstrip(node1, "docker run "
                                   "-v /flocker/test001:/data busybox "
                                   "sh -c 'cat 1 > /data/file'")
        print "*" * 80
        print result
        print "*" * 80

    def test_move_a_dataset(self):
        """
        Running a docker container specifying a dataset name which has been
        created before but which is no longer running moves the dataset before
        starting the container.
        """
        pass
    test_move_a_dataset.skip = "not implemented yet"

    def test_move_a_dataset_check_persistence(self):
        """
        The data in the dataset between the initial instantiation of it and the
        second instantiation of it persists.
        """
        pass
    test_move_a_dataset_check_persistence.skip = "not implemented yet"

    def test_dataset_is_not_moved_when_being_used(self):
        """
        If a container is currently running with a dataset mounted, an error is
        reported rather than ripping it out from underneath a running
        container.
        """
        pass
    test_dataset_is_not_moved_when_being_used.skip = "not implemented yet"


def powerstrip(node, command, input=""):
    """
    Run a command in a shell on a remote host. Useful for defining env vars,
    pipelines and such.
    """
    command = ["sh", "-c", "DOCKER_HOST=localhost:2375 " + command]
    return run(node, command, input)


def shell(node, command, input=""):
    """
    Run a command in a shell on a remote host. Useful for defining env vars,
    pipelines and such.
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
    Wait until REST API is available.

    :param str hostname: The host where the control service is
         running.

    :return Deferred: Fires when REST API is available.
    """
    def api_available():
        try:
            s = socket.socket()
            s.connect((hostname, port))
            return True
        except socket.error:
            return False
    return loop_until(api_available)

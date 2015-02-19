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

If you haven't changed the server-side component:

$ ./quick.sh --no-build

Otherwise:

$ ./quick.sh

"""

# hack to ensure we import from flocker module in submodule (rather than a
# version of flocker that happens to be installed locally)
import sys, os
FLOCKER_PATH = os.path.dirname(os.path.realpath(__file__ + "/../../")) + "/flocker"
sys.path.insert(0, FLOCKER_PATH)

from twisted.trial.unittest import TestCase
from flocker.acceptance.test_api import wait_for_cluster, remote_service_for_test
from twisted.internet import defer

# NB run_SSH is a blocking API
from flocker.acceptance.testtools import run_SSH
from flocker.testtools import loop_until

import socket

class PowerstripFlockerTests(TestCase):
    """
    Some real tests against 
    """

    timeout = 1200

    def setUp(self):
        d = wait_for_cluster(self, 2)
        def got_cluster(cluster):
            self.cluster = cluster
            # control service is on self.base_url...
            # ips on [n.address for n in cluster.nodes]
            # what to do next:
            # * log into each node in turn:
            #   * docker run -e "CONTROL_SERVICE_API=%(self.base_url)" \
            #       clusterhq/powerstrip-flocker
            #   * docker run [...] clusterhq/powerstrip
            # * make Docker API requests to the hosts by running "docker" CLI
            #   commands on them via Powerstrip
            # * assert that the desired flocker API actions have occurred
            #   (either via zfs list or flocker API calls)
            self.powerstripflockers = {}
            self.powerstrips = {}
            daemonReadyDeferreds = []
            self.ips = [node.address for node in cluster.nodes]
            for ip in self.ips:
                # cleanup after previous test runs
                run(ip, ["pkill", "-f", "flocker"])
                try:
                    run(ip, ["docker", "rm", "-f", "powerstrip"])
                except:
                    pass
                try:
                    run(ip, ["docker", "rm", "-f", "powerstrip-flocker"])
                except:
                    pass
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
                # start powerstrip-flocker and powerstrip
                self.powerstripflockers[ip] = remote_service_for_test(self, ip,
                    ["docker", "run", "--name=powerstrip-flocker",
                       "--expose", "80",
                       "-p", "9999:80", # so that we can detect it being up
                       "-e", "FLOCKER_CONTROL_SERVICE_BASE_URL=%s" % (self.cluster.base_url,),
                        # XXX change lmarsden to clusterhq before release, for
                        # automated builds (lmarsden is faster for pushing
                        # manual builds during testing)
                       "lmarsden/powerstrip-flocker:latest"])
                print "Waiting for powerstrip-flocker to show up on", ip, "..."
                self.powerstrips[ip] = remote_service_for_test(self, ip,
                    ["docker", "run", "--name=powerstrip",
                       "-p", "2375:2375",
                       "-v", "/var/run/docker.sock:/var/run/docker.sock",
                       "-v", "/root/powerstrip-config/adapters.yml:"
                             "/etc/powerstrip/adapters.yml",
                       "--link", "powerstrip-flocker:powerstrip-flocker",
                       "clusterhq/powerstrip:latest"])
                print "Waiting for powerstrip to show up on", ip, "..."
                daemonReadyDeferreds.append(wait_for_socket(ip, 9999))
                daemonReadyDeferreds.append(wait_for_socket(ip, 2375))
            d = defer.gatherResults(daemonReadyDeferreds)
            # def debug():
            #     services
            #     import pdb; pdb.set_trace()
            # d.addCallback(lambda ignored: deferLater(reactor, 1, debug))
            return d
        d.addCallback(got_cluster)
        return d

    def test_get_a_cluster(self):
        # at this point, we should have self.ips and powerstrip and
        # powerstrip-flocker running...
        import pdb; pdb.set_trace()


def run(node, command, input=""):
    """
    Synchronously run a command (list of bytes) on a node's address (bytes)
    with optional input (bytes).
    """
    return run_SSH(22, "root", node, command, input)


def wait_for_socket(hostname, port):
    # TODO: upstream this modified version into flocker
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

# Copyright ClusterHQ Limited. See LICENSE file for details.

"""
Acceptance tests for powerstrip-flocker which can be run against the same
acceptance testing infrastructure (Vagrant, etc) as Flocker itself.

Reuses the flocker tutorial vagrant boxes.  For how to run, see:
http://doc-dev.clusterhq.com/gettinginvolved/acceptance-testing.html

Eventually powerstrip-flocker should have unit tests, but starting with
integration tests is a reasonable first pass, since unit tests depend on having
a big stack of (ideally verified) fakes for Docker, powerstrip, flocker API
etc.

Run these tests with:

    $ admin/run-powerstrip-acceptance-tests --keep \
          --distribution=fedora-20 powerstripflocker.test.test_acceptance

"""

# hack to get access to flocker module in submodule (rather than a version of
# flocker that happens to be installed locally)
import sys, os
FLOCKER_PATH = os.path.dirname(os.path.realpath(__file__ + "/../../")) + "/flocker"
sys.path.insert(0, FLOCKER_PATH)

from twisted.trial.unittest import TestCase
from flocker.acceptance.test_api import wait_for_cluster, remote_service_for_test
from twisted.internet.task import deferLater
from twisted.internet import reactor

class PowerstripFlockerTests(TestCase):
    def test_get_a_cluster(self):
        d = wait_for_cluster(self, 2)
        def got_cluster(cluster):
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
            services = []
            for ip in [node.address for node in cluster.nodes]:
                services.append(remote_service_for_test(self, ip,
                    ["docker", "run",
                        "busybox", "sh", "-c",
                            "while true; do echo 1; sleep 1; done"]))
            def debug():
                services
                import pdb; pdb.set_trace()
            return deferLater(reactor, 1, debug)
        d.addCallback(got_cluster)
        return d

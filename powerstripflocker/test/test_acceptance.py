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
from flocker.acceptance.test_api import wait_for_cluster

class PowerstripFlockerTests(TestCase):
    def test_get_a_cluster(self):
        d = wait_for_cluster(self, 2)
        def got_cluster(result):
            # control service is on self.base_url...
            # ips on [n.address for n in result.nodes]
            # what to do next:
            # * log into each node in turn:
            #   * docker run -e "CONTROL_SERVICE_API=%(self.base_url)" \
            #       clusterhq/powerstrip-flocker
            #   * docker run [...] clusterhq/powerstrip
            # * make Docker API requests to the hosts by running "docker" CLI
            #   commands on them via Powerstrip
            # * assert that the desired flocker API actions have occurred
            self
            import pdb; pdb.set_trace()
            return result
        d.addCallback(got_cluster)
        return d

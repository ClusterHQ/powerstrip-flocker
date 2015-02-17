# Copyright ClusterHQ Limited. See LICENSE file for details.

"""
Acceptance tests for powerstrip-flocker which can be run against the same
acceptance testing infrastructure (Vagrant, etc) as Flocker itself.

Reuses the flocker tutorial vagrant boxes.  For how to run, see:
http://doc-dev.clusterhq.com/gettinginvolved/acceptance-testing.html

Eventually powerstrip-flocker should have unit tests, but starting with
integration tests is a reasonable first pass, since unit tests depend on having
a big stack of (ideally verified) fakes.

Run these tests with:

    $ admin/run-powerstrip-acceptance-tests --keep \
          --distribution=fedora-20 powerstripflocker.test.test_acceptance

"""
from twisted.trial.unittest import TestCase
from flocker.acceptance import test_api

class PowerstripFlockerTests(TestCase):
    def test_dataset_creation(self):
        return test_api.DatasetAPITests.test_dataset_creation(self)

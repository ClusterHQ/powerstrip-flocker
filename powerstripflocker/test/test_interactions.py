# Copyright ClusterHQ Inc. See LICENSE file for details.

"""
Directly test the powerstrip-flocker implementation using fake Flocker and
Docker plugin API implementations.
"""

class FakeDockerPluginHandshake():
    """
    """
    def __init__(self, socketPath):
        """
        Initialize given a socket path to a plugin which implements the
        handshake.
        """
        pass

    def handshake(self):
        """
        Do the handshake. Just respond with the decoded JSON structure.
        """
        pass


class FakeDockerVolumeExtensionPoint():
    def __init__(self, socketPath):
        """
        Initialize given a socket path to a plugin which implements the
        volume extension point.
        """
        pass

    def create(self, name):
        """
        Called by the tests to simulate docker requesting a volume to be
        created.
        """
        pass

    def destroy(self, name):
        """
        """
        pass



#!/usr/bin/env python

import utils
import subprocess

print "Gathering internal & external IP addresses from Vagrant..."

instances = []
for n in range(1, 3):
    command = "vagrant ssh-config node%d 2>/dev/null |grep HostName" % (n,)
    result = subprocess.check_output(command, shell=True)
    externalIP = result.split()[1]
    result = utils.runSSH(externalIP, ["ifconfig"])
    internalIP = result.split("\n")[1].split()[1].split(":")[1]
    instances.append((externalIP, internalIP))

# node1 is, according to the Vagrantfile, where the control service gets
# started
masterExternal, masterInternal = instances[0]
utils.pushConfig(masterExternal, instances)

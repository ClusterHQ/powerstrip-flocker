#!/usr/bin/env python

import utils
import subprocess

print "Gathering internal & external IP addresses from Vagrant..."

instances = []
for n in range(1, 3): # 2 hosts
    command = "vagrant ssh-config node%d 2>/dev/null |grep HostName" % (n,)
    result = subprocess.check_output(command, shell=True)
    externalIP = result.split()[1]
    result = utils.runSSH(externalIP, ["ifconfig"])
    internalIP = result.split("\n")[1].split()[1].split(":")[1]
    instances.append((externalIP, internalIP))

# node1 is, according to the Vagrantfile, where the control service gets
# started.
masterExternal, masterInternal = instances[0]
minionExternal, minionInternal = instances[1]
utils.pushConfig(masterExternal, instances)

# install powerstrip, powerstrip-flocker, and configure both nodes to start
# flocker-control and flocker-zfs service.
print "Setting up powerstrip, powerstrip-flocker & flocker."

utils.runSSHPassthru(masterExternal, ["sudo", "/vagrant/install.sh", "master"])
utils.runSSHPassthru(minionExternal, ["sudo", "/vagrant/install.sh", "minion"])

print "Finished setting up powerstrip, powerstrip-flocker & flocker!"
print "Now configuring SSH keys on hosts..."

utils.runSSHRaw(masterExternal, 'sudo /vagrant/keygen.sh')
utils.runSSHRaw(minionExternal, 'sudo /vagrant/keygen.sh')

masterPubkey = utils.runSSH(masterExternal,
        ["sudo", "cat", "/root/.ssh/id_rsa.pub"]).strip()
minionPubkey = utils.runSSH(minionExternal,
        ["sudo", "cat", "/root/.ssh/id_rsa.pub"]).strip()

# Make root on the hosts trust eachother
utils.runSSH(masterExternal, ["sudo", "bash", "-c",
        "'echo %s >> /root/.ssh/authorized_keys'" % (minionPubkey,)])
utils.runSSH(minionExternal, ["sudo", "bash", "-c",
        "'echo %s >> /root/.ssh/authorized_keys'" % (masterPubkey,)])
print "Setting up firewall to only allow the minions to connect to the master control service..."

#utils.scp("iptables.sh", masterExternal, "/vagrant/iptables.sh")
#utils.scp("iptables.sh", minionExternal, "/vagrant/iptables.sh")

utils.runSSH(masterExternal, ["sudo", "/vagrant/iptables.sh"])
utils.runSSH(minionExternal, ["sudo", "/vagrant/iptables.sh"])

print "Done! You can now play with docker + powerstrip + flocker on your hosts :)"

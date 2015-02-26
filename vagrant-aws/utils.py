from pipes import quote
import subprocess
import yaml
import os

config = yaml.load(open("settings.yml"))

def runSSH(ip, command):
    command = 'ssh -i %s %s@%s %s' % (config["private_key_path"],
            config["remote_server_username"],
            ip, " ".join(map(quote, command)))
    return subprocess.check_output(command, shell=True)

def runSSHPassthru(ip, command):
    command = 'ssh -i %s %s@%s %s' % (config["private_key_path"],
            config["remote_server_username"],
            ip, " ".join(map(quote, command)))
    return os.system(command)

def pushConfig(text, instances):
    f = open("master_address", "w")
    f.write(text)
    f.close()

    print "Written master address"
    for (externalIP, internalIP) in instances:
        runSSH(externalIP, ['sudo', 'mkdir', '-p', '/etc/flocker'])

        f = open("my_address", "w")
        f.write(externalIP)
        f.close()

        # push the list of minions to the master (for later firewalling of control
        # port and minion port) [might as well push list of minions to all
        # nodes at this point...]
        f = open("minions", "w")
        f.write([e for (e, i) in instances].join("\n"))
        f.close()

        for f in ('master_address', 'my_address', 'minions'):
            scp = ("scp -i %(private_key_path)s %(filename)s "
                   "%(remote_server_username)s@%(external_ip)s:/tmp/%(filename)s") % dict(
                        private_key_path=config["private_key_path"],
                        remote_server_username=config["remote_server_username"],
                        external_ip=externalIP, filename=f)
            subprocess.check_output(scp, shell=True)
            runSSH(externalIP, ['sudo', 'mv', '/tmp/%s' % (f,), '/etc/flocker/%s' % (f,)])
            print "Pushed", f, "to", externalIP

    print "Finished telling all nodes about the master."
